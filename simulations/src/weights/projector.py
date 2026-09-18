"""Portage de poids HuggingFace vers les modules hermitiens.

**Extension du 2026-09-18** : couvre le bloc d'attention
(`project_bert_attention`, actée le 2026-08-14), le FFN
(`project_bert_ffn`), les `LayerNorm` (`project_bert_layer_norm`), une
couche complète (`project_bert_layer`), l'empilement complet
(`project_bert_model`) et les embeddings (`project_bert_embeddings`).

`project_bert_layer` exige que `hermitian_layer.attention_norm`/
`output_norm` soient des `HermitianLayerNorm` (portage-compatible) — pas
`HermitianRMSNorm` (pas de centrage, ne peut pas reproduire `LayerNorm`
réelle même à `Im=0`, cf. `docs/SW_Design.md`). `HermitianLayerNorm` est
donc l'outil de vérification de portage, pas l'architecture par défaut
(`HermitianRMSNorm`, cf. correctif du 2026-09-18).

Charger le modèle HuggingFace source avec `BertModel.from_pretrained`
explicitement, pas `AutoModel` : certains checkpoints anciens (ex.
`prajjwal1/bert-tiny`) ont un `config.json` sans `model_type`, incompatible
avec la résolution `Auto*` des versions récentes de `transformers` (cf.
`docs/spike-weights-state-dict-mapping.md`).
"""

import torch

from src.hermitian.attention import HermitianSelfAttention
from src.hermitian.complex_linear import ComplexLinear
from src.hermitian.embeddings import HermitianEmbeddings
from src.hermitian.ffn import HermitianFFN
from src.hermitian.layer import HermitianBertLayer, HermitianBertModel
from src.hermitian.norm import HermitianLayerNorm


def _project_embedding_table(real_emb, imag_emb, hf_embedding, imag_std: float) -> None:
    with torch.no_grad():
        real_emb.weight.copy_(hf_embedding.weight)
        imag_emb.weight.normal_(mean=0.0, std=imag_std)


def _project_linear(complex_linear: ComplexLinear, hf_linear, imag_std: float) -> None:
    with torch.no_grad():
        complex_linear.fc_real.weight.copy_(hf_linear.weight)
        complex_linear.bias_real.copy_(hf_linear.bias)
        complex_linear.fc_imag.weight.normal_(mean=0.0, std=imag_std)
        complex_linear.bias_imag.normal_(mean=0.0, std=imag_std)


def project_bert_attention(
    hermitian_attn: HermitianSelfAttention, hf_attention, imag_std: float = 0.0
) -> None:
    """Copie les poids d'un `BertAttention` HuggingFace dans un `HermitianSelfAttention`.

    `hf_attention` : module `layer.attention` d'un `BertModel` HuggingFace
    (a les sous-modules `.self.{query,key,value}` et `.output.dense`).
    `imag_std` : écart-type du bruit gaussien injecté dans la partie
    imaginaire (0.0 par défaut ⇒ partie imaginaire exactement nulle, requis
    par le test de régression I-01).
    """
    _project_linear(hermitian_attn.q_proj, hf_attention.self.query, imag_std)
    _project_linear(hermitian_attn.k_proj, hf_attention.self.key, imag_std)
    _project_linear(hermitian_attn.v_proj, hf_attention.self.value, imag_std)
    _project_linear(hermitian_attn.out_proj, hf_attention.output.dense, imag_std)


def project_bert_ffn(hermitian_ffn: HermitianFFN, hf_layer, imag_std: float = 0.0) -> None:
    """Copie les poids du FFN (`intermediate.dense`, `output.dense`) d'un
    `BertLayer` HuggingFace dans un `HermitianFFN`.

    `hf_layer` : module `encoder.layer[i]` d'un `BertModel` (pas
    `layer.attention` — le FFN est porté par `layer.intermediate`/`layer.output`
    directement).
    """
    _project_linear(hermitian_ffn.fc1, hf_layer.intermediate.dense, imag_std)
    _project_linear(hermitian_ffn.fc2, hf_layer.output.dense, imag_std)


def project_bert_layer_norm(
    hermitian_norm: HermitianLayerNorm, hf_layer_norm, imag_std: float = 0.0
) -> None:
    """Copie les poids d'un `nn.LayerNorm` HuggingFace dans un `HermitianLayerNorm`.

    `hermitian_norm` doit être une `HermitianLayerNorm` — `HermitianRMSNorm`
    n'a pas de biais/centrage et ne peut pas reproduire `LayerNorm` réelle.
    """
    if not isinstance(hermitian_norm, HermitianLayerNorm):
        raise TypeError(
            "project_bert_layer_norm requiert une HermitianLayerNorm "
            "(portage-compatible) ; HermitianRMSNorm ne peut pas reproduire "
            "nn.LayerNorm même à Im=0 (pas de centrage/biais), cf. docs/SW_Design.md"
        )
    with torch.no_grad():
        hermitian_norm.gamma.copy_(hf_layer_norm.weight)
        hermitian_norm.bias_real.copy_(hf_layer_norm.bias)
        hermitian_norm.bias_imag.normal_(mean=0.0, std=imag_std)


def project_bert_layer(
    hermitian_layer: HermitianBertLayer, hf_layer, imag_std: float = 0.0
) -> None:
    """Copie tous les poids d'un `BertLayer` HuggingFace (attention, FFN,
    les deux `LayerNorm`) dans un `HermitianBertLayer` complet.

    `hf_layer` : module `encoder.layer[i]` d'un `BertModel`.
    `hermitian_layer` doit avoir été construit avec `norm_cls=HermitianLayerNorm`
    (cf. `project_bert_layer_norm`).
    """
    project_bert_attention(hermitian_layer.attention, hf_layer.attention, imag_std)
    project_bert_layer_norm(
        hermitian_layer.attention_norm, hf_layer.attention.output.LayerNorm, imag_std
    )
    project_bert_ffn(hermitian_layer.ffn, hf_layer, imag_std)
    project_bert_layer_norm(hermitian_layer.output_norm, hf_layer.output.LayerNorm, imag_std)


def project_bert_model(
    hermitian_model: HermitianBertModel, hf_model, imag_std: float = 0.0
) -> None:
    """Boucle `project_bert_layer` sur toutes les couches de l'empilement.

    `hf_model` : un `BertModel` HuggingFace complet. `hermitian_model` doit
    avoir le même nombre de couches (`len(hermitian_model.layers) ==
    hf_model.config.num_hidden_layers`) et avoir été construit avec
    `norm_cls=HermitianLayerNorm`.
    """
    hf_layers = hf_model.encoder.layer
    if len(hermitian_model.layers) != len(hf_layers):
        raise ValueError(
            f"Nombre de couches incompatible : hermitian_model en a "
            f"{len(hermitian_model.layers)}, hf_model en a {len(hf_layers)}"
        )
    for hermitian_layer, hf_layer in zip(hermitian_model.layers, hf_layers):
        project_bert_layer(hermitian_layer, hf_layer, imag_std)


def project_bert_embeddings(
    hermitian_embeddings: HermitianEmbeddings, hf_embeddings, imag_std: float = 0.0
) -> None:
    """Copie les trois tables d'embeddings (word/position/token_type) et la
    `LayerNorm` d'un `BertEmbeddings` HuggingFace dans un `HermitianEmbeddings`.

    `hermitian_embeddings.norm` doit être une `HermitianLayerNorm` pour un
    portage exact (cf. `project_bert_layer_norm`).
    """
    _project_embedding_table(
        hermitian_embeddings.word_embeddings_real,
        hermitian_embeddings.word_embeddings_imag,
        hf_embeddings.word_embeddings,
        imag_std,
    )
    _project_embedding_table(
        hermitian_embeddings.position_embeddings_real,
        hermitian_embeddings.position_embeddings_imag,
        hf_embeddings.position_embeddings,
        imag_std,
    )
    _project_embedding_table(
        hermitian_embeddings.token_type_embeddings_real,
        hermitian_embeddings.token_type_embeddings_imag,
        hf_embeddings.token_type_embeddings,
        imag_std,
    )
    project_bert_layer_norm(hermitian_embeddings.norm, hf_embeddings.LayerNorm, imag_std)
