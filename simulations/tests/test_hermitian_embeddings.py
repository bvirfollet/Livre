"""Tests structurels pour les embeddings natifs (cf. docs/SW_Design.md).
Le portage de poids réel est testé bout-en-bout dans test_weights.py."""

import torch

from src.hermitian.embeddings import HermitianEmbeddings
from src.hermitian.norm import HermitianLayerNorm, HermitianRMSNorm
from tests.conftest import ATOL, RTOL


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
