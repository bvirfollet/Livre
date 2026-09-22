"""Nouveau candidat de signal endogène — paramètre d'ordre de Kuramoto
`R(t) = |Σⱼψⱼ| / Σⱼ|ψⱼ|`, cf. contribution Gémini
`implications_théorème_Stone_suite` (2026-09-22) et docs/DevPlan.md.

Corrige les deux défauts identifiés dans le signal précédent
(entropie sur coordonnées brutes) : pas de dépendance de jauge
arbitraire (invariant sous ψ↦e^{iα}ψ global), pas de dilution spatiale
(mesure l'alignement de phase, pas une localisation sur des
coordonnées numérotées). Zéro dépendance à W — seulement ψ.

Exploration, pas confirmatoire.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import math

import torch

from src.hermitian.norm import HermitianRMSNorm
from src.hermitian.tied_ffn import TiedHermitianFFN
from src.hopfield.full_stack_tied_dynamics import full_stack_state_energy, full_stack_tied_step
from src.superposition.dynamics import evolution_operator
from src.superposition.patterns import build_n_pattern_weights

D_MODEL, D_FF, T_TOKENS, BETA, RELAX_STEPS = 16, 32, 5, 1.0, 60
LANDSCAPE_SEED = 14
N_BASINS = 8
DT_TOTAL = 60.0
N_SUBSTEPS = 600
GAMMA_GRID = [1.0, 3.0, 6.0, 12.0]
K0 = 10.0
M_TRAJECTORIES = 20
SEED = 3131


def flatten_state(x_real, x_imag):
    return torch.complex(x_real, x_imag).reshape(-1)


def find_n_basins(landscape_seed, n_basins):
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
            converged.append((e, flatten_state(x_real, x_imag)))

    converged.sort(key=lambda t: t[0])
    basins = []
    for e, z in converged:
        if basins and (e - basins[-1][0]) < 0.5:
            continue
        basins.append((e, z))
        if len(basins) == n_basins:
            break
    return [z for _, z in basins]


def kuramoto_r(z: torch.Tensor) -> float:
    """R(ψ) = |Σψⱼ| / Σ|ψⱼ| ∈ [0,1] — 0=dispersion de phase totale,
    1=cohérence de phase parfaite. Aucune référence à W."""
    return (z.sum().abs() / (z.abs().sum() + 1e-12)).item()


def main() -> None:
    patterns = find_n_basins(LANDSCAPE_SEED, N_BASINS)
    w = build_n_pattern_weights(patterns, zero_diagonal=True)
    z0 = patterns[0] / patterns[0].norm()
    dt_small = DT_TOTAL / N_SUBSTEPS
    u_small = evolution_operator(w, dt_small)
    eigvecs = torch.linalg.eigh(w)[1]

    # 1) Sous Y seul : plage naturelle de R(t)
    z = z0.clone().to(torch.complex64)
    trace = []
    with torch.no_grad():
        for _ in range(N_SUBSTEPS):
            z = u_small @ z
            trace.append(kuramoto_r(z))
    trace_t = torch.tensor(trace)
    r_min, r_max = trace_t.min().item(), trace_t.max().item()
    print(f"Sous Y seul : R(t) min={r_min:.4f} max={r_max:.4f} moyenne={trace_t.mean():.4f}\n")

    def normalize(r: float) -> float:
        return max(0.0, min(1.0, (r - r_min) / (r_max - r_min)))

    generator = torch.Generator().manual_seed(SEED)
    print(f"{'gamma':>6}  {'% effondrées':>13}  {'<pas du 1er saut>':>18}  {'<R au saut>':>12}")

    for gamma in GAMMA_GRID:
        collapses, first_jump_steps, r_jumps = 0, [], []
        for _ in range(M_TRAJECTORIES):
            z = z0.clone().to(torch.complex64)
            collapsed_at, r_at_jump = None, None
            with torch.no_grad():
                for step in range(N_SUBSTEPS):
                    z = u_small @ z
                    r = kuramoto_r(z)
                    rate = K0 * (normalize(r) ** gamma)
                    p_jump = 1.0 - math.exp(-rate * dt_small) if rate > 0 else 0.0
                    if p_jump > 0 and torch.rand((), generator=generator).item() < p_jump:
                        probs = (eigvecs.conj().T @ z).abs() ** 2
                        probs = probs / probs.sum()
                        outcome = torch.multinomial(probs, 1, generator=generator).item()
                        z = eigvecs[:, outcome].clone().to(torch.complex64)
                        collapsed_at, r_at_jump = step, r
                        break
            if collapsed_at is not None:
                collapses += 1
                first_jump_steps.append(collapsed_at)
                r_jumps.append(r_at_jump)

        pct = 100.0 * collapses / M_TRAJECTORIES
        mean_step = sum(first_jump_steps) / len(first_jump_steps) if first_jump_steps else float("nan")
        mean_r = sum(r_jumps) / len(r_jumps) if r_jumps else float("nan")
        print(f"{gamma:>6.1f}  {pct:>12.1f}%  {mean_step:>18.1f}  {mean_r:>12.4f}")

    print(f"\nRepère : R(t) sous Y seul varie entre {r_min:.4f} et {r_max:.4f}.")


if __name__ == "__main__":
    main()
