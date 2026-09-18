"""Tests unitaires pour le FFN et la RMSNorm natifs (cf. docs/SW_Design.md,
correction du 2026-09-18 — architecture vectorielle, pas matricielle).

Invariant central testé : la préservation de la phase, analogue de
l'hermiticité pour ces deux composants (cf. `gating.py`, `norm.py`).
"""

import math

import torch

from src.hermitian.ffn import HermitianFFN
from src.hermitian.gating import phase_preserving_gate
from src.hermitian.norm import HermitianLayerNorm, HermitianRMSNorm
from tests.conftest import ATOL, RTOL


def _phase(real: torch.Tensor, imag: torch.Tensor) -> torch.Tensor:
    return torch.atan2(imag, real)


def test_phase_preserving_gate_hand_n2():
    """Cas N=2 à la main : z=[3+4j, 0].
    |z0|=5, GELU(5)≈5 (GELU(x)→x pour x grand), donc g(z0)≈z0.
    z1=0 : gate ne doit pas produire de NaN, sortie doit être 0.
    """
    z_real = torch.tensor([3.0, 0.0])
    z_imag = torch.tensor([4.0, 0.0])

    out_real, out_imag = phase_preserving_gate(z_real, z_imag)

    assert torch.isfinite(out_real).all() and torch.isfinite(out_imag).all()
    assert torch.allclose(out_real[1], torch.tensor(0.0), atol=ATOL, rtol=RTOL)
    assert torch.allclose(out_imag[1], torch.tensor(0.0), atol=ATOL, rtol=RTOL)

    # GELU(5) ≈ 5.0 (à ~1e-6 près, la queue gaussienne est négligeable) :
    # g(z0) ≈ z0, donc phase et magnitude quasi inchangées.
    gelu_5 = torch.nn.functional.gelu(torch.tensor(5.0)).item()
    expected_real0 = gelu_5 * 3.0 / 5.0
    expected_imag0 = gelu_5 * 4.0 / 5.0
    assert torch.allclose(out_real[0], torch.tensor(expected_real0), atol=ATOL, rtol=RTOL)
    assert torch.allclose(out_imag[0], torch.tensor(expected_imag0), atol=ATOL, rtol=RTOL)


def test_phase_preserving_gate_preserves_phase_random():
    z_real = torch.randn(20)
    z_imag = torch.randn(20)
    # Écarte les entrées trop proches de 0 (phase mal définie/instable
    # numériquement à cette échelle) — pas une faiblesse du gate lui-même.
    mask = (z_real**2 + z_imag**2) > 1e-4
    z_real, z_imag = z_real[mask], z_imag[mask]

    out_real, out_imag = phase_preserving_gate(z_real, z_imag)

    assert torch.allclose(_phase(z_real, z_imag), _phase(out_real, out_imag), atol=1e-4, rtol=1e-4)


def test_hermitian_ffn_forward_shape_and_finite():
    d_model = 8
    ffn = HermitianFFN(d_model)
    x_real = torch.randn(2, 5, d_model)
    x_imag = torch.randn(2, 5, d_model)

    out_real, out_imag = ffn(x_real, x_imag)

    assert out_real.shape == (2, 5, d_model)
    assert out_imag.shape == (2, 5, d_model)
    assert torch.isfinite(out_real).all() and torch.isfinite(out_imag).all()


def test_rmsnorm_hand_n2():
    """Cas N=2 à la main : z=[3+4j, 0], gamma=1.
    RMS = sqrt(mean(|z|^2)) = sqrt((9+16+0+0)/2) = sqrt(12.5).
    Sortie attendue : z / sqrt(12.5) (phase inchangée pour z0, z1 reste 0).
    """
    norm = HermitianRMSNorm(d_model=2, eps=0.0)
    x_real = torch.tensor([[3.0, 0.0]])
    x_imag = torch.tensor([[4.0, 0.0]])

    out_real, out_imag = norm(x_real, x_imag)

    rms = math.sqrt(12.5)
    assert torch.allclose(out_real, torch.tensor([[3.0 / rms, 0.0]]), atol=ATOL, rtol=RTOL)
    assert torch.allclose(out_imag, torch.tensor([[4.0 / rms, 0.0]]), atol=ATOL, rtol=RTOL)

    # Phase de z0 inchangée.
    assert torch.allclose(
        _phase(x_real[:, 0], x_imag[:, 0]), _phase(out_real[:, 0], out_imag[:, 0]),
        atol=ATOL, rtol=RTOL,
    )


def test_rmsnorm_output_rms_is_gamma():
    """Avec gamma=1 partout et eps→0, le RMS de la sortie doit valoir 1
    exactement (invariant structurel de la RMSNorm, indépendant de x)."""
    d_model = 16
    norm = HermitianRMSNorm(d_model, eps=0.0)
    x_real = torch.randn(4, d_model)
    x_imag = torch.randn(4, d_model)

    out_real, out_imag = norm(x_real, x_imag)

    output_rms = torch.sqrt((out_real**2 + out_imag**2).mean(dim=-1))
    assert torch.allclose(output_rms, torch.ones(4), atol=1e-5, rtol=1e-4)


def test_layernorm_reduces_to_real_layernorm_when_im_zero():
    """Portage-compatible : Im=0 partout, bias_imag=0 (init par défaut)
    ⇒ identique à nn.LayerNorm(x_real) — même test de régression que
    ComplexLinear/WeightProjector (I-01)."""
    d_model = 6
    eps = 1e-5
    hermitian_ln = HermitianLayerNorm(d_model, eps=eps)
    real_ln = torch.nn.LayerNorm(d_model, eps=eps)
    with torch.no_grad():
        hermitian_ln.gamma.copy_(real_ln.weight)
        hermitian_ln.bias_real.copy_(real_ln.bias)

    x_real = torch.randn(3, d_model)
    x_imag = torch.zeros(3, d_model)

    out_real, out_imag = hermitian_ln(x_real, x_imag)
    expected = real_ln(x_real)

    assert torch.allclose(out_real, expected, atol=ATOL, rtol=RTOL)
    assert torch.allclose(out_imag, torch.zeros_like(out_imag), atol=ATOL, rtol=RTOL)


def test_layernorm_hand_n2():
    """Cas N=2 à la main : x=[1,3] (réel), gamma=1, bias=0.
    mean=2, centré=[-1,1], variance=mean([1,1])=1, std≈1 ⇒ sortie=[-1,1]."""
    ln = HermitianLayerNorm(d_model=2, eps=0.0)
    x_real = torch.tensor([[1.0, 3.0]])
    x_imag = torch.tensor([[0.0, 0.0]])

    out_real, out_imag = ln(x_real, x_imag)

    assert torch.allclose(out_real, torch.tensor([[-1.0, 1.0]]), atol=ATOL, rtol=RTOL)
    assert torch.allclose(out_imag, torch.zeros_like(out_imag), atol=ATOL, rtol=RTOL)


def test_layernorm_does_not_preserve_phase_in_general():
    """Contrairement à RMSNorm, le centrage complexe déplace la phase
    individuelle de chaque composante — vérifie que ce n'est pas
    silencieusement redevenu faux (documentation du compromis, 2026-09-18)."""
    d_model = 6
    ln = HermitianLayerNorm(d_model, eps=1e-8)
    x_real = torch.randn(1, d_model)
    x_imag = torch.randn(1, d_model)

    out_real, out_imag = ln(x_real, x_imag)

    phase_in = torch.atan2(x_imag, x_real)
    phase_out = torch.atan2(out_imag, out_real)
    assert not torch.allclose(phase_in, phase_out, atol=1e-3, rtol=1e-3)


def test_layernorm_blind_to_dc_shift_but_not_rmsnorm():
    """Vérifie empiriquement la prédiction analytique du 2026-09-18 : le
    centrage de LayerNorm annule spécifiquement la sensibilité au
    décalage uniforme (ε·𝟙), sans réduire la discrimination pour une
    perturbation orthogonale (moyenne nulle) — RMSNorm reste sensible aux
    deux. Ce n'est donc pas une perte générale de discernement, mais une
    insensibilité ciblée à une seule direction (cf. docs/DevPlan.md,
    discussion sur le rôle du centrage pour l'attention par produit
    scalaire sur des poids pré-entraînés)."""
    d_model = 8
    epsilon = 0.05
    z0_real = torch.randn(1, d_model)
    z0_imag = torch.randn(1, d_model)

    u_dc = torch.ones(1, d_model) / (d_model**0.5)
    v = torch.randn(1, d_model)
    v = v - v.mean(dim=-1, keepdim=True)
    v = v / v.norm(dim=-1, keepdim=True)

    rmsnorm = HermitianRMSNorm(d_model, eps=1e-8)
    layernorm = HermitianLayerNorm(d_model, eps=1e-8)

    def distance(norm_module, real_b):
        out_a_real, out_a_imag = norm_module(z0_real, z0_imag)
        out_b_real, out_b_imag = norm_module(real_b, z0_imag)
        return torch.sqrt((out_a_real - out_b_real) ** 2 + (out_a_imag - out_b_imag) ** 2).sum()

    d_dc_ln = distance(layernorm, z0_real + epsilon * u_dc)
    d_dc_rms = distance(rmsnorm, z0_real + epsilon * u_dc)
    d_orth_ln = distance(layernorm, z0_real + epsilon * v)
    d_orth_rms = distance(rmsnorm, z0_real + epsilon * v)

    assert torch.allclose(d_dc_ln, torch.tensor(0.0), atol=1e-5)
    assert d_dc_rms > 1e-3
    # Les deux normes discriminent la perturbation orthogonale dans le
    # même ordre de grandeur (pas de perte structurelle sous RMSNorm).
    assert d_orth_rms > 1e-3
    assert d_orth_ln > 1e-3
    assert 0.3 < (d_orth_rms / d_orth_ln) < 3.0


def test_rmsnorm_preserves_phase_random():
    d_model = 10
    norm = HermitianRMSNorm(d_model, eps=1e-8)
    x_real = torch.randn(3, d_model)
    x_imag = torch.randn(3, d_model)
    mask = (x_real**2 + x_imag**2) > 1e-4

    out_real, out_imag = norm(x_real, x_imag)

    assert torch.allclose(
        _phase(x_real[mask], x_imag[mask]), _phase(out_real[mask], out_imag[mask]),
        atol=1e-4, rtol=1e-4,
    )
