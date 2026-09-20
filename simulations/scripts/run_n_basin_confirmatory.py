"""Protocole confirmatoire — superposition maintenue (test A) et
collapse dissipatif (test B), cf. docs/DevPlan.md, pré-enregistré avant
ce run. Seeds fraîches (301, 302, 303), seuils fixés à l'avance.
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
LANDSCAPE_SEEDS = [301, 302, 303]
N_BASINS = 8
DT_TOTAL = 2.0
N_SUBSTEPS = 20
M_TRAJECTORIES = 1000
SUCCESS_ENTROPY_A = 1.0
SUCCESS_Z_B = 5.0
SEED = 999


def flatten_state(x_real: torch.Tensor, x_imag: torch.Tensor) -> torch.Tensor:
    return torch.complex(x_real, x_imag).reshape(-1)


def find_n_basins(landscape_seed: int, n_basins: int):
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


def participation_weights(patterns, z):
    return torch.tensor([torch.abs(torch.vdot(p / p.norm(), z)).item() ** 2 for p in patterns])


def entropy_from_weights(w):
    p = w / w.sum()
    p_safe = p.clamp(min=1e-12)
    return -(p_safe * p_safe.log()).sum().item()


def run_zeno_trajectory(w, z0, k_ana, basis, n_named, generator):
    dt_small = DT_TOTAL / N_SUBSTEPS
    u_small = evolution_operator(w, dt_small)
    z = z0.clone().to(torch.complex64)
    p_measure = 1.0 - math.exp(-k_ana * dt_small) if k_ana > 0 else 0.0
    for _ in range(N_SUBSTEPS):
        z = u_small @ z
        if p_measure > 0 and torch.rand((), generator=generator).item() < p_measure:
            coeffs = basis.conj().T @ z
            probs_named = coeffs[:n_named].abs() ** 2
            prob_rest = max(0.0, 1.0 - probs_named.sum().item())
            probs = torch.cat([probs_named, torch.tensor([prob_rest])]).clamp(min=0.0)
            probs = probs / probs.sum()
            outcome = torch.multinomial(probs, 1, generator=generator).item()
            if outcome < n_named:
                z = basis[:, outcome].clone()
            else:
                z = z - basis[:, :n_named] @ coeffs[:n_named]
                z = z / z.norm()
    return z


def test_a(patterns) -> dict:
    w = build_n_pattern_weights(patterns, zero_diagonal=True)
    z0 = patterns[0] / patterns[0].norm()
    u = evolution_operator(w, DT_TOTAL)
    z_t = u @ z0.to(torch.complex64)
    weights = participation_weights(patterns, z_t)
    s = entropy_from_weights(weights)
    return {"entropy": s, "success": s > SUCCESS_ENTROPY_A}


def test_b(patterns, generator) -> dict:
    w = build_n_pattern_weights(patterns, zero_diagonal=True)
    z0 = patterns[0] / patterns[0].norm()
    basis = concept_basis(patterns)

    stats = {}
    for k_ana in (0.0, 10.0):
        entropies = []
        for _ in range(M_TRAJECTORIES):
            z_t = run_zeno_trajectory(w, z0, k_ana, basis, N_BASINS, generator)
            weights = participation_weights(patterns, z_t)
            entropies.append(entropy_from_weights(weights))
        ent = torch.tensor(entropies)
        mean = ent.mean().item()
        se = (ent.std(unbiased=True) / math.sqrt(M_TRAJECTORIES)).item()
        stats[k_ana] = {"mean": mean, "se": se}

    z_score = (stats[0.0]["mean"] - stats[10.0]["mean"]) / math.sqrt(
        stats[0.0]["se"] ** 2 + stats[10.0]["se"] ** 2
    )
    return {"stats": stats, "z_score": z_score, "success": z_score >= SUCCESS_Z_B}


def main() -> None:
    generator = torch.Generator().manual_seed(SEED)
    results = {}
    for landscape_seed in LANDSCAPE_SEEDS:
        print(f"\n=== paysage seed={landscape_seed} ===")
        patterns = find_n_basins(landscape_seed, N_BASINS)

        a = test_a(patterns)
        print(f"Test A : S(dt=2.0, K_ana=0) = {a['entropy']:.4f} "
              f"(seuil > {SUCCESS_ENTROPY_A}) -> {'OUI' if a['success'] else 'NON'}")

        b = test_b(patterns, generator)
        s0, s10 = b["stats"][0.0], b["stats"][10.0]
        print(f"Test B : <S>(K_ana=0)={s0['mean']:.4f}±{s0['se']:.4f}  "
              f"<S>(K_ana=10)={s10['mean']:.4f}±{s10['se']:.4f}  "
              f"z={b['z_score']:.2f} (seuil >= {SUCCESS_Z_B}) -> {'OUI' if b['success'] else 'NON'}")

        results[landscape_seed] = {"test_a": a, "test_b": b}

    all_a = all(results[s]["test_a"]["success"] for s in LANDSCAPE_SEEDS)
    all_b = all(results[s]["test_b"]["success"] for s in LANDSCAPE_SEEDS)
    print(f"\nTest A réussi sur les 3 paysages : {all_a}")
    print(f"Test B réussi sur les 3 paysages : {all_b}")
    print(f"Décision de citation (les deux requis) : {all_a and all_b}")

    out_path = Path(__file__).parent.parent / "docs" / "results" / "n_basin_confirmatory_2026-09-20.json"
    out_path.write_text(json.dumps({
        "landscape_seeds": LANDSCAPE_SEEDS,
        "dt_total": DT_TOTAL,
        "m_trajectories": M_TRAJECTORIES,
        "success_entropy_a": SUCCESS_ENTROPY_A,
        "success_z_b": SUCCESS_Z_B,
        "results": results,
        "test_a_all_pass": all_a,
        "test_b_all_pass": all_b,
    }, indent=2))
    print(f"\nRésultat archivé : {out_path}")


if __name__ == "__main__":
    main()
