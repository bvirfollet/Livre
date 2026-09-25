"""Embeddings natifs pour l'architecture vectorielle hermitienne —
cf. `docs/SW_Design.md`.

Même schéma que le reste du portage (`WeightProjector`) : `Re` = table
HuggingFace copiée telle quelle, `Im` = bruit gaussien (`imag_std`, 0.0
pour le portage exact). Structure identique à `BertEmbeddings` (somme
word+position+token_type, puis normalisation) pour rester
portage-compatible.

**Correction du 2026-09-25** : `position_embeddings_imag` est initialisée
par une construction sinusoïdale (`sin(pos·ωₖ)`, cf.
`sinusoidal_position_imag_init`) plutôt que par bruit gaussien non
structuré — le codage positionnel original du Transformer (Vaswani et
al. 2017) est déjà construit en paires `sin`/`cos`, soit la partie
réelle et imaginaire d'une exponentielle complexe. Sans effet sur les
tests de portage existants (`project_bert_embeddings` écrase cette
initialisation avec du bruit calibré par `imag_std`, y compris `0.0`
pour le portage exact) — ne change le comportement que pour un modèle
construit sans passer par le portage (le cas d'un entraînement).
"""

import torch
import torch.nn as nn

from .norm import HermitianRMSNorm


def sinusoidal_position_imag_init(embedding: nn.Embedding, d_model: int) -> None:
    """`weight[pos,k] = sin(pos·ωₖ)`, `ωₖ=1/10000^(k/d_model)` — même
    schéma de fréquences que le codage positionnel de Vaswani et al.
    2017, appliqué ici uniquement à la partie imaginaire."""
    max_position, _ = embedding.weight.shape
    positions = torch.arange(max_position, dtype=torch.float32).unsqueeze(1)
    dims = torch.arange(d_model, dtype=torch.float32).unsqueeze(0)
    omega = 1.0 / (10000.0 ** (dims / d_model))
    with torch.no_grad():
        embedding.weight.copy_(torch.sin(positions * omega))


class HermitianEmbeddings(nn.Module):
    """`norm_cls=HermitianRMSNorm` par défaut, cohérent avec
    `HermitianBertLayer` (préservation de la phase, cf. `docs/SW_Design.md`
    et le correctif du 2026-09-18) — passer `HermitianLayerNorm`
    explicitement pour la vérification de portage (I-01 étendu).
    """

    def __init__(
        self,
        vocab_size: int,
        d_model: int,
        max_position_embeddings: int,
        type_vocab_size: int,
        norm_cls: type = HermitianRMSNorm,
        norm_eps: float = 1e-8,
        padding_idx: int | None = 0,
    ):
        super().__init__()
        self.word_embeddings_real = nn.Embedding(vocab_size, d_model, padding_idx=padding_idx)
        self.word_embeddings_imag = nn.Embedding(vocab_size, d_model, padding_idx=padding_idx)
        self.position_embeddings_real = nn.Embedding(max_position_embeddings, d_model)
        self.position_embeddings_imag = nn.Embedding(max_position_embeddings, d_model)
        sinusoidal_position_imag_init(self.position_embeddings_imag, d_model)
        self.token_type_embeddings_real = nn.Embedding(type_vocab_size, d_model)
        self.token_type_embeddings_imag = nn.Embedding(type_vocab_size, d_model)
        self.norm = norm_cls(d_model, eps=norm_eps)

    def forward(
        self,
        input_ids: torch.Tensor,
        token_type_ids: torch.Tensor | None = None,
        position_ids: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        seq_len = input_ids.shape[-1]
        if position_ids is None:
            position_ids = torch.arange(seq_len, device=input_ids.device).unsqueeze(0)
        if token_type_ids is None:
            token_type_ids = torch.zeros_like(input_ids)

        real = (
            self.word_embeddings_real(input_ids)
            + self.position_embeddings_real(position_ids)
            + self.token_type_embeddings_real(token_type_ids)
        )
        imag = (
            self.word_embeddings_imag(input_ids)
            + self.position_embeddings_imag(position_ids)
            + self.token_type_embeddings_imag(token_type_ids)
        )
        return self.norm(real, imag)
