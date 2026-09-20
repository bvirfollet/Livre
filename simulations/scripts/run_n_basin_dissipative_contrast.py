"""Contraste régime unitaire (K_ana=0) vs dissipatif (K_ana>0) sur la
superposition à N=8 bassins, cf. docs/DevPlan.md.

**Second essai (2026-09-20)** : le premier essai (déphasage aléatoire,
sans collapse) donnait une entropie qui *montait* vers le maximum avec
`K_ana` — diagnostiqué comme une confusion entre l'entropie de la
moyenne d'ensemble (toujours plus grande, par concavité/Jensen) et la
moyenne des entropies individuelles. Corrigé ici par de véritables
événements de mesure projective répétés (règle de Born, effet Zénon
quantique) — `K_ana` est le taux (au sens Poisson) de ces événements,
pas l'écart-type d'un bruit de phase. Entropie calculée **par
trajectoire**, puis moyennée — pas l'inverse.
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
DT_TOTAL = 2.0
N_SUBSTEPS = 20
K_ANA_GRID = [0.0, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0]
M_TRAJECTORIES = 200
SEED = 777


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


def concept_basis(patterns: list[torch.Tensor]) -> torch.Tensor:
    """Base orthonormée alignée sur les motifs (QR) : colonnes 0..7
    couvrent span(patterns) (e_0=pattern_0 exactement), le reste
    complète arbitrairement. Sert de base de mesure — les projecteurs
    P_k=|e_k><e_k| sont les L_k (« projecteurs de concept »)."""
    d = patterns[0].shape[0]
    torch.manual_seed(0)
    mat = torch.stack(patterns, dim=1).to(torch.complex64)
    extra = torch.randn(d, d - len(patterns), dtype=torch.complex64)
    full = torch.cat([mat, extra], dim=1)
    q, _ = torch.linalg.qr(full)
    return q


def participation_weights(patterns: list[torch.Tensor], z: torch.Tensor) -> torch.Tensor:
    return torch.tensor(
        [torch.abs(torch.vdot(p / p.norm(), z)).item() ** 2 for p in patterns]
    )


def entropy_from_weights(w: torch.Tensor) -> tuple[float, float]:
    p = w / w.sum()
    p_safe = p.clamp(min=1e-12)
    s = -(p_safe * p_safe.log()).sum().item()
    return s, math.exp(s)


def run_zeno_trajectory(
    w: torch.Tensor, z0: torch.Tensor, k_ana: float, basis: torch.Tensor,
    n_named: int, generator: torch.Generator,
) -> torch.Tensor:
    """Évolution unitaire par petits pas, avec événement de mesure
    projective (règle de Born, base de concepts) à chaque pas avec
    probabilité `1-exp(-K_ana*dt_small)` (processus de Poisson)."""
    dt_small = DT_TOTAL / N_SUBSTEPS
    u_small = evolution_operator(w, dt_small)
    z = z0.clone().to(torch.complex64)
    p_measure = 1.0 - math.exp(-k_ana * dt_small) if k_ana > 0 else 0.0

    for _ in range(N_SUBSTEPS):
        z = u_small @ z
        if p_measure > 0 and torch.rand((), generator=generator).item() < p_measure:
            coeffs = basis.conj().T @ z  # <e_k|z> pour tous les k
            probs_named = coeffs[:n_named].abs() ** 2
            prob_rest = max(0.0, 1.0 - probs_named.sum().item())
            probs = torch.cat([probs_named, torch.tensor([prob_rest])])
            probs = probs.clamp(min=0.0)
            probs = probs / probs.sum()
            outcome = torch.multinomial(probs, 1, generator=generator).item()
            if outcome < n_named:
                z = basis[:, outcome].clone()
            else:
                z = z - basis[:, :n_named] @ coeffs[:n_named]
                z = z / z.norm()
    return z


def main() -> None:
    patterns = find_n_basins(LANDSCAPE_SEED, N_BASINS)
    w = build_n_pattern_weights(patterns, zero_diagonal=True)
    z0 = patterns[0] / patterns[0].norm()
    basis = concept_basis(patterns)

    generator = torch.Generator().manual_seed(SEED)

    print(f"{N_BASINS} bassins réels (paysage seed={LANDSCAPE_SEED}), "
          f"dt_total={DT_TOTAL}, {M_TRAJECTORIES} trajectoires par K_ana.\n")
    print(f"{'K_ana':>8}  {'<S> par trajectoire':>20}  {'<N_eff>':>9}")

    rows = []
    for k_ana in K_ANA_GRID:
        entropies = []
        for _ in range(M_TRAJECTORIES):
            z_t = run_zeno_trajectory(w, z0, k_ana, basis, N_BASINS, generator)
            weights = participation_weights(patterns, z_t)
            s, n_eff = entropy_from_weights(weights)
            entropies.append(s)
        mean_s = sum(entropies) / len(entropies)
        mean_n_eff = math.exp(mean_s)
        rows.append({"k_ana": k_ana, "mean_entropy": mean_s, "mean_n_eff": mean_n_eff})
        print(f"{k_ana:>8.2f}  {mean_s:>20.4f}  {mean_n_eff:>9.3f}")

    print(f"\nEntropie maximale possible (N=8) : {math.log(N_BASINS):.4f}")

    out_path = Path(__file__).parent.parent / "docs" / "results" / "n_basin_dissipative_contrast_2026-09-20.json"
    out_path.write_text(json.dumps({
        "landscape_seed": LANDSCAPE_SEED,
        "n_basins": N_BASINS,
        "dt_total": DT_TOTAL,
        "n_substeps": N_SUBSTEPS,
        "m_trajectories": M_TRAJECTORIES,
        "k_ana_grid": K_ANA_GRID,
        "max_entropy": math.log(N_BASINS),
        "rows": rows,
    }, indent=2))
    print(f"\nRésultat archivé : {out_path}")


if __name__ == "__main__":
    main()
