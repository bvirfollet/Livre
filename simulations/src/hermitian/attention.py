"""Attention self-hermitienne.

Suit `docs/SW_Design.md` : S = Q K† / √d_k, symétrisée explicitement
(H = (S + S†) / 2) avant toute exploitation spectrale, softmax appliqué
sur Re(H) uniquement — la partie imaginaire porte le déphasage et n'entre
pas dans la pondération d'attention.

Représentation en paires (real, imag), cf. `complex_linear.py` pour la
justification (compatibilité BF16 native, pas de dtype complexe matérialisé
sur le chemin chaud).
"""

import torch
import torch.nn as nn
import torch.nn.functional as F

from .complex_linear import ComplexLinear


class HermitianSelfAttention(nn.Module):
    def __init__(self, d_model: int, num_heads: int):
        super().__init__()
        if d_model % num_heads != 0:
            raise ValueError("d_model doit être divisible par num_heads")
        self.d_model = d_model
        self.num_heads = num_heads
        self.head_dim = d_model // num_heads

        self.q_proj = ComplexLinear(d_model, d_model)
        self.k_proj = ComplexLinear(d_model, d_model)
        self.v_proj = ComplexLinear(d_model, d_model)
        self.out_proj = ComplexLinear(d_model, d_model)

    def _split_heads(self, r: torch.Tensor, i: torch.Tensor):
        B, T, _ = r.shape
        r = r.view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        i = i.view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        return r, i

    def _merge_heads(self, r: torch.Tensor, i: torch.Tensor):
        B, H, T, hd = r.shape
        r = r.transpose(1, 2).contiguous().view(B, T, H * hd)
        i = i.transpose(1, 2).contiguous().view(B, T, H * hd)
        return r, i

    def forward(self, x_real: torch.Tensor, x_imag: torch.Tensor):
        q_r, q_i = self._split_heads(*self.q_proj(x_real, x_imag))
        k_r, k_i = self._split_heads(*self.k_proj(x_real, x_imag))
        v_r, v_i = self._split_heads(*self.v_proj(x_real, x_imag))

        scale = self.head_dim**0.5
        # S = Q K^dagger / sqrt(d_k)  (K^dagger = conj(K)^T)
        s_real = (
            torch.matmul(q_r, k_r.transpose(-2, -1))
            + torch.matmul(q_i, k_i.transpose(-2, -1))
        ) / scale
        s_imag = (
            torch.matmul(q_i, k_r.transpose(-2, -1))
            - torch.matmul(q_r, k_i.transpose(-2, -1))
        ) / scale

        # Symétrisation hermitienne explicite : H = (S + S^dagger) / 2
        # => partie réelle symétrisée, partie imaginaire antisymétrisée.
        h_real = 0.5 * (s_real + s_real.transpose(-2, -1))
        h_imag = 0.5 * (s_imag - s_imag.transpose(-2, -1))

        attn_weights = F.softmax(h_real, dim=-1)

        out_real = torch.matmul(attn_weights, v_r)
        out_imag = torch.matmul(attn_weights, v_i)

        out_real, out_imag = self._merge_heads(out_real, out_imag)
        out_real, out_imag = self.out_proj(out_real, out_imag)

        return out_real, out_imag, (h_real, h_imag)
