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

    **Non conservatif** (vérifié le 2026-09-20, cf. `docs/DevPlan.md`) :
    `∂g_réel/∂Im = 0 ≠ ∂g_imag/∂Re = Im·φ(Re)` en général — ce gate ne
    peut donc admettre aucune fonction de Lagrange au sens de Krotov.
    Réservé à la variante « portage BERT » (`HermitianFFN`), qui n'a
    jamais revendiqué de garantie d'énergie de toute façon.
    """
    gate = torch.special.ndtr(z_real)  # Φ(Re(z)), la CDF normale standard
    return z_real * gate, z_imag * gate


def conservative_radial_gate(
    z_real: torch.Tensor, z_imag: torch.Tensor
) -> tuple[torch.Tensor, torch.Tensor]:
    """`g(z) = z · Φ(|z|)` — préserve la phase (gain réel positif) ET
    conservatif (vérifié le 2026-09-20 : `∂g_réel/∂Im = ∂g_imag/∂Re`
    partout, condition de Schwarz satisfaite pour tout gain radial
    `s(|z|)`, cf. `docs/DevPlan.md` pour la preuve générale).

    Prix à payer : à `Im=0`, se réduit à `a·Φ(|a|)`, une fonction
    **impaire** de `a` — pas `GELU(a)` (qui n'est pas impaire). Ce gate
    n'est donc *pas* portage-compatible avec `GELU` réel ; réservé à la
    variante « Hopfield hermitien strict » (`TiedHermitianFFN`), qui a
    déjà renoncé au portage exact dès l'étape attention (tying `V=K`).
    """
    r = torch.sqrt(z_real**2 + z_imag**2)
    gate = torch.special.ndtr(r)
    return z_real * gate, z_imag * gate


def radial_gate_lagrangian(r: torch.Tensor) -> torch.Tensor:
    """`L(z) = F(|z|)`, Lagrangienne de `conservative_radial_gate` —
    `F(r) = ∫₀^r v·Φ(v) dv` (l'antidérivée de `GELU` évaluée en `|z|`),
    vérifiée le 2026-09-20 : `∇_{(Re,Im)} F(|z|) = z·Φ(|z|)` exactement.

    Forme fermée : `F(r) = ½[(r²−1)Φ(r) + r·φ(r)] − ½[−Φ(0)] `, normalisée
    pour `F(0)=0` (`φ` = densité normale standard).
    """
    phi_cdf = torch.special.ndtr(r)
    phi_pdf = torch.exp(-0.5 * r**2) / (2.0 * torch.pi) ** 0.5
    a_r = 0.5 * ((r**2 - 1.0) * phi_cdf + r * phi_pdf)
    a_0 = 0.5 * (-1.0 * 0.5)  # A(0) = 0.5*((0-1)*Phi(0) + 0) = -0.25
    return a_r - a_0
