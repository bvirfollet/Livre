"""Protocole confirmatoire — transfert unitaire entre bassins voisins
(cf. docs/DevPlan.md, pré-enregistré avant ce run). Corrige les deux
failles du run exploratoire (scripts/run_basin_tunneling_unitary.py) :
réduction analytique 2 niveaux (pas de grille Δt fixe), échantillon non
biaisé de paysages et de paires (pas seulement la plus favorable).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import math
from pathlib import Path

import torch

from src.hermitian.norm import HermitianRMSNorm
from src.hermitian.tied_ffn import TiedHermitianFFN
from src.hopfield.full_stack_tied_dynamics import full_stack_state_energy, full_stack_tied_step
from src.superposition.patterns import build_two_pattern_weights

D_MODEL, D_FF, T_TOKENS, BETA, RELAX_STEPS = 16, 32, 5, 1.0, 60
LANDSCAPE_SEEDS = [201, 202, 203, 204, 205]
N_INITS_PER_LANDSCAPE = 60
CLUSTER_TOL = 0.5
SUCCESS_THRESHOLD = 0.5


def flatten_state(x_real: torch.Tensor, x_imag: torch.Tensor) -> torch.Tensor:
    return torch.complex(x_real, x_imag).reshape(-1)


def map_basins(landscape_seed: int) -> list[dict]:
    """Reconstruit un paysage et retourne les bassins distincts trouvés
    (un représentant état + énergie par bassin), triés par énergie."""
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
        for i in range(N_INITS_PER_LANDSCAPE):
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
        if basins and (e - basins[-1]["energy"]) < CLUSTER_TOL:
            continue  # même bassin que le précédent, on garde le premier représentant
        basins.append({"energy": e, "xi": flatten_state(xr, xi)})
    return basins


def two_level_p_b_max(xi_a: torch.Tensor, xi_b: torch.Tensor) -> tuple[float, float]:
    """Réduction analytique exacte à span(xi_a, xi_b), retourne (P_B_max, overlap)."""
    e1 = xi_a / xi_a.norm()
    c = torch.vdot(e1, xi_b)
    b_perp = xi_b - c * e1
    d = b_perp.norm().item()
    alpha = xi_a.norm().item()
    overlap = (torch.abs(c) / xi_b.norm()).item()

    if d < 1e-8:
        # xi_b colinéaire à xi_a : pas de second niveau, transfert trivial vers la même direction
        return 1.0, 1.0

    h = torch.tensor(
        [[alpha**2 + torch.abs(c).item() ** 2, (c * d).item()], [(c.conj() * d).item(), d**2]],
        dtype=torch.complex64,
    )
    eigvals = torch.linalg.eigvalsh(h)
    omega_r = (eigvals[1] - eigvals[0]).item()
    if omega_r < 1e-8:
        return 0.0, overlap

    z0_2d = torch.tensor([1.0, 0.0], dtype=torch.complex64)
    target_2d = torch.tensor([c.item(), d], dtype=torch.complex64) / xi_b.norm()

    ts = torch.linspace(0, 4 * math.pi / omega_r, 201)
    p_b_max = 0.0
    for t in ts:
        u = torch.linalg.matrix_exp(-1j * h * t.item())
        zt = u @ z0_2d
        p_b = torch.abs(torch.vdot(target_2d, zt)).item() ** 2
        p_b_max = max(p_b_max, p_b)
    return p_b_max, overlap


def main() -> None:
    all_pairs = []
    for landscape_seed in LANDSCAPE_SEEDS:
        basins = map_basins(landscape_seed)
        print(f"paysage seed={landscape_seed}: {len(basins)} bassins distincts")
        for i in range(len(basins) - 1):
            gap = basins[i + 1]["energy"] - basins[i]["energy"]
            p_b_max, overlap = two_level_p_b_max(basins[i]["xi"], basins[i + 1]["xi"])
            all_pairs.append(
                {
                    "landscape_seed": landscape_seed,
                    "gap": gap,
                    "overlap": overlap,
                    "p_b_max": p_b_max,
                    "success": p_b_max > SUCCESS_THRESHOLD,
                }
            )

    n_success = sum(1 for p in all_pairs if p["success"])
    print(f"\n{n_success}/{len(all_pairs)} paires franchissent le seuil P_B_max>{SUCCESS_THRESHOLD}")
    print(f"\n{'seed':>6} {'gap':>8} {'overlap':>8} {'P_B_max':>8} {'succès':>7}")
    for p in all_pairs:
        print(
            f"{p['landscape_seed']:>6} {p['gap']:>8.3f} {p['overlap']:>8.4f} "
            f"{p['p_b_max']:>8.4f} {'OUI' if p['success'] else 'non':>7}"
        )

    low_overlap = [p for p in all_pairs if p["overlap"] < 0.05]
    if low_overlap:
        max_p_b_low_overlap = max(p["p_b_max"] for p in low_overlap)
        print(
            f"\nGarde-fou (recouvrement<0,05, {len(low_overlap)} paires) : "
            f"P_B_max maximal observé = {max_p_b_low_overlap:.4f} (doit être proche de 0)"
        )

    out_path = (
        Path(__file__).parent.parent
        / "docs"
        / "results"
        / "basin_tunneling_confirmatory_2026-09-20.json"
    )
    out_path.write_text(
        json.dumps(
            {
                "landscape_seeds": LANDSCAPE_SEEDS,
                "n_inits_per_landscape": N_INITS_PER_LANDSCAPE,
                "cluster_tol": CLUSTER_TOL,
                "success_threshold": SUCCESS_THRESHOLD,
                "n_pairs": len(all_pairs),
                "n_success": n_success,
                "pairs": all_pairs,
            },
            indent=2,
        )
    )
    print(f"\nRésultat archivé : {out_path}")


if __name__ == "__main__":
    main()
