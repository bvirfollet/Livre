"""K_ana endogène — « Phase 1 » de la proposition (second avis, via
Gémini, 2026-09-20, cf. docs/DevPlan.md) : remplace le taux de Poisson
constant `K_ana` par un taux asservi à l'état de la trajectoire
elle-même, `λ(t) = K0·p_max(t)^γ`, `p_max(t)=max_k|⟨e_k|ψ(t)⟩|²`.

Question testée : le réseau déclenche-t-il lui-même son propre
effondrement dès qu'un attracteur émerge par interférence constructive,
sans qu'aucun taux constant ne soit imposé de l'extérieur — restant en
superposition tant qu'aucun bassin ne domine ?
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
from src.superposition.dynamics import evolution_operator
from src.superposition.patterns import build_n_pattern_weights

D_MODEL, D_FF, T_TOKENS, BETA, RELAX_STEPS = 16, 32, 5, 1.0, 60
LANDSCAPE_SEED = 14
N_BASINS = 8
DT_TOTAL = 20.0  # fenêtre longue : laisser le temps à un attracteur d'émerger naturellement
N_SUBSTEPS = 200
K0_GRID = [0.1, 1.0, 10.0]
GAMMA_GRID = [2.0, 6.0, 12.0, 20.0]
M_TRAJECTORIES = 20
SEED = 4242


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


def concept_basis(patterns):
    d = patterns[0].shape[0]
    torch.manual_seed(0)
    mat = torch.stack(patterns, dim=1).to(torch.complex64)
    extra = torch.randn(d, d - len(patterns), dtype=torch.complex64)
    full = torch.cat([mat, extra], dim=1)
    q, _ = torch.linalg.qr(full)
    return q


def participation_weights(patterns, z):
    return torch.tensor([torch.abs(torch.vdot(p / p.norm(), z)).item() ** 2 for p in patterns])


def entropy_from_weights(w):
    p = w / w.sum()
    p_safe = p.clamp(min=1e-12)
    return -(p_safe * p_safe.log()).sum().item()


def run_endogenous_trajectory(w, z0, k0, gamma, basis, n_named, generator):
    """Retourne la trajectoire complète d'entropie S(t) (base des motifs)
    et de p_max(t) (base de concepts, signal local à la trajectoire)."""
    dt_small = DT_TOTAL / N_SUBSTEPS
    u_small = evolution_operator(w, dt_small)
    z = z0.clone().to(torch.complex64)
    collapsed_at = None
    p_max_at_jump = None
    p_max_traj = []

    for step in range(N_SUBSTEPS):
        z = u_small @ z
        coeffs = basis.conj().T @ z
        probs_named = coeffs[:n_named].abs() ** 2
        p_max = probs_named.max().item()

        rate = k0 * (p_max**gamma)
        p_jump = 1.0 - math.exp(-rate * dt_small) if rate > 0 else 0.0
        if p_jump > 0 and torch.rand((), generator=generator).item() < p_jump:
            prob_rest = max(0.0, 1.0 - probs_named.sum().item())
            probs = torch.cat([probs_named, torch.tensor([prob_rest])]).clamp(min=0.0)
            probs = probs / probs.sum()
            outcome = torch.multinomial(probs, 1, generator=generator).item()
            if outcome < n_named:
                z = basis[:, outcome].clone()
            else:
                z = z - basis[:, :n_named] @ coeffs[:n_named]
                z = z / z.norm()
            if collapsed_at is None:
                collapsed_at = step
                p_max_at_jump = p_max

        p_max_traj.append(p_max)

    return z, p_max_traj, collapsed_at, p_max_at_jump


def main() -> None:
    patterns = find_n_basins(LANDSCAPE_SEED, N_BASINS)
    w = build_n_pattern_weights(patterns, zero_diagonal=True)
    z0 = patterns[0] / patterns[0].norm()
    basis = concept_basis(patterns)
    generator = torch.Generator().manual_seed(SEED)

    print(f"{N_BASINS} bassins réels (paysage seed={LANDSCAPE_SEED}), "
          f"dt_total={DT_TOTAL}, {N_SUBSTEPS} sous-pas, "
          f"{M_TRAJECTORIES} trajectoires par (K0,gamma).\n")

    # Diagnostic préalable : p_max(t) sous Y seul (K0=0) — une résonance
    # émerge-t-elle spontanément, sans aucune mesure ?
    _, p_max_pure, _, _ = run_endogenous_trajectory(w, z0, 0.0, 2.0, basis, N_BASINS, generator)
    p_max_pure_t = torch.tensor(p_max_pure)
    print(f"Sous Y seul : p_max(t) min={p_max_pure_t.min():.3f} "
          f"max={p_max_pure_t.max():.3f} moyenne={p_max_pure_t.mean():.3f} "
          f"(référence dispersée = 1/8 = 0.125)\n")

    print(f"{'gamma':>6}  {'K0':>8}  {'% effondrées':>13}  "
          f"{'<pas du 1er saut>':>18}  {'<p_max au saut>':>16}")

    rows = []
    for gamma in GAMMA_GRID:
        for k0 in K0_GRID:
            collapses, first_jump_steps, p_max_jumps = 0, [], []
            for _ in range(M_TRAJECTORIES):
                _, _, collapsed_at, p_max_at_jump = run_endogenous_trajectory(
                    w, z0, k0, gamma, basis, N_BASINS, generator
                )
                if collapsed_at is not None:
                    collapses += 1
                    first_jump_steps.append(collapsed_at)
                    p_max_jumps.append(p_max_at_jump)

            pct_collapsed = 100.0 * collapses / M_TRAJECTORIES
            mean_first_jump = sum(first_jump_steps) / len(first_jump_steps) if first_jump_steps else float("nan")
            mean_p_max_jump = sum(p_max_jumps) / len(p_max_jumps) if p_max_jumps else float("nan")
            rows.append({
                "gamma": gamma, "k0": k0,
                "pct_collapsed": pct_collapsed, "mean_first_jump_step": mean_first_jump,
                "mean_p_max_at_jump": mean_p_max_jump,
            })
            print(f"{gamma:>6.1f}  {k0:>8.2f}  {pct_collapsed:>12.1f}%  "
                  f"{mean_first_jump:>18.1f}  {mean_p_max_jump:>16.3f}")

    out_path = Path(__file__).parent.parent / "docs" / "results" / "n_basin_endogenous_kana_2026-09-20.json"
    out_path.write_text(json.dumps({
        "landscape_seed": LANDSCAPE_SEED,
        "dt_total": DT_TOTAL,
        "n_substeps": N_SUBSTEPS,
        "gamma_grid": GAMMA_GRID,
        "k0_grid": K0_GRID,
        "m_trajectories": M_TRAJECTORIES,
        "rows": rows,
    }, indent=2))
    print(f"\nRésultat archivé : {out_path}")


if __name__ == "__main__":
    main()
