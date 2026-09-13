"""Harnais Monte-Carlo — test de Leggett-Garg généralisé à `nS` temps.

Protocole complet et seuils fixés dans `docs/DevPlan.md` (section
« Recherche — Superposition quantique »). Ce module implémente `nS=3`
(LG standard, `K(3)=C₁₂+C₂₃−C₁₃`), le cas retenu pour cette première
itération — cf. discussion du 2026-09-13.

Chaque paire de temps `(a,b)` est estimée sur un **sous-ensemble frais**
de `M` tirages indépendants (préparation identique `z0` à chaque tirage,
seule la mesure — règle de Born — introduit du hasard) : c'est la
condition de mesurabilité non invasive du test LG, qui interdit de
réutiliser un tirage pour plusieurs paires de temps.
"""

import math

import torch

from .dynamics import evolution_operator
from .measurement import measure

# Bornes classiques/quantiques pour nS=3 (Emary, Lambert & Nori, Rep. Prog.
# Phys. 77, 016001, 2014 ; cf. docs/DevPlan.md).
CLASSICAL_BOUND_K3 = 1.0
QUANTUM_BOUND_K3 = 3.0 * math.cos(math.pi / 3.0)  # = 1.5, résultat de Lüders


def two_time_correlation(
    z0: torch.Tensor,
    w: torch.Tensor,
    p_plus: torch.Tensor,
    p_minus: torch.Tensor,
    n_a: int,
    n_b: int,
    dt: float,
    m_samples: int,
    generator: torch.Generator | None = None,
) -> tuple[float, float]:
    """Estime `Cab = ⟨QₐQᵦ⟩` sur `m_samples` tirages indépendants.

    `n_a < n_b` : nombre d'itérations de Hopfield (le "temps", cf.
    `docs/DevPlan.md`) séparant chaque mesure de l'état initial `z0`.
    Retourne `(Ĉab, erreur_standard)`.
    """
    if n_a >= n_b:
        raise ValueError("n_a doit être strictement inférieur à n_b")

    u_to_a = evolution_operator(w, dt=n_a * dt) if n_a > 0 else None
    u_gap = evolution_operator(w, dt=(n_b - n_a) * dt)

    products = torch.empty(m_samples)
    for k in range(m_samples):
        z_a = (u_to_a @ z0) if u_to_a is not None else z0.clone()
        outcome_a, z_collapsed = measure(z_a, p_plus, p_minus, generator=generator)
        z_b = u_gap @ z_collapsed
        outcome_b, _ = measure(z_b, p_plus, p_minus, generator=generator)
        products[k] = outcome_a * outcome_b

    c_hat = products.mean().item()
    standard_error = products.std(unbiased=True).item() / math.sqrt(m_samples)
    return c_hat, standard_error


def leggett_garg_k3(
    z0: torch.Tensor,
    w: torch.Tensor,
    p_plus: torch.Tensor,
    p_minus: torch.Tensor,
    dt: float,
    m_samples: int,
    generator: torch.Generator | None = None,
) -> dict:
    """`K(3) = C₁₂+C₂₃−C₁₃`, budget total `3×m_samples` (un sous-ensemble
    frais par paire de temps, cf. docstring du module).

    Retourne un dict avec `k3`, `standard_error` (somme quadratique des 3
    erreurs — les 3 sous-ensembles sont indépendants), et le détail des
    corrélations.
    """
    c12, se12 = two_time_correlation(z0, w, p_plus, p_minus, 0, 1, dt, m_samples, generator)
    c23, se23 = two_time_correlation(z0, w, p_plus, p_minus, 1, 2, dt, m_samples, generator)
    c13, se13 = two_time_correlation(z0, w, p_plus, p_minus, 0, 2, dt, m_samples, generator)

    k3 = c12 + c23 - c13
    standard_error = math.sqrt(se12**2 + se23**2 + se13**2)

    return {
        "k3": k3,
        "standard_error": standard_error,
        "C12": c12,
        "C23": c23,
        "C13": c13,
    }


def exact_two_time_correlation(
    z0: torch.Tensor,
    w: torch.Tensor,
    p_plus: torch.Tensor,
    p_minus: torch.Tensor,
    n_a: int,
    n_b: int,
    dt: float,
) -> float:
    """`Cab` calculé exactement à partir des probabilités de Born (pas de
    tirage Monte-Carlo) — sert de référence de régression indépendante du
    bruit d'échantillonnage (cf. I-04, `docs/test_plan.md`).

    `E[QₐQᵦ] = Σ_{qₐ,qᵦ∈{±1}} qₐ·qᵦ·P(qₐ)·P(qᵦ|qₐ)`.
    """
    if n_a >= n_b:
        raise ValueError("n_a doit être strictement inférieur à n_b")

    u_to_a = evolution_operator(w, dt=n_a * dt) if n_a > 0 else None
    z_a = (u_to_a @ z0) if u_to_a is not None else z0
    u_gap = evolution_operator(w, dt=(n_b - n_a) * dt)

    prob_a_plus = torch.real(torch.vdot(z_a, p_plus @ z_a)).item()
    prob_a_plus = min(max(prob_a_plus, 0.0), 1.0)
    prob_a_minus = 1.0 - prob_a_plus

    def _collapse(projector: torch.Tensor) -> torch.Tensor:
        collapsed = projector @ z_a
        return collapsed / collapsed.norm()

    def _prob_b_plus(z_after_collapse: torch.Tensor) -> float:
        z_b = u_gap @ z_after_collapse
        p = torch.real(torch.vdot(z_b, p_plus @ z_b)).item()
        return min(max(p, 0.0), 1.0)

    e_qb_given_a_plus = 2.0 * _prob_b_plus(_collapse(p_plus)) - 1.0
    e_qb_given_a_minus = 2.0 * _prob_b_plus(_collapse(p_minus)) - 1.0

    return prob_a_plus * e_qb_given_a_plus - prob_a_minus * e_qb_given_a_minus


def exact_leggett_garg_k3(
    z0: torch.Tensor, w: torch.Tensor, p_plus: torch.Tensor, p_minus: torch.Tensor, dt: float
) -> float:
    """`K(3)` exact — référence de régression, cf. `exact_two_time_correlation`."""
    c12 = exact_two_time_correlation(z0, w, p_plus, p_minus, 0, 1, dt)
    c23 = exact_two_time_correlation(z0, w, p_plus, p_minus, 1, 2, dt)
    c13 = exact_two_time_correlation(z0, w, p_plus, p_minus, 0, 2, dt)
    return c12 + c23 - c13


def aggregated_local_k3(
    z0: torch.Tensor,
    w: torch.Tensor,
    node_projectors: list[tuple[torch.Tensor, torch.Tensor]],
    dt: float,
    m_samples: int,
    generator: torch.Generator | None = None,
) -> dict:
    """`Q_i` agrégé sur `nN` nœuds (cf. `docs/DevPlan.md` — teste la
    superposition élémentaire sans faire exploser la famille de tests en
    testant chaque nœud individuellement).

    `node_projectors` : liste de `(p_plus_i, p_minus_i)`, une paire par
    nœud (cf. `patterns.local_axis` + `measurement.dichotomic_projectors`).
    Retourne la moyenne des `K(3)` par nœud et l'erreur standard agrégée
    (moyenne quadratique des erreurs, propagation pour une moyenne de `nN`
    variables indépendantes).
    """
    node_results = [
        leggett_garg_k3(z0, w, p_plus, p_minus, dt, m_samples, generator)
        for p_plus, p_minus in node_projectors
    ]
    n_nodes = len(node_results)
    mean_k3 = sum(r["k3"] for r in node_results) / n_nodes
    mean_standard_error = math.sqrt(sum(r["standard_error"] ** 2 for r in node_results)) / n_nodes

    return {
        "k3": mean_k3,
        "standard_error": mean_standard_error,
        "per_node": node_results,
    }


def significance_sigma(k3: float, standard_error: float, bound: float = CLASSICAL_BOUND_K3) -> float:
    """Nombre d'erreurs standard par lesquelles `|k3|` dépasse la borne
    classique (test unilatéral). Seuil de décision (5σ, correction de
    Bonferroni sur la famille de 10 tests) fixé dans `docs/DevPlan.md`,
    appliqué en aval de cette fonction, pas ici.
    """
    excess = abs(k3) - bound
    if standard_error == 0.0:
        return math.inf if excess > 0 else 0.0
    return excess / standard_error


def required_m_for_significance(delta: float, n_s: int = 3, z_target: float = 5.0) -> int:
    """`M` par corrélation nécessaire pour séparer la marge `delta`
    (violation attendue − borne classique) de `z_target` erreurs standard,
    en utilisant la borne conservative `σ_K ≤ √(nS/M)` (variance ≤1 par
    corrélation — cf. calcul de puissance de `docs/DevPlan.md`) :

        M ≥ z_target² · nS / delta²

    Conservative par construction : la variance réelle d'une corrélation
    `Cᵢⱼ` est `1−Cᵢⱼ² < 1` dès que `|Cᵢⱼ|>0`, donc le `M` réellement requis
    est en général plus petit que la valeur retournée ici.
    """
    if delta <= 0:
        raise ValueError("delta doit être strictement positif pour qu'un M fini existe")
    return math.ceil((z_target**2) * n_s / (delta**2))
