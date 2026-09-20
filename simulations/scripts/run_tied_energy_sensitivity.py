"""Étape 2 du protocole de tying V=K (cf. docs/DevPlan.md) : sensibilité
de la décroissance d'énergie à la variabilité de K.

Grille de sigma, num_seeds, num_steps, tol : pré-enregistrés dans
docs/DevPlan.md, non modifiés ici.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch

from src.hermitian.norm import HermitianRMSNorm
from src.hopfield.tied_dynamics import state_energy, tied_iteration

D_MODEL = 16
T_PATTERNS = 5
BETA = 1.0
NUM_STEPS = 20
NUM_SEEDS = 20
ENERGY_TOL = 1e-4
SIGMA_GRID = [0.0, 0.01, 0.05, 0.1, 0.2, 0.5, 1.0]


def run_trajectory(seed: int, sigma: float) -> list[float]:
    torch.manual_seed(seed)
    k_real = torch.randn(T_PATTERNS, D_MODEL)
    k_imag = torch.randn(T_PATTERNS, D_MODEL)
    xi_real = torch.randn(T_PATTERNS, D_MODEL)
    xi_imag = torch.randn(T_PATTERNS, D_MODEL)
    norm = HermitianRMSNorm(D_MODEL)
    norm.eval()

    energies = [state_energy(xi_real, xi_imag, k_real, k_imag, BETA).item()]
    with torch.no_grad():
        for _ in range(NUM_STEPS):
            k_step_real = k_real + sigma * torch.randn(T_PATTERNS, D_MODEL)
            k_step_imag = k_imag + sigma * torch.randn(T_PATTERNS, D_MODEL)
            xi_real, xi_imag = tied_iteration(
                xi_real, xi_imag, k_step_real, k_step_imag, BETA, norm
            )
            energies.append(
                state_energy(xi_real, xi_imag, k_step_real, k_step_imag, BETA).item()
            )
    return energies


def main() -> None:
    results = {}
    for sigma in SIGMA_GRID:
        total_pairs = 0
        monotone_pairs = 0
        for seed in range(NUM_SEEDS):
            energies = run_trajectory(seed, sigma)
            for t in range(len(energies) - 1):
                total_pairs += 1
                if energies[t + 1] <= energies[t] + ENERGY_TOL:
                    monotone_pairs += 1
        fraction = monotone_pairs / total_pairs
        results[sigma] = fraction
        print(f"sigma={sigma:>5.2f}  fraction monotone = {fraction:.4f}")

    threshold_sigma = None
    for sigma in SIGMA_GRID:
        if results[sigma] >= 0.95:
            threshold_sigma = sigma
    print(f"\nPlus grand sigma avec fraction >= 95% : {threshold_sigma}")

    out_path = Path(__file__).parent.parent / "docs" / "results" / "tied_energy_sensitivity_2026-09-20.json"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(
        json.dumps(
            {
                "d_model": D_MODEL,
                "t_patterns": T_PATTERNS,
                "beta": BETA,
                "num_steps": NUM_STEPS,
                "num_seeds": NUM_SEEDS,
                "energy_tol": ENERGY_TOL,
                "sigma_grid": SIGMA_GRID,
                "fraction_monotone_by_sigma": results,
                "threshold_sigma_95pct": threshold_sigma,
            },
            indent=2,
        )
    )
    print(f"\nRésultat archivé : {out_path}")


if __name__ == "__main__":
    main()
