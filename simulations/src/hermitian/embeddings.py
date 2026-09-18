"""Embeddings natifs pour l'architecture vectorielle hermitienne —
cf. `docs/SW_Design.md`.

Même schéma que le reste du portage (`WeightProjector`) : `Re` = table
HuggingFace copiée telle quelle, `Im` = bruit gaussien (`imag_std`, 0.0
pour le portage exact). Structure identique à `BertEmbeddings` (somme
word+position+token_type, puis normalisation) pour rester
portage-compatible.
"""

import torch
import torch.nn as nn

from .norm import HermitianRMSNorm


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
