"""Dynamique du FFN à poids liés (`W₂=W₁†`), cf. `docs/DevPlan.md`,
section « Hopfield hermitien à poids liés — FFN ». Même schéma que
`tied_dynamics.py` (attention), transposé au FFN via le gate radial
conservatif.
"""

import torch

from src.hermitian.gating import radial_gate_lagrangian
from src.hermitian.norm import HermitianRMSNorm
from src.hermitian.tied_ffn import TiedHermitianFFN


def ffn_tied_iteration(
    x_real: torch.Tensor,
    x_imag: torch.Tensor,
    ffn: TiedHermitianFFN,
    norm: HermitianRMSNorm,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Un pas : x ← RMSNorm(x + FFN_lié(x))."""
    out_real, out_imag = ffn(x_real, x_imag)
    return norm(x_real + out_real, x_imag + out_imag)


def ffn_state_energy(
    x_real: torch.Tensor, x_imag: torch.Tensor, ffn: TiedHermitianFFN
) -> torch.Tensor:
    """`E(x) = -Σ_a F(|h_a(x)|) + ½‖x‖²`, `h = fc1(x)` — Legendre du gate
    radial (terme d'attraction) plus terme quadratique du visible."""
    h_real, h_imag = ffn.fc1(x_real, x_imag)
    r = torch.sqrt(h_real**2 + h_imag**2)
    attraction = radial_gate_lagrangian(r).sum(dim=-1)
    quadratic = 0.5 * (x_real.pow(2) + x_imag.pow(2)).sum(dim=-1)
    return (-attraction + quadratic).sum()
