"""Tests unitaires pour le FFN et la RMSNorm natifs (cf. docs/SW_Design.md,
correction du 2026-09-18 — architecture vectorielle, pas matricielle).

Invariant central testé : la préservation de la phase, analogue de
l'hermiticité pour ces deux composants (cf. `gating.py`, `norm.py`).
"""

import math

import torch

from src.hermitian.ffn import HermitianFFN
from src.hermitian.gating import phase_preserving_gate
from src.hermitian.norm import HermitianRMSNorm
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
