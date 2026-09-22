"""Protocole confirmatoire — signal de collapse interne c(t) (Test E' et
Test C'), cf. docs/DevPlan.md, pré-enregistré avant ce run. Seeds
fraîches (501, 502, 503), seuils fixés à l'avance.

**Correction du 2026-09-20** : la version précédente normalisait par
`ln(80)` (la dimension totale de l'espace, une constante architecturale
globale — irréaliste comme information « disponible depuis
l'intérieur »). Retiré : `c_norm=(c-c_min)/(c_max-c_min)` est invariant
à toute transformation affine de `c`, donc `ln(80)` s'annulait déjà
dans le résultat final — utiliser directement `-S(ψ)` (l'entropie
brute, signe inversé) donne un résultat numériquement identique, sans
jamais invoquer la dimension totale du réseau.
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
LANDSCAPE_SEEDS = [501, 502, 503]
N_BASINS = 8
DT_TOTAL = 60.0
N_SUBSTEPS = 600
M_TRAJECTORIES = 500
GAMMA_PAIR = (1.0, 12.0)
K0_FIXED = 10.0
SUCCESS_REL_MARGIN_E = 0.2
MIN_COLLAPSES_FOR_POWER = 20
SUCCESS_Z_C = 5.0
SEED = 7070


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
        raise RuntimeError(f"seed={landscape_seed}: seulement {len(basins)} bassins")
    return [z for _, z in basins]


def raw_entropy(z: torch.Tensor) -> float:
    """S(ψ) = -Σ|ψᵢ|² ln|ψᵢ|² — toujours positive, aucune constante
    architecturale globale."""
    p = z.abs() ** 2
    p = p / p.sum()
    p_safe = p.clamp(min=1e-12)
    return -(p_safe * p_safe.log()).sum().item()


def concentration(z: torch.Tensor) -> float:
    """c_brut(ψ) = -S(ψ). Utilisée uniquement via c_norm (min-max), qui
    est invariante à toute transformation affine de c — pas de ln(N)
    nécessaire, il s'annulerait de toute façon. **Ne pas** utiliser
    cette valeur brute pour un test à marge relative (le signe change
    la sémantique de « 0,2×référence » — cf. Test E', qui utilise
    `raw_entropy` directement, jamais `concentration`, pour cette
    raison précise)."""
    return -raw_entropy(z)


def calibrate(w, z0):
    """Test E' (sur l'entropie brute, toujours positive — la marge
    relative n'a de sens que sur une grandeur de signe fixe) +
    calibration de c_min/c_max pour la loi de saut (sur `concentration`,
    invariante à l'affine, cf. remarque plus haut) — calcul exact,
    déterministe."""
    dt_small = DT_TOTAL / N_SUBSTEPS
    u_small = evolution_operator(w, dt_small)
    z = z0.clone().to(torch.complex64)
    s0 = raw_entropy(z)
    s_trace = [s0]
    c_trace = [concentration(z)]
    with torch.no_grad():
        for _ in range(N_SUBSTEPS):
            z = u_small @ z
            s_trace.append(raw_entropy(z))
            c_trace.append(concentration(z))
    s_t = torch.tensor(s_trace)
    c_t = torch.tensor(c_trace)
    c_min, c_max = c_t.min().item(), c_t.max().item()
    s_min_reached = s_t.min().item()
    # cristallisation = baisse d'entropie ; marge relative bien posée
    # car s0 > 0 toujours (entropie de Shannon d'une distribution non
    # dégénérée).
    success_e = (s0 - s_min_reached) > SUCCESS_REL_MARGIN_E * s0
    return {
        "s0": s0, "s_min_reached": s_min_reached,
        "c_min": c_min, "c_max": c_max, "success": success_e,
    }


def run_jump_trajectory(w, z0, k0, gamma, c_min, c_max, eigvecs, generator):
    dt_small = DT_TOTAL / N_SUBSTEPS
    u_small = evolution_operator(w, dt_small)
    z = z0.clone().to(torch.complex64)
    collapsed_at, c_at_jump = None, None
    with torch.no_grad():
        for step in range(N_SUBSTEPS):
            z = u_small @ z
            c = concentration(z)
            c_norm = max(0.0, min(1.0, (c - c_min) / (c_max - c_min)))
            rate = k0 * (c_norm**gamma)
            p_jump = 1.0 - math.exp(-rate * dt_small) if rate > 0 else 0.0
            if p_jump > 0 and torch.rand((), generator=generator).item() < p_jump:
                probs = (eigvecs.conj().T @ z).abs() ** 2
                probs = probs / probs.sum()
                outcome = torch.multinomial(probs, 1, generator=generator).item()
                z = eigvecs[:, outcome].clone().to(torch.complex64)
                collapsed_at, c_at_jump = step, c
                break
    return collapsed_at, c_at_jump


def test_c_prime(w, z0, c_min, c_max, eigvecs, generator) -> dict:
    stats = {}
    for gamma in GAMMA_PAIR:
        c_jumps = []
        for _ in range(M_TRAJECTORIES):
            collapsed_at, c_at_jump = run_jump_trajectory(
                w, z0, K0_FIXED, gamma, c_min, c_max, eigvecs, generator
            )
            if collapsed_at is not None:
                c_jumps.append(c_at_jump)
        n = len(c_jumps)
        if n < MIN_COLLAPSES_FOR_POWER:
            stats[gamma] = {"n_collapses": n, "mean": None, "se": None}
        else:
            t = torch.tensor(c_jumps)
            stats[gamma] = {
                "n_collapses": n, "mean": t.mean().item(),
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
        w = build_n_pattern_weights(patterns, zero_diagonal=True)
        z0 = patterns[0] / patterns[0].norm()
        eigvecs = torch.linalg.eigh(w)[1]

        e = calibrate(w, z0)
        print(f"Test E' : S0={e['s0']:.4f} S_min_atteint={e['s_min_reached']:.4f} "
              f"(baisse relative seuil -{SUCCESS_REL_MARGIN_E*100:.0f}%) -> {'OUI' if e['success'] else 'NON'}")

        c = test_c_prime(w, z0, e["c_min"], e["c_max"], eigvecs, generator)
        if c["underpowered"]:
            print(f"Test C' : NON CONCLUANT ({[(g, c['stats'][g]['n_collapses']) for g in GAMMA_PAIR]})")
        else:
            g_lo, g_hi = GAMMA_PAIR
            s_lo, s_hi = c["stats"][g_lo], c["stats"][g_hi]
            print(f"Test C' : <c>(gamma={g_lo})={s_lo['mean']:.4f}±{s_lo['se']:.4f} (n={s_lo['n_collapses']})  "
                  f"<c>(gamma={g_hi})={s_hi['mean']:.4f}±{s_hi['se']:.4f} (n={s_hi['n_collapses']})  "
                  f"z={c['z_score']:.2f} -> {'OUI' if c['success'] else 'NON'}")

        results[landscape_seed] = {"test_e": e, "test_c": c}

    all_e = all(results[s]["test_e"]["success"] for s in LANDSCAPE_SEEDS)
    all_c = all(results[s]["test_c"]["success"] for s in LANDSCAPE_SEEDS)
    print(f"\nTest E' réussi sur les 3 paysages : {all_e}")
    print(f"Test C' réussi sur les 3 paysages : {all_c}")
    print(f"Décision de citation : {all_e and all_c}")

    out_path = Path(__file__).parent.parent / "docs" / "results" / "c_signal_confirmatory_2026-09-20.json"
    out_path.write_text(json.dumps({
        "landscape_seeds": LANDSCAPE_SEEDS,
        "m_trajectories": M_TRAJECTORIES,
        "gamma_pair": GAMMA_PAIR,
        "k0_fixed": K0_FIXED,
        "results": results,
        "test_e_all_pass": all_e,
        "test_c_all_pass": all_c,
    }, indent=2))
    print(f"\nRésultat archivé : {out_path}")


if __name__ == "__main__":
    main()
