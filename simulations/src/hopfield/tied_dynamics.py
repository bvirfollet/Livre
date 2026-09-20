"""Dynamique de Hopfield hermitien à poids liés (V=K) — protocole en 3
temps, cf. `docs/DevPlan.md`, section « Recherche — Hopfield hermitien à
poids liés (tying V=K) ».

Travaille directement au niveau (ξ, K) — pas de projections apprises
(`ComplexLinear`/`HermitianSelfAttention`) : ce module teste la dynamique
elle-même (Q=ξ, tying V=K), pas le portage de poids.
"""

import torch

from src.hermitian.norm import HermitianRMSNorm

from .equivalence import hopfield_energy, hopfield_step


def tied_iteration(
    xi_real: torch.Tensor,
    xi_imag: torch.Tensor,
    k_real: torch.Tensor,
    k_imag: torch.Tensor,
    beta: float,
    norm: HermitianRMSNorm,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Un pas : ξ ← RMSNorm(ξ + hopfield_step(Q=ξ, K, V=K, β))."""
    attn_real, attn_imag, _ = hopfield_step(
        xi_real, xi_imag, k_real, k_imag, k_real, k_imag, beta
    )
    residual_real = xi_real + attn_real
    residual_imag = xi_imag + attn_imag
    return norm(residual_real, residual_imag)


def state_energy(
    xi_real: torch.Tensor,
    xi_imag: torch.Tensor,
    k_real: torch.Tensor,
    k_imag: torch.Tensor,
    beta: float,
) -> torch.Tensor:
    """E(ξ) au sens de Ramsauer, K fixé jouant le rôle des motifs stockés X."""
    s_real = torch.matmul(xi_real, k_real.transpose(-2, -1)) + torch.matmul(
        xi_imag, k_imag.transpose(-2, -1)
    )
    return hopfield_energy(s_real, xi_real, xi_imag, beta)
