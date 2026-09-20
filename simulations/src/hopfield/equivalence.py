"""Équivalence Hopfield 1-pas ≡ attention hermitienne.

Référence : réseaux de Hopfield modernes continus / dense associative
memories (Ramsauer et al. 2020), étendus au cas hermitien complexe dans
`contributions/gémini/BERT_hermitien_PoC`.

Formalisme :

    z^(1) = softmax(β · Re(q K†)) K

C'est exactement la même formule que l'attention hermitienne
`softmax(Re(QK†)/√d_k) · V` avec V = K et β = 1/√d_k — ce n'est pas une
coïncidence numérique, c'est la même fonction. L'équivalence est
inconditionnelle (Q, K, V quelconques) depuis la correction du
2026-08-14 : `HermitianSelfAttention` applique le softmax sur `Re(S)` brut,
*sans* symétrisation préalable (la symétrisation `H = (S+S†)/2` n'est
calculée que pour l'inspection/l'exploitation spectrale en aval, cf.
`attention.py`). Une version antérieure symétrisait avant le softmax, ce
qui aurait restreint l'équivalence au seul cas auto-associatif (Q = K) —
détecté par le test I-01 (portage de poids HuggingFace, `docs/test_plan.md`).

Fonction d'énergie de Liapounov (sert de substitut au calcul spectral
complet, cf. `docs/SW_Design.md`) :

    E(Z) = -1/β · Σ_i log(Σ_j exp(β · Re(Q_i K_j†))) + 1/2 · ||Z||_F²
"""

import torch


def hopfield_step(
    q_real: torch.Tensor,
    q_imag: torch.Tensor,
    k_real: torch.Tensor,
    k_imag: torch.Tensor,
    v_real: torch.Tensor,
    v_imag: torch.Tensor,
    beta: float,
):
    """Un pas de mise à jour de Hopfield continu complexe.

    Retourne (out_real, out_imag, s_real) où s_real = Re(Q K†) (non mis
    à l'échelle : le facteur d'échelle est porté par beta).
    """
    s_real = torch.matmul(q_real, k_real.transpose(-2, -1)) + torch.matmul(
        q_imag, k_imag.transpose(-2, -1)
    )
    attn_weights = torch.softmax(beta * s_real, dim=-1)
    out_real = torch.matmul(attn_weights, v_real)
    out_imag = torch.matmul(attn_weights, v_imag)
    return out_real, out_imag, s_real


def hopfield_energy(
    s_real: torch.Tensor,
    z_real: torch.Tensor,
    z_imag: torch.Tensor,
    beta: float,
) -> torch.Tensor:
    """E(Z) pour l'état Z (real, imag), à partir de s_real = Re(Q K†).

    s_real : (..., T, T) ; z_real/z_imag : (..., T, d).
    Retourne un tenseur (...,) — une énergie scalaire par batch/tête.
    """
    lse = torch.logsumexp(beta * s_real, dim=-1)  # (..., T), somme sur j
    energy_attraction = -(1.0 / beta) * lse.sum(dim=-1)  # somme sur i
    energy_norm = 0.5 * (z_real.pow(2) + z_imag.pow(2)).sum(dim=(-2, -1))
    return energy_attraction + energy_norm
