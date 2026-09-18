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
from src.hermitian.layer import HermitianBertLayer  # noqa: E402
from src.hermitian.norm import HermitianLayerNorm  # noqa: E402
from src.weights.projector import project_bert_attention, project_bert_layer  # noqa: E402
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
