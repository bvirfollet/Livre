"""Couche linéaire complexe.

API en paires de tenseurs réels (real, imag) plutôt qu'en dtype
`torch.complex64` : chaque composante reste un tenseur réel ordinaire,
compatible nativement avec `torch.autocast(dtype=torch.bfloat16)` — il
n'existe pas de dtype "complex-bfloat16" combinant deux composantes bf16
dans PyTorch (seuls complex32/64/128, en FP16/FP32/FP64, sont supportés
par `torch.complex()`).
"""

import torch
import torch.nn as nn


class ComplexLinear(nn.Module):
    """Y = X W + B en arithmétique complexe, décomposée en Re/Im.

    Y_real = X_real @ W_real^T - X_imag @ W_imag^T + B_real
    Y_imag = X_real @ W_imag^T + X_imag @ W_real^T + B_imag
    """

    def __init__(self, in_features: int, out_features: int):
        super().__init__()
        self.fc_real = nn.Linear(in_features, out_features)
        self.fc_imag = nn.Linear(in_features, out_features)

    def forward(
        self, x_real: torch.Tensor, x_imag: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        out_real = self.fc_real(x_real) - self.fc_imag(x_imag)
        out_imag = self.fc_real(x_imag) + self.fc_imag(x_real)
        return out_real, out_imag
