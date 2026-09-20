"""Normalisation native pour l'architecture vectorielle hermitienne —
cf. `docs/SW_Design.md`, correction du 2026-09-18.

Deux variantes gardées en parallèle (décision Bertrand, 2026-09-18) :
- `HermitianRMSNorm` : préserve la phase exactement, pas de portage exact
  possible depuis `LayerNorm` classique (pas de centrage).
- `HermitianLayerNorm` : centrage complet (fidèle à `nn.LayerNorm`), se
  réduit exactement à `LayerNorm` réelle quand `Im=0` (portage-compatible)
  — mais ne préserve *pas* la phase individuelle (soustraire une moyenne
  complexe partagée change `arg(zᵢ)` différemment pour chaque `i`).

Objectif de la comparaison (cf. discussion du 2026-09-18) : le centrage
supprime la sensibilité à un décalage uniforme partagé par toutes les
dimensions (`x₂=x₁+c·𝟙` devient indiscernable de `x₁` après centrage) —
ce qui peut être bénéfique pour l'attention par produit scalaire sur des
poids pré-entraînés (le biais partagé gonflait artificiellement `Q·K`),
mais au prix de la préservation de phase. Voir
`scripts/compare_normalizations.py` pour la mesure empirique.
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


class HermitianLayerNorm(nn.Module):
    """`LN(z) = γ·(z − mean(z))/std(z) + β`, centrage complexe complet
    (moyenne complexe soustraite, variance = `mean(|z−mean(z)|²)`).

    Portage-compatible : avec `x_imag=0` partout et `bias_imag=0`, se
    réduit exactement à `nn.LayerNorm(x_real)` — copier `weight`/`bias`
    de BERT dans `gamma`/`bias_real` reproduit BERT classique à l'identique
    (même test de régression que pour `ComplexLinear`/`WeightProjector`).
    `bias_imag` distinct de `bias_real`, initialisé à zéro.
    """

    def __init__(self, d_model: int, eps: float = 1e-8):
        super().__init__()
        self.gamma = nn.Parameter(torch.ones(d_model))
        self.bias_real = nn.Parameter(torch.zeros(d_model))
        self.bias_imag = nn.Parameter(torch.zeros(d_model))
        self.eps = eps

    def forward(
        self, x_real: torch.Tensor, x_imag: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        mean_real = x_real.mean(dim=-1, keepdim=True)
        mean_imag = x_imag.mean(dim=-1, keepdim=True)
        centered_real = x_real - mean_real
        centered_imag = x_imag - mean_imag

        variance = (centered_real**2 + centered_imag**2).mean(dim=-1, keepdim=True)
        std = torch.sqrt(variance + self.eps)

        normalized_real = centered_real / std
        normalized_imag = centered_imag / std

        out_real = self.gamma * normalized_real + self.bias_real
        out_imag = self.gamma * normalized_imag + self.bias_imag
        return out_real, out_imag
