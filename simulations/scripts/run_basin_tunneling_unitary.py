"""K_ana faible / régime Y dominant : transfert de population entre deux
bassins voisins sous évolution UNITAIRE pure (U=exp(-iW·t/Y), K_ana=0),
en réutilisant tel quel le module `src/superposition/` (Leggett-Garg).

Script autonome et reproductible (pas de dépendance à un fichier binaire
non versionné) : retrouve d'abord la paire de bassins voisins sur le
paysage tying complet (seed=14, mêmes seeds d'initialisation que
`scripts/run_full_stack_tied_check.py`), puis simule l'évolution
unitaire entre eux.

Les deux bassins jouent le rôle des deux motifs concurrents ξ¹/ξ² du
protocole Leggett-Garg — aplatis en un vecteur complexe unique
`nN=T*d_model`. Aucun nouveau formalisme : `Y` renomme `ħ_eff` (cf.
`docs/DevPlan.md`, correction du glissement de nom, contribution Gémini
« implications_théorème_Stone ») et joue le rôle du facteur d'échelle du
temps dans `U=exp(-iW·t/Y)` — équivalent à balayer `Δt` directement.
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
from src.superposition.dynamics import evolution_operator
from src.superposition.patterns import build_two_pattern_weights

D_MODEL, D_FF, T_TOKENS, BETA, RELAX_STEPS = 16, 32, 5, 1.0, 60
LANDSCAPE_SEED = 14
INIT_SEEDS = range(2000, 2060)
DT_GRID = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0]


def flatten_state(x_real: torch.Tensor, x_imag: torch.Tensor) -> torch.Tensor:
    """(T, d_model) réel+imag -> vecteur complexe plat (nN=T*d_model,)."""
    return torch.complex(x_real, x_imag).reshape(-1)


def find_neighboring_basin_pair() -> dict:
    """Reconstruit le paysage tying complet (seed=14) et retrouve la
    paire de bassins voisins au plus petit écart, parmi 60 conditions
    initiales — même paysage que `scripts/run_full_stack_tied_check.py`."""
    torch.manual_seed(LANDSCAPE_SEED)
    k_real = torch.randn(T_TOKENS, D_MODEL)
    k_imag = torch.randn(T_TOKENS, D_MODEL)
    ffn = TiedHermitianFFN(D_MODEL, D_FF)
    ffn.eval()
    norm_attn = HermitianRMSNorm(D_MODEL)
    norm_attn.eval()
    norm_ffn = HermitianRMSNorm(D_MODEL)
    norm_ffn.eval()

    converged = {}
    with torch.no_grad():
        for init_seed in INIT_SEEDS:
            torch.manual_seed(init_seed)
            x_real = torch.randn(T_TOKENS, D_MODEL)
            x_imag = torch.randn(T_TOKENS, D_MODEL)
            for _ in range(RELAX_STEPS):
                x_real, x_imag = full_stack_tied_step(
                    x_real, x_imag, k_real, k_imag, BETA, ffn, norm_attn, norm_ffn
                )
            e = full_stack_state_energy(x_real, x_imag, k_real, k_imag, BETA, ffn)
            converged[init_seed] = (round(e, 2), x_real.clone(), x_imag.clone())

    by_energy = sorted(converged.items(), key=lambda kv: kv[1][0])
    prev_seed, (prev_e, *_) = by_energy[0]
    best_gap, best_pair = float("inf"), None
    for seed, (e, _, _) in by_energy[1:]:
        gap = e - prev_e
        if 0.05 < gap < best_gap:
            best_gap, best_pair = gap, (prev_seed, seed)
        prev_seed, prev_e = seed, e

    seed_a, seed_b = best_pair
    e_a, xr_a, xi_a = converged[seed_a]
    e_b, xr_b, xi_b = converged[seed_b]
    return {
        "gap": best_gap,
        "xi_a": flatten_state(xr_a, xi_a),
        "xi_b": flatten_state(xr_b, xi_b),
        "e_a": e_a,
        "e_b": e_b,
    }


def main() -> None:
    basins = find_neighboring_basin_pair()
    xi_a, xi_b, gap = basins["xi_a"], basins["xi_b"], basins["gap"]

    w = build_two_pattern_weights(xi_a, xi_b, zero_diagonal=True)
    z0 = xi_a / xi_a.norm()
    target = xi_b / xi_b.norm()
    overlap = (torch.abs(torch.vdot(xi_a, xi_b)) / (xi_a.norm() * xi_b.norm())).item()

    print(f"Écart d'énergie classique entre les deux bassins : {gap:.4f}")
    print(f"Recouvrement |<xi_a|xi_b>| (non nul -> dynamique non triviale) : {overlap:.4f}")
    print()
    print(f"{'dt (=t/Y)':>10}  {'P_B(dt)':>10}")

    results = {}
    for dt in DT_GRID:
        u = evolution_operator(w, dt)
        z_t = u @ z0.to(torch.complex64)
        p_b = torch.abs(torch.vdot(target.to(torch.complex64), z_t)).item() ** 2
        results[dt] = p_b
        print(f"{dt:>10.2f}  {p_b:>10.4f}")

    max_p_b = max(results.values())
    print(f"\nP_B max atteint sur la grille : {max_p_b:.4f}")

    out_path = Path(__file__).parent.parent / "docs" / "results" / "basin_tunneling_unitary_2026-09-20.json"
    out_path.write_text(
        json.dumps(
            {
                "landscape_seed": LANDSCAPE_SEED,
                "classical_gap": gap,
                "overlap_xi_a_xi_b": overlap,
                "dt_grid": DT_GRID,
                "p_b_by_dt": results,
                "max_p_b": max_p_b,
            },
            indent=2,
        )
    )
    print(f"Résultat archivé : {out_path}")


if __name__ == "__main__":
    main()
