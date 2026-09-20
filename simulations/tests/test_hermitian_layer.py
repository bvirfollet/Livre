"""Tests pour l'empilement multi-couches (cf. docs/SW_Design.md).

Portée : tests structurels (forme, finitude, non-fuite de partie
imaginaire quand rien n'en introduit). Le portage de poids réel HuggingFace
au niveau couche/modèle complet (I-01 étendu) nécessite d'abord d'étendre
`WeightProjector` au FFN — non fait ici, cf. docs/TODO.md.
"""

import torch

from src.hermitian.complex_linear import ComplexLinear
from src.hermitian.layer import HermitianBertLayer, HermitianBertModel
from src.hermitian.norm import HermitianLayerNorm, HermitianRMSNorm
from tests.conftest import ATOL, RTOL


def _zero_imaginary_weights(module: torch.nn.Module) -> None:
    """Met à zéro toute composante imaginaire des poids (ComplexLinear et
    Norm), pour vérifier qu'aucune fuite Re->Im n'est introduite par la
    structure de la couche elle-même (indépendamment de tout portage réel
    de poids HuggingFace)."""
    with torch.no_grad():
        for m in module.modules():
            if isinstance(m, ComplexLinear):
                m.fc_imag.weight.zero_()
                m.bias_imag.zero_()
            elif isinstance(m, HermitianLayerNorm):
                m.bias_imag.zero_()
            # HermitianRMSNorm n'a pas de composante imaginaire de poids.


def test_layer_forward_shape_and_finite():
    d_model = 8
    layer = HermitianBertLayer(d_model=d_model, num_heads=2)
    x_real = torch.randn(2, 5, d_model)
    x_imag = torch.randn(2, 5, d_model)

    out_real, out_imag = layer(x_real, x_imag)

    assert out_real.shape == (2, 5, d_model)
    assert out_imag.shape == (2, 5, d_model)
    assert torch.isfinite(out_real).all() and torch.isfinite(out_imag).all()


def test_layer_im_zero_stays_zero_when_no_source_of_phase():
    """Avec x_imag=0 et toutes les composantes imaginaires des poids à
    zéro, la couche ne doit introduire aucune partie imaginaire — sinon
    une fuite Re->Im existerait dans la structure elle-même (indépendante
    du portage de poids réels)."""
    d_model = 8
    layer = HermitianBertLayer(d_model=d_model, num_heads=2, norm_cls=HermitianLayerNorm)
    _zero_imaginary_weights(layer)

    x_real = torch.randn(2, 5, d_model)
    x_imag = torch.zeros(2, 5, d_model)

    out_real, out_imag = layer(x_real, x_imag)

    assert torch.allclose(out_imag, torch.zeros_like(out_imag), atol=ATOL, rtol=RTOL)
    assert torch.isfinite(out_real).all()


def test_layer_works_with_rmsnorm_variant():
    d_model = 8
    layer = HermitianBertLayer(d_model=d_model, num_heads=2, norm_cls=HermitianRMSNorm)
    x_real = torch.randn(2, 5, d_model)
    x_imag = torch.randn(2, 5, d_model)

    out_real, out_imag = layer(x_real, x_imag)

    assert torch.isfinite(out_real).all() and torch.isfinite(out_imag).all()


def test_model_stack_shape_and_finite():
    d_model = 8
    model = HermitianBertModel(d_model=d_model, num_heads=2, num_layers=3)
    x_real = torch.randn(2, 5, d_model)
    x_imag = torch.randn(2, 5, d_model)

    out_real, out_imag = model(x_real, x_imag)

    assert out_real.shape == (2, 5, d_model)
    assert out_imag.shape == (2, 5, d_model)
    assert torch.isfinite(out_real).all() and torch.isfinite(out_imag).all()
    assert len(model.layers) == 3


def test_model_im_zero_stays_zero_across_all_layers():
    d_model = 8
    model = HermitianBertModel(d_model=d_model, num_heads=2, num_layers=3)
    _zero_imaginary_weights(model)

    x_real = torch.randn(2, 5, d_model)
    x_imag = torch.zeros(2, 5, d_model)

    out_real, out_imag = model(x_real, x_imag)

    assert torch.allclose(out_imag, torch.zeros_like(out_imag), atol=ATOL, rtol=RTOL)
