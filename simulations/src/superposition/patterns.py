"""Construction du réseau hermitien à partir de motifs mémorisés.

Sous-track « Superposition Leggett-Garg » (cf. `docs/DevPlan.md`, section
dédiée) — régime unitaire cohérent (`γ=0`), distinct de la dynamique
dissipative de `src/hermitian`/`src/hopfield`.

Représentation : `torch.complex64` natif (pas la paire réel/imag utilisée
dans `src/hermitian`) — ce module ne participe à aucune boucle
d'entraînement BF16, la contrainte qui motivait la paire réel/imag ne
s'applique pas ici.
"""

import torch


def build_two_pattern_weights(
    pattern1: torch.Tensor, pattern2: torch.Tensor, zero_diagonal: bool = True
) -> torch.Tensor:
    """W = ξ¹ξ¹† + ξ²ξ²† (stockage hebbien complexe), hermitien par construction.

    `zero_diagonal=True` (par défaut) : impose Wᵢᵢ=0, hypothèse standard de
    Hopfield. `zero_diagonal=False` : garde le self-couplage — piste notée
    dans `docs/DevPlan.md` pour discriminer non-classicité locale (nœud)
    vs relationnelle (couplage), enfreint volontairement le modèle Hopfield
    standard.
    """
    pattern1 = pattern1.to(torch.complex64)
    pattern2 = pattern2.to(torch.complex64)
    w = torch.outer(pattern1, pattern1.conj()) + torch.outer(pattern2, pattern2.conj())
    if zero_diagonal:
        w = w - torch.diag(torch.diagonal(w))
    return w
