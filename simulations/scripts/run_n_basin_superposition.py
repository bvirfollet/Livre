"""Superposition simultanée sur N=8 bassins réels — recadrage du
2026-09-20 (cf. docs/DevPlan.md, section « Recadrage : superposition
simultanée et intrication réseau/entrée »).

Remplace le fil « tunnel » (dynamique post-effondrement, mauvaise
question) par la question directement posée : en évolution unitaire
pure (K_ana=0), en partant localisé dans un seul bassin, le réseau
explore-t-il *simultanément* plusieurs bassins à la fois (superposition
cohérente), pas séquentiellement ?

Métrique : entropie de participation sur les 8 directions de bassin
(recommandation validée par Bertrand) — pas le protocole Leggett-Garg
existant (binaire par construction, ne généralise pas naturellement à
N=8 issues sans inventer une variante ad hoc).

8 bassins réels du paysage tying complet déjà utilisé (seed=14) — choix
délibéré pour garder la possibilité de croiser avec les résultats
précédents (bassins déjà caractérisés dans le fil tunnel).
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
DT_GRID = [0.0, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0]


def flatten_state(x_real: torch.Tensor, x_imag: torch.Tensor) -> torch.Tensor:
    return torch.complex(x_real, x_imag).reshape(-1)


def find_n_basins(landscape_seed: int, n_basins: int) -> list[torch.Tensor]:
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


def participation_weights(patterns: list[torch.Tensor], z: torch.Tensor) -> torch.Tensor:
    """w_i = |<xi_i/||xi_i||| z>|^2, normalisé en distribution (somme=1)."""
    overlaps = torch.tensor(
        [torch.abs(torch.vdot(p / p.norm(), z)).item() ** 2 for p in patterns]
    )
    return overlaps / overlaps.sum()


def participation_entropy(p: torch.Tensor) -> tuple[float, float]:
    """Entropie de Shannon (nats) et nombre de participation effectif exp(S)."""
    p_safe = p.clamp(min=1e-12)
    s = -(p_safe * p_safe.log()).sum().item()
    return s, math.exp(s)


def main() -> None:
    patterns = find_n_basins(LANDSCAPE_SEED, N_BASINS)
    w = build_n_pattern_weights(patterns, zero_diagonal=True)

    z0 = patterns[0] / patterns[0].norm()
    print(f"{N_BASINS} bassins réels (paysage seed={LANDSCAPE_SEED}), "
          f"état initial localisé dans le bassin 0.\n")
    print(f"{'dt (=t/Y)':>10}  {'entropie S':>11}  {'N_eff':>7}  poids par bassin")

    rows = []
    for dt in DT_GRID:
        u = evolution_operator(w, dt)
        z_t = u @ z0.to(torch.complex64) if dt > 0 else z0.to(torch.complex64)
        weights = participation_weights(patterns, z_t)
        s, n_eff = participation_entropy(weights)
        rows.append({"dt": dt, "entropy": s, "n_eff": n_eff, "weights": weights.tolist()})
        w_str = " ".join(f"{v:.2f}" for v in weights.tolist())
        print(f"{dt:>10.2f}  {s:>11.4f}  {n_eff:>7.3f}  [{w_str}]")

    print(f"\nEntropie maximale possible (distribution uniforme sur {N_BASINS}) : "
          f"{math.log(N_BASINS):.4f} (N_eff={N_BASINS})")

    out_path = Path(__file__).parent.parent / "docs" / "results" / "n_basin_superposition_2026-09-20.json"
    out_path.write_text(json.dumps({
        "landscape_seed": LANDSCAPE_SEED,
        "n_basins": N_BASINS,
        "dt_grid": DT_GRID,
        "max_entropy": math.log(N_BASINS),
        "rows": rows,
    }, indent=2))
    print(f"\nRésultat archivé : {out_path}")


if __name__ == "__main__":
    main()
