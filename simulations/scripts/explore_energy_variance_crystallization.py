"""Revalidation de la cristallisation spontanée avec ΔE²(ψ) au lieu de
p_max(t), cf. docs/DevPlan.md. ΔE²(ψ)=⟨ψ|W²|ψ⟩-⟨ψ|W|ψ⟩² ne demande que
`ψ` et `W` — calculable depuis l'intérieur du réseau, sans base de
concepts nommés construite de l'extérieur (contrairement à p_max).

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
GAMMA_GRID = [1.0, 3.0, 6.0]
K0 = 10.0
M_TRAJECTORIES = 15
SEED = 9090


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


def delta_e2(w: torch.Tensor, z: torch.Tensor) -> float:
    """ΔE²(ψ) = <ψ|W²|ψ> - <ψ|W|ψ>² — calculable depuis psi et W seuls."""
    wz = w @ z
    mean_w = torch.vdot(z, wz).real.item()
    mean_w2 = torch.vdot(wz, wz).real.item()  # <psi|W W|psi> = ||W psi||^2 (W hermitien)
    return mean_w2 - mean_w**2


def main() -> None:
    patterns = find_n_basins(LANDSCAPE_SEED, N_BASINS)
    w = build_n_pattern_weights(patterns, zero_diagonal=True)
    z0 = patterns[0] / patterns[0].norm()
    dt_small = DT_TOTAL / N_SUBSTEPS
    u_small = evolution_operator(w, dt_small)

    # 1) Sous Y seul : plage naturelle de ΔE²(t)
    z = z0.clone().to(torch.complex64)
    trace = []
    with torch.no_grad():
        for _ in range(N_SUBSTEPS):
            z = u_small @ z
            trace.append(delta_e2(w, z))
    trace_t = torch.tensor(trace)
    print(f"Sous Y seul : ΔE²(t) min={trace_t.min():.3f} max={trace_t.max():.3f} "
          f"moyenne={trace_t.mean():.3f}\n")

    sigma2 = trace_t.mean().item()  # échelle de référence pour la loi de saut

    # 2) Loi de saut décroissante en ΔE² : lambda(t) = K0 / (1+DE2/sigma2)^gamma
    generator = torch.Generator().manual_seed(SEED)
    print(f"{'gamma':>6}  {'% effondrées':>13}  {'<pas du 1er saut>':>18}  {'<DeltaE2 au saut>':>18}")

    for gamma in GAMMA_GRID:
        collapses, first_jump_steps, de2_jumps = 0, [], []
        for _ in range(M_TRAJECTORIES):
            z = z0.clone().to(torch.complex64)
            collapsed_at, de2_at_jump = None, None
            with torch.no_grad():
                for step in range(N_SUBSTEPS):
                    z = u_small @ z
                    de2 = delta_e2(w, z)
                    rate = K0 / (1.0 + de2 / sigma2) ** gamma
                    p_jump = 1.0 - math.exp(-rate * dt_small)
                    if torch.rand((), generator=generator).item() < p_jump:
                        eigvals, eigvecs = torch.linalg.eigh(w)
                        probs = (eigvecs.conj().T @ z).abs() ** 2
                        probs = probs / probs.sum()
                        outcome = torch.multinomial(probs, 1, generator=generator).item()
                        z = eigvecs[:, outcome].clone().to(torch.complex64)
                        collapsed_at, de2_at_jump = step, de2
                        break
            if collapsed_at is not None:
                collapses += 1
                first_jump_steps.append(collapsed_at)
                de2_jumps.append(de2_at_jump)

        pct = 100.0 * collapses / M_TRAJECTORIES
        mean_step = sum(first_jump_steps) / len(first_jump_steps) if first_jump_steps else float("nan")
        mean_de2 = sum(de2_jumps) / len(de2_jumps) if de2_jumps else float("nan")
        print(f"{gamma:>6.1f}  {pct:>12.1f}%  {mean_step:>18.1f}  {mean_de2:>18.3f}")


if __name__ == "__main__":
    main()
