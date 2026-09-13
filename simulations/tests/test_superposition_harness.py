"""Test d'intégration I-04 (cf. docs/test_plan.md) : régression du harnais
Leggett-Garg contre des faits théoriques connus, *avant* tout run
statistique sur le modèle réseau (I-05).

On ne reproduit pas ici la paramétrisation exacte qui sature `K(3)=3/2`
(Lüders) — non retrouvée dans la source consultée pour ce sous-track. Les
deux faits vérifiés à la place sont plus modestes mais suffisent comme
garde-fous de régression :
  1. Sans évolution (dt=0), la mesure répétée est parfaitement corrélée à
     elle-même : K(3) doit valoir exactement la borne classique (1.0), ni
     plus ni moins — un bug de signe ferait déraper cette valeur triviale.
  2. Avec évolution cohérente, K(3) peut dépasser la borne classique, mais
     ne doit *jamais* dépasser la borne quantique maximale prouvée
     (3·cos(π/3)=1.5) — un bug de règle de Born pourrait sinon produire
     des violations non physiques au-delà de ce plafond.
"""

import math

import torch

from src.superposition.harness import (
    CLASSICAL_BOUND_K3,
    QUANTUM_BOUND_K3,
    aggregated_local_k3,
    exact_leggett_garg_k3,
    leggett_garg_k3,
    required_m_for_significance,
    significance_sigma,
)
from src.superposition.measurement import dichotomic_projectors
from src.superposition.patterns import build_two_pattern_weights, global_axis, local_axis
from tests.conftest import ATOL, RTOL

PATTERN1 = torch.tensor([1.0, 0.0], dtype=torch.complex64)
PATTERN2 = torch.tensor([1.0, 1.0], dtype=torch.complex64) / math.sqrt(2)


def _reference_system():
    w = build_two_pattern_weights(PATTERN1, PATTERN2, zero_diagonal=True)
    axis = global_axis(PATTERN1, PATTERN2)
    p_plus, p_minus = dichotomic_projectors(axis)
    z0 = PATTERN1.clone()
    return z0, w, p_plus, p_minus


def test_i04_k3_at_classical_bound_without_evolution():
    """dt=0 : aucune évolution entre les mesures ⇒ corrélation parfaite,
    K(3) doit tomber exactement sur la borne classique (1.0)."""
    z0, w, p_plus, p_minus = _reference_system()
    k3 = exact_leggett_garg_k3(z0, w, p_plus, p_minus, dt=0.0)
    assert math.isclose(k3, CLASSICAL_BOUND_K3, abs_tol=1e-4)


def test_i04_k3_never_exceeds_quantum_bound_and_can_violate_classical():
    """Balayage de `dt` : K(3) reste toujours ≤ borne quantique (1.5), et
    dépasse la borne classique (1.0) pour au moins une valeur de `dt`
    (démontre une violation réelle, pas seulement une absence de bug)."""
    z0, w, p_plus, p_minus = _reference_system()

    max_abs_k3 = 0.0
    violation_found = False
    for step in range(1, 40):
        dt = 0.1 * step
        k3 = exact_leggett_garg_k3(z0, w, p_plus, p_minus, dt=dt)
        assert abs(k3) <= QUANTUM_BOUND_K3 + 1e-4, (
            f"K(3)={k3} dépasse la borne quantique {QUANTUM_BOUND_K3} à dt={dt}"
        )
        max_abs_k3 = max(max_abs_k3, abs(k3))
        if abs(k3) > CLASSICAL_BOUND_K3:
            violation_found = True

    assert violation_found, "aucune violation de la borne classique observée sur le balayage"


def test_montecarlo_estimator_matches_exact_computation():
    """Le harnais Monte-Carlo (échantillonné) converge vers la valeur exacte
    (Born, sans bruit) à M grand — validation croisée avant tout run
    statistique réel (I-05)."""
    torch.manual_seed(42)
    z0, w, p_plus, p_minus = _reference_system()
    dt = 1.0

    exact = exact_leggett_garg_k3(z0, w, p_plus, p_minus, dt=dt)
    result = leggett_garg_k3(z0, w, p_plus, p_minus, dt=dt, m_samples=2000)

    # Tolérance dictée par le bruit d'échantillonnage (~standard_error),
    # pas par ATOL/RTOL (déterministe) — marge à 4 erreurs standard.
    assert abs(result["k3"] - exact) < 4 * result["standard_error"]


def test_aggregated_local_k3_shape_and_consistency():
    """`Q_i` agrégé : moyenne cohérente sur les nN=2 nœuds, erreur standard
    positive, présence du détail par nœud."""
    torch.manual_seed(7)
    z0, w, _p_plus, _p_minus = _reference_system()
    node_projectors = [
        dichotomic_projectors(local_axis(PATTERN1, PATTERN2, node=i)) for i in range(2)
    ]

    result = aggregated_local_k3(z0, w, node_projectors, dt=1.0, m_samples=200)

    assert len(result["per_node"]) == 2
    assert result["standard_error"] > 0.0
    manual_mean = sum(r["k3"] for r in result["per_node"]) / 2
    assert math.isclose(result["k3"], manual_mean, rel_tol=1e-9)


def test_required_m_for_significance_matches_hand_calculation():
    """Cas nS=3, delta=0.5 (marge théorique maximale) : M ≥ 25*3/0.25 = 300,
    valeur qui a servi à fixer le M=300 initial (cf. docs/DevPlan.md)."""
    assert required_m_for_significance(delta=0.5, n_s=3, z_target=5.0) == 300


def test_significance_sigma_sanity():
    """`significance_sigma` : à la borne classique exacte, 0σ ; nettement
    au-dessus, un score positif cohérent avec l'écart/erreur fournis."""
    assert significance_sigma(1.0, standard_error=0.1) == 0.0
    assert math.isclose(
        significance_sigma(1.5, standard_error=0.1), 5.0, rel_tol=1e-6
    )
    assert significance_sigma(0.5, standard_error=0.1) < 0.0
