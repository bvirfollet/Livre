"""Empilement complet (attention liée + FFN liée), poids fixes — même
protocole que l'étape 1 attention/FFN, combiné. Résultat négatif attendu
(cf. docs/DevPlan.md) : contrairement aux composantes testées
séparément, la combinaison séquentielle n'est PAS monotone à 100%.
Rapport, pas une assertion — le résultat lui-même est ce qui est
intéressant, pas un pass/fail.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from pathlib import Path

import torch

from src.hermitian.norm import HermitianRMSNorm
from src.hermitian.tied_ffn import TiedHermitianFFN
from src.hopfield.full_stack_tied_dynamics import (
    full_stack_state_energy,
    full_stack_tied_step,
)

D_MODEL = 16
D_FF = 32
T_TOKENS = 5
BETA = 1.0
NUM_STEPS = 20
NUM_SEEDS = 20
ENERGY_TOL = 1e-4


def run_trajectory(seed: int) -> list[float]:
    torch.manual_seed(seed)
    k_real = torch.randn(T_TOKENS, D_MODEL)
    k_imag = torch.randn(T_TOKENS, D_MODEL)
    ffn = TiedHermitianFFN(D_MODEL, D_FF)
    ffn.eval()
    norm_attn = HermitianRMSNorm(D_MODEL)
    norm_attn.eval()
    norm_ffn = HermitianRMSNorm(D_MODEL)
    norm_ffn.eval()

    x_real = torch.randn(T_TOKENS, D_MODEL)
    x_imag = torch.randn(T_TOKENS, D_MODEL)

    energies = [full_stack_state_energy(x_real, x_imag, k_real, k_imag, BETA, ffn)]
    with torch.no_grad():
        for _ in range(NUM_STEPS):
            x_real, x_imag = full_stack_tied_step(
                x_real, x_imag, k_real, k_imag, BETA, ffn, norm_attn, norm_ffn
            )
            energies.append(
                full_stack_state_energy(x_real, x_imag, k_real, k_imag, BETA, ffn)
            )
    return energies


def main() -> None:
    all_trajectories = {}
    seeds_with_violation = {}
    for seed in range(NUM_SEEDS):
        energies = run_trajectory(seed)
        all_trajectories[seed] = energies
        violations = [
            (t, energies[t], energies[t + 1])
            for t in range(len(energies) - 1)
            if energies[t + 1] > energies[t] + ENERGY_TOL
        ]
        if violations:
            seeds_with_violation[seed] = violations
        status = "VIOLATION" if violations else "monotone"
        print(f"seed={seed:>2}  E0={energies[0]:9.3f}  E_final={energies[-1]:9.3f}  {status}")

    print(
        f"\n{len(seeds_with_violation)}/{NUM_SEEDS} graines avec au moins une "
        f"violation de monotonie (K et W1 tous deux fixes)."
    )
    for seed, viol in seeds_with_violation.items():
        deltas = [v[2] - v[1] for v in viol]
        print(
            f"  seed={seed}: {len(viol)} violations, "
            f"delta min/max={min(deltas):.6f}/{max(deltas):.6f}, "
            f"première au pas {viol[0][0]}"
        )

    out_path = (
        Path(__file__).parent.parent
        / "docs"
        / "results"
        / "full_stack_tied_check_2026-09-20.json"
    )
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(
        json.dumps(
            {
                "d_model": D_MODEL,
                "d_ff": D_FF,
                "t_tokens": T_TOKENS,
                "num_steps": NUM_STEPS,
                "num_seeds": NUM_SEEDS,
                "energy_tol": ENERGY_TOL,
                "trajectories": all_trajectories,
                "seeds_with_violation": {
                    str(s): v for s, v in seeds_with_violation.items()
                },
            },
            indent=2,
        )
    )
    print(f"\nRésultat archivé : {out_path}")


if __name__ == "__main__":
    main()
