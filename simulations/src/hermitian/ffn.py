"""FFN natif pour l'architecture vectorielle hermitienne (échelle
`d_model`) — cf. `docs/SW_Design.md`, correction du 2026-09-18.

La piste initialement notée (résonance matricielle `H'=φ(W₂(W₁HW₁†)W₂†)`,
`contributions/gémini/Evolution_BERT_suite`) suppose un token représenté
par une matrice hermitienne — l'architecture à compression écartée du
pipeline natif. `HermitianSelfAttention` représente chaque token par un
vecteur `z ∈ C^{d_model}` ; ce FFN est conçu pour cette représentation.
"""

import torch
import torch.nn as nn

from .complex_linear import ComplexLinear
from .gating import phase_preserving_gate


class HermitianFFN(nn.Module):
    """`FFN(z) = ComplexLinear₂(g(ComplexLinear₁(z)))`, `g` = gate réel
    préservant la phase (cf. `gating.py`). Position-wise, comme le FFN
    BERT classique — mêmes poids appliqués à chaque token.
    """

    def __init__(self, d_model: int, d_ff: int | None = None):
        super().__init__()
        d_ff = d_ff or 4 * d_model
        self.fc1 = ComplexLinear(d_model, d_ff)
        self.fc2 = ComplexLinear(d_ff, d_model)

    def forward(
        self, x_real: torch.Tensor, x_imag: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        h_real, h_imag = self.fc1(x_real, x_imag)
        h_real, h_imag = phase_preserving_gate(h_real, h_imag)
        return self.fc2(h_real, h_imag)
