"""Tests structurels pour les embeddings natifs (cf. docs/SW_Design.md).
Le portage de poids réel est testé bout-en-bout dans test_weights.py."""

import math

import torch

from src.hermitian.embeddings import HermitianEmbeddings, sinusoidal_position_imag_init
from src.hermitian.norm import HermitianLayerNorm, HermitianRMSNorm
from tests.conftest import ATOL, RTOL


def test_position_embeddings_imag_is_sinusoidal_by_default():
    """Correctif du 2026-09-25 : position_embeddings_imag n'est plus du
    bruit gaussien non structuré, mais sin(pos·ωₖ)."""
    emb = HermitianEmbeddings(
        vocab_size=50, d_model=8, max_position_embeddings=16, type_vocab_size=2
    )
    weight = emb.position_embeddings_imag.weight.detach()

    positions = torch.arange(16, dtype=torch.float32).unsqueeze(1)
    dims = torch.arange(8, dtype=torch.float32).unsqueeze(0)
    omega = 1.0 / (10000.0 ** (dims / 8))
    expected = torch.sin(positions * omega)

    assert torch.allclose(weight, expected, atol=ATOL, rtol=RTOL)
    # garde-fou de non-vacuité : à pos=0 tout vaut 0 (sin(0)=0), il faut
    # vérifier ailleurs qu'à pos=0 pour que le test soit significatif
    assert weight[1].abs().max().item() > 0.0


def test_sinusoidal_position_imag_init_reusable_standalone():
    """La fonction d'initialisation reste utilisable isolément (pas
    seulement via le constructeur)."""
    embedding = torch.nn.Embedding(10, 4)
    sinusoidal_position_imag_init(embedding, d_model=4)
    assert not torch.isnan(embedding.weight).any()
    expected_at_pos2_dim0 = math.sin(2 * 1.0)  # omega_0 = 1/10000^0 = 1
    assert abs(embedding.weight[2, 0].item() - expected_at_pos2_dim0) < 1e-5


def test_embeddings_forward_shape_and_finite():
    emb = HermitianEmbeddings(
        vocab_size=50, d_model=8, max_position_embeddings=16, type_vocab_size=2
    )
    input_ids = torch.randint(0, 50, (2, 5))

    out_real, out_imag = emb(input_ids)

    assert out_real.shape == (2, 5, 8)
    assert out_imag.shape == (2, 5, 8)
    assert torch.isfinite(out_real).all() and torch.isfinite(out_imag).all()


def test_embeddings_default_position_and_token_type_ids():
    """Sans position_ids/token_type_ids explicites : arange(seq_len) et
    zéros, comme HuggingFace."""
    emb = HermitianEmbeddings(
        vocab_size=50, d_model=8, max_position_embeddings=16, type_vocab_size=2
    )
    input_ids = torch.randint(0, 50, (2, 5))
    position_ids = torch.arange(5).unsqueeze(0).expand(2, -1)
    token_type_ids = torch.zeros_like(input_ids)

    out_real_default, out_imag_default = emb(input_ids)
    out_real_explicit, out_imag_explicit = emb(input_ids, token_type_ids, position_ids)

    assert torch.allclose(out_real_default, out_real_explicit, atol=ATOL, rtol=RTOL)
    assert torch.allclose(out_imag_default, out_imag_explicit, atol=ATOL, rtol=RTOL)


def test_embeddings_im_zero_stays_zero_when_no_source_of_phase():
    emb = HermitianEmbeddings(
        vocab_size=50, d_model=8, max_position_embeddings=16, type_vocab_size=2,
        norm_cls=HermitianLayerNorm,
    )
    with torch.no_grad():
        emb.word_embeddings_imag.weight.zero_()
        emb.position_embeddings_imag.weight.zero_()
        emb.token_type_embeddings_imag.weight.zero_()
        emb.norm.bias_imag.zero_()

    input_ids = torch.randint(0, 50, (2, 5))
    out_real, out_imag = emb(input_ids)

    assert torch.allclose(out_imag, torch.zeros_like(out_imag), atol=ATOL, rtol=RTOL)


def test_embeddings_works_with_rmsnorm_variant():
    emb = HermitianEmbeddings(
        vocab_size=50, d_model=8, max_position_embeddings=16, type_vocab_size=2,
        norm_cls=HermitianRMSNorm,
    )
    input_ids = torch.randint(0, 50, (2, 5))

    out_real, out_imag = emb(input_ids)

    assert torch.isfinite(out_real).all() and torch.isfinite(out_imag).all()
