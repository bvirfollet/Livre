"""Gate réel préservant la phase — brique commune au FFN et (implicitement)
compatible avec toute non-linéarité future respectant le même principe.

Analogue du "modReLU" (Arjovsky et al. 2016, Trabelsi et al. 2018) : la
non-linéarité porte sur le module `|z|` uniquement, jamais sur la phase —
cohérent avec le principe déjà établi dans `attention.py` (softmax sur
`Re(S)` seul, la partie imaginaire n'est jamais triturée arbitrairement).
"""

import torch
import torch.nn.functional as F


def phase_preserving_gate(
    z_real: torch.Tensor, z_imag: torch.Tensor, eps: float = 1e-8
) -> tuple[torch.Tensor, torch.Tensor]:
    """`g(z) = GELU(|z|) · z / (|z| + ε)` — un gate réel non négatif
    appliqué identiquement à Re et Im, donc `arg(g(z)) = arg(z)` exactement
    (à l'arrondi flottant près), pour tout `z ≠ 0`. Le `ε` au dénominateur
    évite `0/0` en `z=0` sans introduire de dépendance à la phase (le
    numérateur est déjà nul via `GELU(0)=0` dans ce cas).
    """
    modulus = torch.sqrt(z_real**2 + z_imag**2)
    gate = F.gelu(modulus) / (modulus + eps)
    return z_real * gate, z_imag * gate
