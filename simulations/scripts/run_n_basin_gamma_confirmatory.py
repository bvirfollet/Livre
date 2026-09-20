"""Protocole confirmatoire — cristallisation spontanée (test E) et
sélectivité de gamma (test C), cf. docs/DevPlan.md, pré-enregistré
avant ce run. Seeds fraîches (401, 402, 403), seuils fixés à l'avance.
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
LANDSCAPE_SEEDS = [401, 402, 403]
N_BASINS = 8
DT_TOTAL = 20.0
N_SUBSTEPS = 200
M_TRAJECTORIES = 500
GAMMA_PAIR = (2.0, 20.0)
K0_FIXED = 10.0
SUCCESS_MAX_P_MAX_E = 0.5
MIN_COLLAPSES_FOR_POWER = 20
SUCCESS_Z_C = 5.0
SEED = 5150


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
    if len(basins) < n_basins:
        raise RuntimeError(f"seed={landscape_seed}: seulement {len(basins)} bassins distincts trouvés")
    return [z for _, z in basins]


def concept_basis(patterns):
    d = patterns[0].shape[0]
    torch.manual_seed(0)
    mat = torch.stack(patterns, dim=1).to(torch.complex64)
    extra = torch.randn(d, d - len(patterns), dtype=torch.complex64)
    full = torch.cat([mat, extra], dim=1)
    q, _ = torch.linalg.qr(full)
    return q


def run_endogenous_trajectory(w, z0, k0, gamma, basis, n_named, generator):
    dt_small = DT_TOTAL / N_SUBSTEPS
    u_small = evolution_operator(w, dt_small)
    z = z0.clone().to(torch.complex64)
    collapsed_at, p_max_at_jump = None, None
    p_max_pure_trace = []

    for step in range(N_SUBSTEPS):
        z = u_small @ z
        coeffs = basis.conj().T @ z
        probs_named = coeffs[:n_named].abs() ** 2
        p_max = probs_named.max().item()
        p_max_pure_trace.append(p_max)

        if k0 > 0:
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

    return collapsed_at, p_max_at_jump, max(p_max_pure_trace)


def test_e(patterns) -> dict:
    w = build_n_pattern_weights(patterns, zero_diagonal=True)
    z0 = patterns[0] / patterns[0].norm()
    basis = concept_basis(patterns)
    _, _, max_p_max = run_endogenous_trajectory(
        w, z0, 0.0, 1.0, basis, N_BASINS, torch.Generator().manual_seed(0)
    )
    return {"max_p_max": max_p_max, "success": max_p_max > SUCCESS_MAX_P_MAX_E}


def test_c(patterns, generator) -> dict:
    w = build_n_pattern_weights(patterns, zero_diagonal=True)
    z0 = patterns[0] / patterns[0].norm()
    basis = concept_basis(patterns)

    stats = {}
    for gamma in GAMMA_PAIR:
        p_max_jumps = []
        for _ in range(M_TRAJECTORIES):
            collapsed_at, p_max_at_jump, _ = run_endogenous_trajectory(
                w, z0, K0_FIXED, gamma, basis, N_BASINS, generator
            )
            if collapsed_at is not None:
                p_max_jumps.append(p_max_at_jump)
        n = len(p_max_jumps)
        if n < MIN_COLLAPSES_FOR_POWER:
            stats[gamma] = {"n_collapses": n, "mean": None, "se": None}
        else:
            t = torch.tensor(p_max_jumps)
            stats[gamma] = {
                "n_collapses": n,
                "mean": t.mean().item(),
                "se": (t.std(unbiased=True) / math.sqrt(n)).item(),
            }

    underpowered = any(stats[g]["mean"] is None for g in GAMMA_PAIR)
    if underpowered:
        return {"stats": stats, "z_score": None, "success": False, "underpowered": True}

    g_lo, g_hi = GAMMA_PAIR
    z_score = (stats[g_hi]["mean"] - stats[g_lo]["mean"]) / math.sqrt(
        stats[g_hi]["se"] ** 2 + stats[g_lo]["se"] ** 2
    )
    return {"stats": stats, "z_score": z_score, "success": z_score >= SUCCESS_Z_C, "underpowered": False}


def main() -> None:
    generator = torch.Generator().manual_seed(SEED)
    results = {}
    for landscape_seed in LANDSCAPE_SEEDS:
        print(f"\n=== paysage seed={landscape_seed} ===")
        patterns = find_n_basins(landscape_seed, N_BASINS)

        e = test_e(patterns)
        print(f"Test E : max_t p_max(t) = {e['max_p_max']:.4f} "
              f"(seuil > {SUCCESS_MAX_P_MAX_E}) -> {'OUI' if e['success'] else 'NON'}")

        c = test_c(patterns, generator)
        if c["underpowered"]:
            print(f"Test C : NON CONCLUANT (moins de {MIN_COLLAPSES_FOR_POWER} collapses "
                  f"dans une condition — {[(g, c['stats'][g]['n_collapses']) for g in GAMMA_PAIR]})")
        else:
            g_lo, g_hi = GAMMA_PAIR
            s_lo, s_hi = c["stats"][g_lo], c["stats"][g_hi]
            print(f"Test C : <p_max>(gamma={g_lo})={s_lo['mean']:.4f}±{s_lo['se']:.4f} (n={s_lo['n_collapses']})  "
                  f"<p_max>(gamma={g_hi})={s_hi['mean']:.4f}±{s_hi['se']:.4f} (n={s_hi['n_collapses']})  "
                  f"z={c['z_score']:.2f} (seuil >= {SUCCESS_Z_C}) -> {'OUI' if c['success'] else 'NON'}")

        results[landscape_seed] = {"test_e": e, "test_c": c}

    all_e = all(results[s]["test_e"]["success"] for s in LANDSCAPE_SEEDS)
    all_c = all(results[s]["test_c"]["success"] for s in LANDSCAPE_SEEDS)
    print(f"\nTest E réussi sur les 3 paysages : {all_e}")
    print(f"Test C réussi sur les 3 paysages : {all_c}")
    print(f"Décision de citation (les deux requis) : {all_e and all_c}")

    out_path = Path(__file__).parent.parent / "docs" / "results" / "n_basin_gamma_confirmatory_2026-09-20.json"
    out_path.write_text(json.dumps({
        "landscape_seeds": LANDSCAPE_SEEDS,
        "m_trajectories": M_TRAJECTORIES,
        "gamma_pair": GAMMA_PAIR,
        "k0_fixed": K0_FIXED,
        "success_max_p_max_e": SUCCESS_MAX_P_MAX_E,
        "success_z_c": SUCCESS_Z_C,
        "results": results,
        "test_e_all_pass": all_e,
        "test_c_all_pass": all_c,
    }, indent=2))
    print(f"\nRésultat archivé : {out_path}")


if __name__ == "__main__":
    main()
