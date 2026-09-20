"""Étape 3 (exploratoire, Strate 2/3) du protocole de tying V=K, cf.
docs/DevPlan.md : K réévalué à partir de ξ à chaque pas (empilement
réel), pas de stimulus externe réinjecté. Aucun théorème ne couvre ce
cas — ce script produit une observation, pas un test pass/fail.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from pathlib import Path

import torch

from src.hermitian.complex_linear import ComplexLinear
from src.hermitian.norm import HermitianRMSNorm
from src.hopfield.equivalence import hopfield_energy, hopfield_step

D_MODEL = 16
T_PATTERNS = 5
BETA = 1.0
NUM_STEPS = 20
NUM_SEEDS = 20


def run_trajectory(seed: int) -> list[float]:
    torch.manual_seed(seed)
    k_proj = ComplexLinear(D_MODEL, D_MODEL)
    k_proj.eval()
    norm = HermitianRMSNorm(D_MODEL)
    norm.eval()

    xi_real = torch.randn(T_PATTERNS, D_MODEL)
    xi_imag = torch.randn(T_PATTERNS, D_MODEL)

    energies = []
    with torch.no_grad():
        for _ in range(NUM_STEPS + 1):
            k_real, k_imag = k_proj(xi_real, xi_imag)
            s_real = torch.matmul(xi_real, k_real.transpose(-2, -1)) + torch.matmul(
                xi_imag, k_imag.transpose(-2, -1)
            )
            energies.append(hopfield_energy(s_real, xi_real, xi_imag, BETA).item())

            attn_real, attn_imag, _ = hopfield_step(
                xi_real, xi_imag, k_real, k_imag, k_real, k_imag, BETA
            )
            xi_real, xi_imag = norm(xi_real + attn_real, xi_imag + attn_imag)
    return energies


def main() -> None:
    all_trajectories = {}
    monotone_count = 0
    for seed in range(NUM_SEEDS):
        energies = run_trajectory(seed)
        all_trajectories[seed] = energies
        is_monotone = all(
            energies[t + 1] <= energies[t] + 1e-4 for t in range(len(energies) - 1)
        )
        if is_monotone:
            monotone_count += 1
        trend = "décroissante" if energies[-1] < energies[0] else "non-décroissante"
        print(
            f"seed={seed:>2}  E0={energies[0]:8.3f}  E_final={energies[-1]:8.3f}  "
            f"monotone={is_monotone}  tendance globale={trend}"
        )

    print(
        f"\n{monotone_count}/{NUM_SEEDS} graines strictement monotones sur "
        f"{NUM_STEPS} pas (observation, aucun seuil de succès/échec pré-enregistré)."
    )

    out_path = (
        Path(__file__).parent.parent
        / "docs"
        / "results"
        / "tied_dynamics_real_stacking_2026-09-20.json"
    )
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(
        json.dumps(
            {
                "d_model": D_MODEL,
                "t_patterns": T_PATTERNS,
                "beta": BETA,
                "num_steps": NUM_STEPS,
                "num_seeds": NUM_SEEDS,
                "trajectories": all_trajectories,
                "monotone_count": monotone_count,
            },
            indent=2,
        )
    )
    print(f"\nRésultat archivé : {out_path}")


if __name__ == "__main__":
    main()
