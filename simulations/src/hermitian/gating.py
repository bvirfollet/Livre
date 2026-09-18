"""Gate réel préservant la phase — brique commune au FFN.

**Correction du 2026-09-18** : une première version portait sur `|z|`
(`GELU(|z|)·z/|z|`, analogue "modReLU"). Elle préservait la phase mais ne
se réduisait *pas* à `GELU` réel à `Im=0` — `GELU` n'est pas une fonction
impaire (`GELU(-2)≈-0.045`, très différent de `-GELU(2)≈-1.95`), donc
passer par le module efface l'asymétrie qui fait tout l'intérêt de GELU.
Ça aurait cassé tout test de portage de poids sur le FFN.

Version corrigée : `g(z) = z · Φ(Re(z))`, où `Φ` est la fonction de
répartition normale standard (`GELU(x) = x·Φ(x)` est la définition exacte
de GELU, Hendrycks & Gimpel 2016). `Φ(Re(z)) ∈ (0,1)` est toujours réel
positif, donc `g` préserve la phase exactement (multiplication par un
réel positif) — sans division ni `ε`, plus simple et plus stable que la
version précédente — et se réduit exactement à `GELU(Re)` quand `Im=0`.
"""

import torch


def phase_preserving_gate(
    z_real: torch.Tensor, z_imag: torch.Tensor
) -> tuple[torch.Tensor, torch.Tensor]:
    """`g(z) = z · Φ(Re(z))` — `arg(g(z)) = arg(z)` exactement (`Φ(Re(z))`
    est un réel strictement positif), et `g(Re, 0) = (GELU(Re), 0)`
    exactement (portage-compatible).
    """
    gate = torch.special.ndtr(z_real)  # Φ(Re(z)), la CDF normale standard
    return z_real * gate, z_imag * gate
