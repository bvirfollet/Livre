"""Normalisation native pour l'architecture vectorielle hermitienne —
cf. `docs/SW_Design.md`, correction du 2026-09-18.

La piste initialement envisagée (normalisation de trace de Gémini,
`N(H)=H/(Tr(H)+ε)`) suppose un token représenté par une matrice hermitienne
— même problème que pour le FFN (cf. `ffn.py`). Ici : une variante RMSNorm
préservant la phase, précédent empirique réel (LLaMA et consorts),
contrairement à la normalisation de trace jamais validée.
"""

import torch
import torch.nn as nn


class HermitianRMSNorm(nn.Module):
    """`L(z) = γ · z / (RMS(z) + ε)`, `RMS(z) = √(mean(|z|²))`, `γ` réel
    par dimension, appliqué identiquement à Re et Im — préserve
    `arg(z)` exactement (mise à l'échelle par un réel positif).
    """

    def __init__(self, d_model: int, eps: float = 1e-8):
        super().__init__()
        self.gamma = nn.Parameter(torch.ones(d_model))
        self.eps = eps

    def forward(
        self, x_real: torch.Tensor, x_imag: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        mean_sq = (x_real**2 + x_imag**2).mean(dim=-1, keepdim=True)
        rms = torch.sqrt(mean_sq) + self.eps
        return self.gamma * x_real / rms, self.gamma * x_imag / rms
