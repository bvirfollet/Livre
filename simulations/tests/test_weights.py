"""Test d'intégration I-01 (cf. docs/test_plan.md) : portage de poids.

Portée initiale actée avec Bertrand le 2026-08-14 : bloc d'attention seul.
**Étendue le 2026-09-18** à la couche complète (attention + FFN + les deux
LayerNorm) une fois FFN/LayerNorm/empilement conçus (cf. docs/TODO.md) —
embeddings toujours hors scope.

Utilise `prajjwal1/bert-tiny` (checkpoint minuscule, mêmes noms/formes de
state_dict que bert-base-uncased, cf. docs/spike-weights-state-dict-mapping.md)
pour un test rapide ; nécessite un accès réseau au Hub HuggingFace.
"""

import pytest
import torch

transformers = pytest.importorskip("transformers")
from transformers import BertModel  # noqa: E402

from src.hermitian.attention import HermitianSelfAttention  # noqa: E402
from src.hermitian.embeddings import HermitianEmbeddings  # noqa: E402
from src.hermitian.layer import HermitianBertLayer, HermitianBertModel  # noqa: E402
from src.hermitian.norm import HermitianLayerNorm  # noqa: E402
from src.hopfield.equivalence import hopfield_step  # noqa: E402
from src.weights.projector import (  # noqa: E402
    project_bert_attention,
    project_bert_embeddings,
    project_bert_layer,
    project_bert_model,
)
from tests.conftest import ATOL, RTOL  # noqa: E402


@pytest.fixture(scope="module")
def hf_model():
    model = BertModel.from_pretrained("prajjwal1/bert-tiny")
    model.eval()
    return model


def test_i01_weight_portage_imag_zero_matches_classic_bert(hf_model):
    """Partie imaginaire forcée à 0 ⇒ sortie ≈ BertAttention HuggingFace
    (self-attention + output.dense, sans LayerNorm/résiduelle — absentes
    de HermitianSelfAttention, cf. portée actée ci-dessus)."""
    hf_attention = hf_model.encoder.layer[0].attention
    d_model = hf_model.config.hidden_size
    num_heads = hf_model.config.num_attention_heads

    module = HermitianSelfAttention(d_model=d_model, num_heads=num_heads)
    module.eval()
    project_bert_attention(module, hf_attention, imag_std=0.0)

    x_real = torch.randn(2, 5, d_model)
    x_imag = torch.zeros_like(x_real)

    with torch.no_grad():
        context_layer = hf_attention.self(x_real)[0]
        expected_real = hf_attention.output.dense(context_layer)

        out_real, out_imag, _ = module(x_real, x_imag)

    assert torch.allclose(out_real, expected_real, atol=ATOL, rtol=RTOL)
    assert torch.allclose(out_imag, torch.zeros_like(out_imag), atol=ATOL, rtol=RTOL)


def test_i01_extended_full_layer_matches_classic_bert(hf_model):
    """I-01 étendu (2026-09-18) : couche complète (attention + FFN + les
    deux LayerNorm, `HermitianLayerNorm` — portage-compatible, pas la
    `HermitianRMSNorm` par défaut). `Im=0` ⇒ sortie ≈ `BertLayer` HuggingFace
    complet (Post-LN, résiduelles incluses)."""
    hf_layer = hf_model.encoder.layer[0]
    d_model = hf_model.config.hidden_size
    num_heads = hf_model.config.num_attention_heads
    d_ff = hf_model.config.intermediate_size
    eps = hf_model.config.layer_norm_eps

    layer = HermitianBertLayer(
        d_model=d_model, num_heads=num_heads, d_ff=d_ff,
        norm_cls=HermitianLayerNorm, norm_eps=eps,
    )
    layer.eval()
    project_bert_layer(layer, hf_layer, imag_std=0.0)

    x_real = torch.randn(2, 5, d_model)
    x_imag = torch.zeros_like(x_real)

    with torch.no_grad():
        expected_real = hf_layer(x_real)
        out_real, out_imag = layer(x_real, x_imag)

    assert torch.allclose(out_real, expected_real, atol=ATOL, rtol=RTOL)
    assert torch.allclose(out_imag, torch.zeros_like(out_imag), atol=ATOL, rtol=RTOL)


def test_i01_embeddings_match_classic_bert(hf_model):
    """I-01 étendu aux embeddings (2026-09-18) : `Im=0` ⇒ sortie réelle ≈
    `BertEmbeddings` HuggingFace."""
    hf_embeddings = hf_model.embeddings
    config = hf_model.config

    embeddings = HermitianEmbeddings(
        vocab_size=config.vocab_size,
        d_model=config.hidden_size,
        max_position_embeddings=config.max_position_embeddings,
        type_vocab_size=config.type_vocab_size,
        norm_cls=HermitianLayerNorm,
        norm_eps=config.layer_norm_eps,
    )
    embeddings.eval()
    project_bert_embeddings(embeddings, hf_embeddings, imag_std=0.0)

    input_ids = torch.randint(0, config.vocab_size, (2, 5))

    with torch.no_grad():
        expected_real = hf_embeddings(input_ids)
        out_real, out_imag = embeddings(input_ids)

    assert torch.allclose(out_real, expected_real, atol=ATOL, rtol=RTOL)
    assert torch.allclose(out_imag, torch.zeros_like(out_imag), atol=ATOL, rtol=RTOL)


def test_i01_extended_full_model_matches_classic_bert(hf_model):
    """I-01 étendu au modèle empilé complet (2026-09-18) : embeddings +
    toutes les couches, `Im=0` ⇒ sortie ≈ `BertModel` HuggingFace complet
    (`embeddings` puis `encoder`, sans pooler — non porté)."""
    config = hf_model.config

    embeddings = HermitianEmbeddings(
        vocab_size=config.vocab_size,
        d_model=config.hidden_size,
        max_position_embeddings=config.max_position_embeddings,
        type_vocab_size=config.type_vocab_size,
        norm_cls=HermitianLayerNorm,
        norm_eps=config.layer_norm_eps,
    )
    model = HermitianBertModel(
        d_model=config.hidden_size,
        num_heads=config.num_attention_heads,
        num_layers=config.num_hidden_layers,
        d_ff=config.intermediate_size,
        norm_cls=HermitianLayerNorm,
        norm_eps=config.layer_norm_eps,
    )
    embeddings.eval()
    model.eval()
    project_bert_embeddings(embeddings, hf_model.embeddings, imag_std=0.0)
    project_bert_model(model, hf_model, imag_std=0.0)

    input_ids = torch.randint(0, config.vocab_size, (2, 5))

    with torch.no_grad():
        hf_emb_out = hf_model.embeddings(input_ids)
        expected_real = hf_model.encoder(hf_emb_out).last_hidden_state

        emb_real, emb_imag = embeddings(input_ids)
        out_real, out_imag = model(emb_real, emb_imag)

    assert torch.allclose(out_real, expected_real, atol=ATOL, rtol=RTOL)
    assert torch.allclose(out_imag, torch.zeros_like(out_imag), atol=ATOL, rtol=RTOL)


def test_layer_attention_subblock_still_hopfield_equivalent_after_assembly(hf_model):
    """Réponse partielle à la réserve de Bertrand (2026-09-18, `docs/TODO.md`) :
    le fil conducteur du projet est que BERT se ramène à un Hopfield
    (Ramsauer et al. 2020) plongé dans l'espace hermitien — validé en
    Phase 1 pour le bloc d'attention seul (`test_u03_equivalence_general_qkv`).
    Ce test vérifie que ça reste vrai une fois le bloc **assemblé** dans
    `HermitianBertLayer` et chargé avec de **vrais poids pré-entraînés**
    (bruit imaginaire non nul — régime complexe réel, pas seulement `Im=0`).

    Ne répond PAS à la question de la couche complète (FFN+Norm+résiduelle) :
    seul le sous-bloc attention, avant `out_proj`/résiduelle/norme, est
    testé ici. Voir `docs/TODO.md` pour la question ouverte plus large.
    """
    hf_layer = hf_model.encoder.layer[0]
    d_model = hf_model.config.hidden_size
    num_heads = hf_model.config.num_attention_heads
    d_ff = hf_model.config.intermediate_size

    layer = HermitianBertLayer(
        d_model=d_model, num_heads=num_heads, d_ff=d_ff, norm_cls=HermitianLayerNorm
    )
    layer.eval()
    project_bert_layer(layer, hf_layer, imag_std=1e-2)

    x_real = torch.randn(2, 5, d_model)
    x_imag = torch.randn(2, 5, d_model) * 1e-2
    beta = 1.0 / (d_model // num_heads) ** 0.5

    with torch.no_grad():
        attn = layer.attention
        q_r, q_i = attn._split_heads(*attn.q_proj(x_real, x_imag))
        k_r, k_i = attn._split_heads(*attn.k_proj(x_real, x_imag))
        v_r, v_i = attn._split_heads(*attn.v_proj(x_real, x_imag))

        hop_real, hop_imag, _ = hopfield_step(q_r, q_i, k_r, k_i, v_r, v_i, beta)
        merged_real, merged_imag = attn._merge_heads(hop_real, hop_imag)
        expected_real, expected_imag = attn.out_proj(merged_real, merged_imag)

        actual_real, actual_imag, _ = attn(x_real, x_imag)

    assert torch.allclose(actual_real, expected_real, atol=ATOL, rtol=RTOL)
    assert torch.allclose(actual_imag, expected_imag, atol=ATOL, rtol=RTOL)


def test_i01_imag_noise_leaves_real_part_unaffected_to_first_order_is_not_assumed(hf_model):
    """Garde-fou : avec un bruit imaginaire non nul, out_imag n'est plus nul
    (sinon project_bert_attention n'aurait aucun effet observable et le test
    ci-dessus serait vide de sens)."""
    hf_attention = hf_model.encoder.layer[0].attention
    d_model = hf_model.config.hidden_size
    num_heads = hf_model.config.num_attention_heads

    module = HermitianSelfAttention(d_model=d_model, num_heads=num_heads)
    module.eval()
    project_bert_attention(module, hf_attention, imag_std=1e-2)

    x_real = torch.randn(2, 5, d_model)
    x_imag = torch.zeros_like(x_real)

    with torch.no_grad():
        _, out_imag, _ = module(x_real, x_imag)

    assert out_imag.abs().max().item() > 0.0
