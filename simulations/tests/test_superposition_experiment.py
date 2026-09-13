"""Tests pour la génération de motifs et l'orchestration I-05
(cf. src/superposition/experiment.py)."""

import torch

from src.superposition.experiment import generate_patterns, run_nN_protocol
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


def test_run_nN_protocol_smoke_small_m():
    """Vérifie juste la forme du résultat (pas de run statistique complet
    ici, M réduit pour la vitesse du test)."""
    result = run_nN_protocol(n_nodes=3, m_samples=20)
    assert result["n_nodes"] == 3
    assert "sigma" in result["global"]
    assert "sigma" in result["local"]
    assert len(result["local"]["per_node"]) == 3
