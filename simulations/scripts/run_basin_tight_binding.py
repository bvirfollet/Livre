"""K_ana faible / Y dominant, seconde tentative — Hamiltonien de liaison
forte (tight-binding) sur le vrai paysage `E(x)` entre deux bassins
voisins, cf. docs/DevPlan.md.

Corrige le défaut identifié dans `run_basin_tunneling_confirmatory.py` :
la construction hebbienne à deux motifs (`ξξ†`) ignorait le relief réel
entre les deux bassins (états de norme égale par construction RMSNorm).
Ici, l'énergie réelle `E(x)` le long d'un chemin interpolé entre les
deux bassins est placée directement sur la diagonale d'une chaîne à `N`
sites — la vraie barrière entre à présent dans le calcul.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from pathlib import Path

import torch

from src.hermitian.norm import HermitianRMSNorm
from src.hermitian.tied_ffn import TiedHermitianFFN
from src.hopfield.full_stack_tied_dynamics import full_stack_state_energy, full_stack_tied_step

D_MODEL, D_FF, T_TOKENS, BETA, RELAX_STEPS = 16, 32, 5, 1.0, 60
N_PATH_POINTS = 20  # -> 21 sites (0..20)
HOPPING_GRID = [0.01, 0.1, 1.0, 10.0, 100.0, 1000.0]


def find_basin_pair(landscape_seed: int, gap_min: float = 0.05) -> dict:
    """Reconstruit un paysage, retourne la première paire de bassins
    adjacents rencontrée (par énergie croissante) — même paysage/mêmes
    seeds d'initialisation que le protocole confirmatoire précédent."""
    torch.manual_seed(landscape_seed)
    k_real = torch.randn(T_TOKENS, D_MODEL)
    k_imag = torch.randn(T_TOKENS, D_MODEL)
    ffn = TiedHermitianFFN(D_MODEL, D_FF)
    ffn.eval()
    norm_attn = HermitianRMSNorm(D_MODEL)
    norm_attn.eval()
    norm_ffn = HermitianRMSNorm(D_MODEL)
    norm_ffn.eval()

    converged = []
    with torch.no_grad():
        for i in range(60):
            init_seed = 300_000 + landscape_seed * 1000 + i
            torch.manual_seed(init_seed)
            x_real = torch.randn(T_TOKENS, D_MODEL)
            x_imag = torch.randn(T_TOKENS, D_MODEL)
            for _ in range(RELAX_STEPS):
                x_real, x_imag = full_stack_tied_step(
                    x_real, x_imag, k_real, k_imag, BETA, ffn, norm_attn, norm_ffn
                )
            e = full_stack_state_energy(x_real, x_imag, k_real, k_imag, BETA, ffn)
            converged.append((e, x_real, x_imag))

    converged.sort(key=lambda t: t[0])
    basins = []
    for e, xr, xi in converged:
        if basins and (e - basins[-1][0]) < 0.5:
            continue
        basins.append((e, xr, xi))

    pairs = []
    for i in range(len(basins) - 1):
        gap = basins[i + 1][0] - basins[i][0]
        if gap >= gap_min:
            pairs.append((gap, basins[i], basins[i + 1]))
    pairs.sort(key=lambda p: p[0])
    return {
        "k_real": k_real,
        "k_imag": k_imag,
        "ffn": ffn,
        "pairs": pairs,
    }


def build_path_energies(
    xr_a: torch.Tensor, xi_a: torch.Tensor, xr_b: torch.Tensor, xi_b: torch.Tensor,
    k_real: torch.Tensor, k_imag: torch.Tensor, ffn: TiedHermitianFFN,
) -> torch.Tensor:
    """Interpolation linéaire + renormalisation par token (HermitianRMSNorm,
    gamma=1) à chaque point, énergie réelle E(x_n) sur chaque site."""
    norm = HermitianRMSNorm(D_MODEL)
    norm.eval()
    energies = []
    with torch.no_grad():
        for n in range(N_PATH_POINTS + 1):
            s = n / N_PATH_POINTS
            x_real = (1 - s) * xr_a + s * xr_b
            x_imag = (1 - s) * xi_a + s * xi_b
            x_real, x_imag = norm(x_real, x_imag)
            e = full_stack_state_energy(x_real, x_imag, k_real, k_imag, BETA, ffn)
            energies.append(e)
    return torch.tensor(energies)


def tight_binding_splitting(on_site: torch.Tensor, hopping: float) -> dict:
    """Construit la chaîne tridiagonale, diagonalise, extrait l'écart de
    séparation et les états localisés L/R."""
    n = on_site.shape[0]
    h = torch.diag(on_site.clone())
    for i in range(n - 1):
        h[i, i + 1] = -hopping
        h[i + 1, i] = -hopping

    eigvals, eigvecs = torch.linalg.eigh(h)
    psi0, psi1 = eigvecs[:, 0], eigvecs[:, 1]
    delta_split = (eigvals[1] - eigvals[0]).item()

    combo_plus = (psi0 + psi1) / (2**0.5)
    combo_minus = (psi0 - psi1) / (2**0.5)
    # L := la combinaison la plus concentrée en site 0 (début du chemin, bassin A)
    if combo_plus[0].abs() >= combo_minus[0].abs():
        l_state, r_state = combo_plus, combo_minus
    else:
        l_state, r_state = combo_minus, combo_plus

    return {
        "delta_split": delta_split,
        "eigvals_lowest2": eigvals[:2].tolist(),
        "l_weight_at_0": l_state[0].item() ** 2,
        "l_weight_at_n": l_state[-1].item() ** 2,
        "r_weight_at_0": r_state[0].item() ** 2,
        "r_weight_at_n": r_state[-1].item() ** 2,
    }


def main() -> None:
    landscape_seed = 14  # même paysage que le run exploratoire initial
    data = find_basin_pair(landscape_seed)
    k_real, k_imag, ffn = data["k_real"], data["k_imag"], data["ffn"]

    # on prend les 3 paires au plus petit écart pour ce premier test qualitatif
    results = []
    for gap, (e_a, xr_a, xi_a), (e_b, xr_b, xi_b) in data["pairs"][:3]:
        on_site = build_path_energies(xr_a, xi_a, xr_b, xi_b, k_real, k_imag, ffn)
        barrier_height = (on_site.max() - max(on_site[0], on_site[-1])).item()

        print(f"\nPaire (E_A={e_a:.2f}, E_B={e_b:.2f}, gap={gap:.3f}) — "
              f"hauteur de barrière sur le chemin : {barrier_height:.3f}")
        print("profil E(x_n) le long du chemin :", [round(v, 2) for v in on_site.tolist()])

        row = {"gap": gap, "barrier_height": barrier_height, "by_hopping": {}}
        for t in HOPPING_GRID:
            r = tight_binding_splitting(on_site, t)
            row["by_hopping"][t] = r
            print(f"  hopping={t:>8.2f}  delta_split={r['delta_split']:.6f}  "
                  f"L(0)²={r['l_weight_at_0']:.3f} L(N)²={r['l_weight_at_n']:.3f}")
        results.append(row)

    out_path = Path(__file__).parent.parent / "docs" / "results" / "basin_tight_binding_2026-09-20.json"
    out_path.write_text(json.dumps({
        "landscape_seed": landscape_seed,
        "n_path_points": N_PATH_POINTS,
        "hopping_grid": HOPPING_GRID,
        "results": results,
    }, indent=2))
    print(f"\nRésultat archivé : {out_path}")


if __name__ == "__main__":
    main()
