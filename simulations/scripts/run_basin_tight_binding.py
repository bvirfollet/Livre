"""K_ana faible / Y dominant — Hamiltonien de liaison forte (tight-binding)
sur le vrai paysage `E(x)` entre bassins voisins, cf. docs/DevPlan.md.

Corrige le défaut de la construction hebbienne (norme égale imposée par
RMSNorm, effaçant le relief réel) via une chaîne dont l'énergie sur site
est la vraie énergie composite le long d'un chemin interpolé.

**Correction du 2026-09-20 (second run)** : le nombre de sites `N` est
désormais proportionnel à la distance euclidienne réelle entre les deux
bassins (pas fixé arbitrairement) — pas physique par site constant
(`DELTA_S_PHYS`), pour que le même `hopping` nominal représente le même
couplage physique quelle que soit la paire. Échantillon élargi (toutes
les paires adjacentes de 3 paysages, pas seulement 3 paires d'un seul).
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

D_MODEL, D_FF, T_TOKENS, BETA, RELAX_STEPS = 16, 32, 5, 1.0, 60
LANDSCAPE_SEEDS = [14, 201, 202]
DELTA_S_PHYS = 0.5  # pas physique constant par site (unité de ||x||)
N_MIN, N_MAX = 10, 60
HOPPING_VALUES = [0.01, 0.1]


def map_basins(landscape_seed: int) -> dict:
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
            converged.append((e, x_real, x_imag))

    converged.sort(key=lambda t: t[0])
    basins = []
    for e, xr, xi in converged:
        if basins and (e - basins[-1][0]) < 0.5:
            continue
        basins.append((e, xr, xi))

    pairs = []
    for i in range(len(basins) - 1):
        gap = basins[i + 1][0] - basins[i][0]
        if gap >= 0.05:
            pairs.append((gap, basins[i], basins[i + 1]))

    return {"k_real": k_real, "k_imag": k_imag, "ffn": ffn, "pairs": pairs}


def build_path_energies(
    xr_a, xi_a, xr_b, xi_b, k_real, k_imag, ffn, n_points: int
) -> torch.Tensor:
    norm = HermitianRMSNorm(D_MODEL)
    norm.eval()
    energies = []
    with torch.no_grad():
        for n in range(n_points + 1):
            s = n / n_points
            x_real = (1 - s) * xr_a + s * xr_b
            x_imag = (1 - s) * xi_a + s * xi_b
            x_real, x_imag = norm(x_real, x_imag)
            e = full_stack_state_energy(x_real, x_imag, k_real, k_imag, BETA, ffn)
            energies.append(e)
    return torch.tensor(energies)


def tight_binding_delta_split(on_site: torch.Tensor, hopping: float) -> float:
    n = on_site.shape[0]
    h = torch.diag(on_site.clone())
    for i in range(n - 1):
        h[i, i + 1] = -hopping
        h[i + 1, i] = -hopping
    eigvals = torch.linalg.eigvalsh(h)
    return (eigvals[1] - eigvals[0]).item()


def pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return cov / (sx * sy) if sx > 0 and sy > 0 else float("nan")


def main() -> None:
    all_rows = []
    for landscape_seed in LANDSCAPE_SEEDS:
        data = map_basins(landscape_seed)
        k_real, k_imag, ffn = data["k_real"], data["k_imag"], data["ffn"]
        print(f"paysage seed={landscape_seed}: {len(data['pairs'])} paires adjacentes")

        for gap, (e_a, xr_a, xi_a), (e_b, xr_b, xi_b) in data["pairs"]:
            distance = torch.sqrt((xr_a - xr_b).pow(2).sum() + (xi_a - xi_b).pow(2).sum()).item()
            n_points = int(min(N_MAX, max(N_MIN, round(distance / DELTA_S_PHYS))))

            on_site = build_path_energies(xr_a, xi_a, xr_b, xi_b, k_real, k_imag, ffn, n_points)
            ref = max(on_site[0].item(), on_site[-1].item())
            barrier_height = (on_site.max().item() - ref)
            sqrt_action = sum(max(0.0, v - ref) ** 0.5 for v in on_site.tolist())

            row = {
                "landscape_seed": landscape_seed,
                "gap": gap,
                "distance": distance,
                "n_points": n_points,
                "barrier_height": barrier_height,
                "sqrt_action": sqrt_action,
            }
            for t in HOPPING_VALUES:
                row[f"delta_split_h{t}"] = tight_binding_delta_split(on_site, t)
            all_rows.append(row)

    print(f"\n{len(all_rows)} paires testées au total (pas physique constant = {DELTA_S_PHYS}).\n")
    print(f"{'seed':>6} {'N':>4} {'dist':>7} {'barrier':>8} {'action':>8} "
          f"{'split(h=0.01)':>14} {'split(h=0.1)':>13}")
    for r in all_rows:
        print(f"{r['landscape_seed']:>6} {r['n_points']:>4} {r['distance']:>7.2f} "
              f"{r['barrier_height']:>8.2f} {r['sqrt_action']:>8.2f} "
              f"{r['delta_split_h0.01']:>14.6f} {r['delta_split_h0.1']:>13.6f}")

    barriers = [r["barrier_height"] for r in all_rows]
    actions = [r["sqrt_action"] for r in all_rows]
    splits_001 = [r["delta_split_h0.01"] for r in all_rows]
    splits_01 = [r["delta_split_h0.1"] for r in all_rows]
    log_splits_001 = [math.log(max(s, 1e-12)) for s in splits_001]

    print(f"\nCorrélation (Pearson) barrier_height vs delta_split(h=0.01) : {pearson(barriers, splits_001):.3f}")
    print(f"Corrélation (Pearson) sqrt_action vs delta_split(h=0.01)    : {pearson(actions, splits_001):.3f}")
    print(f"Corrélation (Pearson) sqrt_action vs log(delta_split(h=0.01)) : {pearson(actions, log_splits_001):.3f}")
    print(f"Corrélation (Pearson) barrier_height vs delta_split(h=0.1)  : {pearson(barriers, splits_01):.3f}")

    out_path = Path(__file__).parent.parent / "docs" / "results" / "basin_tight_binding_2026-09-20.json"
    out_path.write_text(json.dumps({
        "delta_s_phys": DELTA_S_PHYS,
        "landscape_seeds": LANDSCAPE_SEEDS,
        "hopping_values": HOPPING_VALUES,
        "rows": all_rows,
        "correlations": {
            "barrier_vs_split_h0.01": pearson(barriers, splits_001),
            "action_vs_split_h0.01": pearson(actions, splits_001),
            "action_vs_log_split_h0.01": pearson(actions, log_splits_001),
            "barrier_vs_split_h0.1": pearson(barriers, splits_01),
        },
    }, indent=2))
    print(f"\nRésultat archivé : {out_path}")


if __name__ == "__main__":
    main()
