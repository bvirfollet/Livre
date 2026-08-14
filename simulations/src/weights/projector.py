"""Portage de poids HuggingFace vers les modules hermitiens.

Portée actée avec Bertrand le 2026-08-14 : seul le bloc d'attention
(`BertAttention` = `self` (query/key/value) + `output.dense`) est projeté
et testé (test I-01). L'architecture complète (embeddings, FFN, LayerNorm,
empilement multi-couches) n'est pas encore conçue — cf. `docs/TODO.md`.

Charger le modèle HuggingFace source avec `BertModel.from_pretrained`
explicitement, pas `AutoModel` : certains checkpoints anciens (ex.
`prajjwal1/bert-tiny`) ont un `config.json` sans `model_type`, incompatible
avec la résolution `Auto*` des versions récentes de `transformers` (cf.
`docs/spike-weights-state-dict-mapping.md`).
"""

import torch

from src.hermitian.attention import HermitianSelfAttention
from src.hermitian.complex_linear import ComplexLinear


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
