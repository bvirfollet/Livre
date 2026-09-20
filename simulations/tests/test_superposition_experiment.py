"""Tests pour la génération de motifs et l'orchestration I-05
(cf. src/superposition/experiment.py)."""

import torch

from src.superposition.experiment import (
    generate_patterns,
    run_confirmatory_binomial_test,
    run_multi_realization_exact,
    run_nN_protocol,
)
from tests.conftest import ATOL, RTOL


def test_generate_patterns_unit_norm_and_deterministic():
    p1a, p2a = generate_patterns(5, seed=42)
    p1b, p2b = generate_patterns(5, seed=42)

    assert torch.allclose(p1a.norm(), torch.tensor(1.0), atol=ATOL, rtol=RTOL)
    assert torch.allclose(p2a.norm(), torch.tensor(1.0), atol=ATOL, rtol=RTOL)
    assert torch.allclose(p1a, p1b, atol=ATOL, rtol=RTOL)
    assert torch.allclose(p2a, p2b, atol=ATOL, rtol=RTOL)


def test_generate_patterns_different_seed_gives_different_patterns():
    p1a, _ = generate_patterns(5, seed=1)
    p1b, _ = generate_patterns(5, seed=2)
    assert not torch.allclose(p1a, p1b, atol=ATOL, rtol=RTOL)


def test_run_multi_realization_exact_shape_and_no_seed_collision():
    results_a = run_multi_realization_exact(n_nodes=3, n_realizations=5)
    results_b = run_multi_realization_exact(n_nodes=10, n_realizations=5)

    assert len(results_a) == 5
    seeds_a = {r["pattern_seed"] for r in results_a}
    seeds_b = {r["pattern_seed"] for r in results_b}
    assert len(seeds_a) == 5  # pas de doublon entre réalisations
    assert seeds_a.isdisjoint(seeds_b)  # pas de recoupement entre nN

    for r in results_a:
        assert "k3_global" in r and "k3_local" in r


def test_run_confirmatory_binomial_test_smoke_small_n():
    """Vérifie la forme du résultat sur un petit nombre de tirages (le test
    complet réel utilise n_realizations plus grand, cf. docs/DevPlan.md)."""
    result = run_confirmatory_binomial_test(n_nodes=3, n_realizations=3, sigma_target=5.0)
    assert result["n_nodes"] == 3
    assert result["n_realizations"] == 3
    assert len(result["per_draw"]) == 3
    assert 0 <= result["k_successes"] <= 3
    assert 0.0 <= result["p_value"] <= 1.0
    # p_null doit être minuscule (taux de faux positif à 5σ)
    assert result["p_null"] < 1e-5


def test_run_nN_protocol_smoke_small_m():
    """Vérifie juste la forme du résultat (pas de run statistique complet
    ici, M réduit pour la vitesse du test)."""
    result = run_nN_protocol(n_nodes=3, m_samples=20)
    assert result["n_nodes"] == 3
    assert "sigma" in result["global"]
    assert "sigma" in result["local"]
    assert len(result["local"]["per_node"]) == 3
