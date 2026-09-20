"""Mesure projective dichotomique (règle de Born) — observable Q=P₊−P₋.

`axis_state` définit le pôle `+1` de `Q` : dans le protocole du sous-track
Leggett-Garg, c'est la direction séparant deux motifs mémorisés concurrents
`ξ¹`, `ξ²` (cf. `docs/DevPlan.md`). Mesurer, ici, effondre réellement l'état
(collapse) — c'est le choix "protocole invasif standard" nécessaire pour
reproduire fidèlement la structure à sous-ensembles séparés du test LG
(cf. discussion du 2026-09-13, DevPlan.md).
"""

import torch


def dichotomic_projectors(axis_state: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Construit (P₊, P₋) à partir d'un état définissant le pôle +1.

    P₊ = |a⟩⟨a| (a = axis_state normalisé), P₋ = I − P₊.
    """
    axis_state = axis_state.to(torch.complex64)
    axis_state = axis_state / axis_state.norm()
    d = axis_state.shape[0]
    p_plus = torch.outer(axis_state, axis_state.conj())
    p_minus = torch.eye(d, dtype=torch.complex64) - p_plus
    return p_plus, p_minus


def measure(
    z: torch.Tensor,
    p_plus: torch.Tensor,
    p_minus: torch.Tensor,
    generator: torch.Generator | None = None,
) -> tuple[int, torch.Tensor]:
    """Mesure projective de Q=P₊−P₋ sur l'état z (règle de Born).

    Retourne (outcome ∈ {+1,-1}, état post-mesure collabé et renormalisé).
    """
    prob_plus = torch.real(torch.vdot(z, p_plus @ z)).item()
    prob_plus = min(max(prob_plus, 0.0), 1.0)  # clip du bruit flottant résiduel
    draw = torch.rand((), generator=generator).item()
    outcome = 1 if draw < prob_plus else -1
    projector = p_plus if outcome == 1 else p_minus
    collapsed = projector.to(z.dtype) @ z
    collapsed = collapsed / collapsed.norm()
    return outcome, collapsed
