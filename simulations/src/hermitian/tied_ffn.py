"""FFN à poids liés (`W₂ = W₁†`) — variante « Hopfield hermitien
strict », distincte de `HermitianFFN` (portage BERT), cf. `docs/DevPlan.md`.

Un seul jeu de poids appris (`fc1`) ; `fc2` n'existe pas comme paramètre
séparé — la sortie utilise directement le conjugué de `fc1.weight`. Pas
de biais (cohérent avec le formalisme de Krotov, qui n'en a pas).

Vérifié le 2026-09-20 : avec le gate radial conservatif
(`conservative_radial_gate`), `TiedHermitianFFN(x) = ∇_x Σ_a F(|h_a(x)|)`
exactement (`h = fc1(x)`, `F` = `radial_gate_lagrangian`) — dérivation de
Wirtinger complète dans `docs/DevPlan.md`.
"""

import torch
import torch.nn as nn

from .complex_linear import ComplexLinear
from .gating import conservative_radial_gate


class TiedHermitianFFN(nn.Module):
    def __init__(self, d_model: int, d_ff: int):
        super().__init__()
        self.fc1 = ComplexLinear(d_model, d_ff)

    def forward(
        self, x_real: torch.Tensor, x_imag: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        h_real, h_imag = self.fc1(x_real, x_imag)
        g_real, g_imag = conservative_radial_gate(h_real, h_imag)

        w_real = self.fc1.fc_real.weight  # (d_ff, d_model)
        w_imag = self.fc1.fc_imag.weight  # (d_ff, d_model)

        # y = g @ conj(W1) : tying W2 = W1† sans paramètre séparé.
        out_real = torch.matmul(g_real, w_real) + torch.matmul(g_imag, w_imag)
        out_imag = -torch.matmul(g_real, w_imag) + torch.matmul(g_imag, w_real)
        return out_real, out_imag
