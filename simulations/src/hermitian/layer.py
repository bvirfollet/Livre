"""Couche et modèle empilé pour l'architecture vectorielle hermitienne
native (`d_model`) — cf. `docs/SW_Design.md`.

Structure Post-LN (identique à BERT classique) :
    x1 = Norm(x + Attention(x))
    x2 = Norm(x1 + FFN(x1))

**Correction du 2026-09-18** : `HermitianRMSNorm` par défaut (préservation
de la phase — principe directeur explicite de tout ce travail, cf. FFN,
gate — confirmé par l'expérience de discrimination : RMSNorm ne montre
aucun désavantage face à LayerNorm, elle est même plus discriminante sur
l'axe DC). `HermitianLayerNorm` reste disponible via `norm_cls`,
réservée à la vérification de portage de poids (I-01 étendu) — pas à
l'architecture principale.
"""

import torch
import torch.nn as nn

from .attention import HermitianSelfAttention
from .ffn import HermitianFFN
from .norm import HermitianRMSNorm


class HermitianBertLayer(nn.Module):
    def __init__(
        self,
        d_model: int,
        num_heads: int,
        d_ff: int | None = None,
        norm_cls: type = HermitianRMSNorm,
        norm_eps: float = 1e-8,
    ):
        super().__init__()
        self.attention = HermitianSelfAttention(d_model, num_heads)
        self.attention_norm = norm_cls(d_model, eps=norm_eps)
        self.ffn = HermitianFFN(d_model, d_ff)
        self.output_norm = norm_cls(d_model, eps=norm_eps)

    def forward(self, x_real: torch.Tensor, x_imag: torch.Tensor):
        attn_real, attn_imag, _ = self.attention(x_real, x_imag)
        x_real, x_imag = self.attention_norm(x_real + attn_real, x_imag + attn_imag)

        ffn_real, ffn_imag = self.ffn(x_real, x_imag)
        x_real, x_imag = self.output_norm(x_real + ffn_real, x_imag + ffn_imag)

        return x_real, x_imag


class HermitianBertModel(nn.Module):
    """Empilement de `num_layers` `HermitianBertLayer` identiques en
    structure (poids indépendants, comme BERT classique)."""

    def __init__(
        self,
        d_model: int,
        num_heads: int,
        num_layers: int,
        d_ff: int | None = None,
        norm_cls: type = HermitianRMSNorm,
        norm_eps: float = 1e-8,
    ):
        super().__init__()
        self.layers = nn.ModuleList(
            [
                HermitianBertLayer(d_model, num_heads, d_ff, norm_cls, norm_eps)
                for _ in range(num_layers)
            ]
        )

    def forward(self, x_real: torch.Tensor, x_imag: torch.Tensor):
        for layer in self.layers:
            x_real, x_imag = layer(x_real, x_imag)
        return x_real, x_imag
