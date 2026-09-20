"""Sensibilité de la décroissance d'énergie du FFN lié (W2=W1†) à la
variabilité de W1 — même protocole que l'étape 2 attention (cf.
docs/DevPlan.md), transposé au FFN.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from pathlib import Path

import torch

from src.hermitian.complex_linear import ComplexLinear
from src.hermitian.gating import conservative_radial_gate, radial_gate_lagrangian
from src.hermitian.norm import HermitianRMSNorm

D_MODEL = 16
D_FF = 32
T_TOKENS = 5
NUM_STEPS = 20
NUM_SEEDS = 20
ENERGY_TOL = 1e-4
SIGMA_GRID = [0.0, 0.01, 0.05, 0.1, 0.2, 0.5, 1.0]


def _ffn_forward(x_real, x_imag, w_real, w_imag):
    h_real = x_real @ w_real.T - x_imag @ w_imag.T
    h_imag = x_real @ w_imag.T + x_imag @ w_real.T
    g_real, g_imag = conservative_radial_gate(h_real, h_imag)
    out_real = g_real @ w_real + g_imag @ w_imag
    out_imag = -g_real @ w_imag + g_imag @ w_real
    return out_real, out_imag, h_real, h_imag


def _energy(x_real, x_imag, h_real, h_imag):
    r = torch.sqrt(h_real**2 + h_imag**2)
    attraction = radial_gate_lagrangian(r).sum()
    quadratic = 0.5 * (x_real.pow(2) + x_imag.pow(2)).sum()
    return (-attraction + quadratic).item()


def run_trajectory(seed: int, sigma: float) -> list[float]:
    torch.manual_seed(seed)
    fc1 = ComplexLinear(D_MODEL, D_FF)  # même init que test_ffn_tying.py (garde-fou sigma=0)
    w_real = fc1.fc_real.weight.detach().clone()
    w_imag = fc1.fc_imag.weight.detach().clone()
    x_real = torch.randn(T_TOKENS, D_MODEL)
    x_imag = torch.randn(T_TOKENS, D_MODEL)
    norm = HermitianRMSNorm(D_MODEL)
    norm.eval()

    energies = []
    with torch.no_grad():
        for _ in range(NUM_STEPS + 1):
            w_step_real = w_real + sigma * torch.randn(D_FF, D_MODEL)
            w_step_imag = w_imag + sigma * torch.randn(D_FF, D_MODEL)
            out_real, out_imag, h_real, h_imag = _ffn_forward(
                x_real, x_imag, w_step_real, w_step_imag
            )
            energies.append(_energy(x_real, x_imag, h_real, h_imag))
            x_real, x_imag = norm(x_real + out_real, x_imag + out_imag)
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

    out_path = (
        Path(__file__).parent.parent
        / "docs"
        / "results"
        / "ffn_tied_energy_sensitivity_2026-09-20.json"
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
