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


def global_axis(pattern1: torch.Tensor, pattern2: torch.Tensor) -> torch.Tensor:
    """Axe de `Q_global` : direction séparant les deux motifs concurrents,
    normalisée. `P₊ = |a⟩⟨a|` sélectionne « penche vers ξ¹ », `P₋ = I−P₊`
    le reste (cf. `docs/DevPlan.md`)."""
    diff = (pattern1 - pattern2).to(torch.complex64)
    return diff / diff.norm()


def local_axis(pattern1: torch.Tensor, pattern2: torch.Tensor, node: int) -> torch.Tensor:
    """Axe de `Q_i` pour le nœud `node` : vecteur nul partout sauf à la
    position `node`, où il porte la phase de `ξ¹ᵢ−ξ²ᵢ` (module 1).

    Simplification actée (cf. `docs/DevPlan.md`) : dans la représentation
    phasor scalaire (un seul espace de Hilbert composite `C^nN`, pas un
    produit tensoriel de sous-espaces par nœud), il n'existe pas de notion
    native de « mesure d'un sous-système ». Ce choix reste une mesure
    projective légitime sur l'espace complet (`P₊+P₋=I`), mais interprétée
    comme un test *local* au nœud plutôt qu'un test *de sous-système*
    rigoureux au sens de l'intrication (réservé au modèle qubit de
    l'Objectif 2, non implémenté ici).
    """
    pattern1 = pattern1.to(torch.complex64)
    pattern2 = pattern2.to(torch.complex64)
    diff_i = pattern1[node] - pattern2[node]
    axis = torch.zeros_like(pattern1)
    if torch.abs(diff_i) > 1e-12:
        axis[node] = diff_i / torch.abs(diff_i)
    else:
        axis[node] = 1.0
    return axis
