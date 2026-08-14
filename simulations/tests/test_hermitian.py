"""Tests unitaires U-01, U-02, U-04 (cf. docs/test_plan.md).

Les cas N=2 sont calculés à la main dans ce fichier — contrairement à ce
qu'affirmait `docs/test_plan.md` avant correction, `BERT_hermitien_PoC` ne
contient aucun exemple numérique explicite pour l'attention hermitienne ou
Hopfield ; voir la correction apportée au fichier.
"""

import math

import torch

from src.hermitian.attention import HermitianSelfAttention
from tests.conftest import ATOL, RTOL


def test_u01_hermiticity_random():
    """U-01 : après symétrisation, H_real symétrique et H_imag antisymétrique."""
    module = HermitianSelfAttention(d_model=8, num_heads=2)
    x_real = torch.randn(2, 5, 8)
    x_imag = torch.randn(2, 5, 8)

    _, _, (h_real, h_imag) = module(x_real, x_imag)

    assert torch.allclose(h_real, h_real.transpose(-2, -1), atol=ATOL, rtol=RTOL)
    assert torch.allclose(h_imag, -h_imag.transpose(-2, -1), atol=ATOL, rtol=RTOL)
    # La diagonale d'une matrice antisymétrique est nulle.
    diag = torch.diagonal(h_imag, dim1=-2, dim2=-1)
    assert torch.allclose(diag, torch.zeros_like(diag), atol=ATOL, rtol=RTOL)


def test_u01_hermiticity_hand_n2():
    """U-01 : cas N=2 calculé à la main (Q != K).

    Q = [[1,0],[0,1]] (réel), K = [1+0i, 0+1i] / [1+0i, 0-1i] (lignes).
    S = Q K^dagger (avant mise à l'échelle) donne S_real=[[1,1],[0,0]],
    S_imag=[[0,0],[-1,1]] (vérifié analytiquement). Le module divise par
    √head_dim = √2 avant symétrisation, donnant après symétrisation :
    H_real=[[1,0.5],[0.5,0]]/√2, H_imag=[[0,0.5],[-0.5,0]]/√2.
    """
    module = HermitianSelfAttention(d_model=2, num_heads=1)
    with torch.no_grad():
        for proj in (module.q_proj, module.k_proj, module.v_proj, module.out_proj):
            proj.fc_real.weight.zero_()
            proj.fc_real.bias.zero_()
            proj.fc_imag.weight.zero_()
            proj.fc_imag.bias.zero_()
        module.q_proj.fc_real.weight.copy_(torch.eye(2))
        module.v_proj.fc_real.weight.copy_(torch.eye(2))
        module.out_proj.fc_real.weight.copy_(torch.eye(2))
        # nn.Linear calcule x @ W^T ; l'entrée x_real ci-dessous est I, donc
        # la sortie vaut exactement W^T. On fixe donc W = (matrice K voulue)^T.
        module.k_proj.fc_real.weight.copy_(
            torch.tensor([[1.0, 0.0], [1.0, 0.0]]).T
        )
        module.k_proj.fc_imag.weight.copy_(
            torch.tensor([[0.0, 1.0], [0.0, -1.0]]).T
        )

    x_real = torch.eye(2).unsqueeze(0)  # (1, T=2, d=2), sert d'entrée identité
    x_imag = torch.zeros(1, 2, 2)

    _, _, (h_real, h_imag) = module(x_real, x_imag)

    scale = math.sqrt(2)
    expected_h_real = (
        torch.tensor([[1.0, 0.5], [0.5, 0.0]]) / scale
    ).unsqueeze(0).unsqueeze(0)
    expected_h_imag = (
        torch.tensor([[0.0, 0.5], [-0.5, 0.0]]) / scale
    ).unsqueeze(0).unsqueeze(0)

    assert torch.allclose(h_real, expected_h_real, atol=ATOL, rtol=RTOL)
    assert torch.allclose(h_imag, expected_h_imag, atol=ATOL, rtol=RTOL)


def test_u02_spectrum_hand_n2():
    """U-02 : réalité + valeurs propres analytiques pour le H du test N=2 ci-dessus.

    H = [[1, 0.5+0.5i], [0.5-0.5i, 0]] (matrice hermitienne 2x2).
    Pour [[a, b], [conj(b), d]] : λ = (a+d)/2 ± sqrt(((a-d)/2)^2 + |b|^2).
    a=1, d=0, b=0.5+0.5i, |b|^2=0.5 => λ = 0.5 ± sqrt(0.25+0.5) = 0.5 ± sqrt(0.75).
    """
    h_real = torch.tensor([[1.0, 0.5], [0.5, 0.0]])
    h_imag = torch.tensor([[0.0, 0.5], [-0.5, 0.0]])

    # Cast FP32 local avant eigh, cf. CLAUDE.md.
    h_complex = torch.complex(h_real.to(torch.float32), h_imag.to(torch.float32))
    eigenvalues = torch.linalg.eigh(h_complex).eigenvalues

    expected = sorted([0.5 - math.sqrt(0.75), 0.5 + math.sqrt(0.75)])
    assert torch.allclose(
        eigenvalues, torch.tensor(expected, dtype=eigenvalues.dtype), atol=ATOL, rtol=RTOL
    )


def test_u02_spectrum_trace_invariant_random():
    """U-02 : Tr(H) = somme des valeurs propres, pour un H aléatoire construit
    par le module (invariant qui détecterait une inversion de signe Re/Im)."""
    module = HermitianSelfAttention(d_model=8, num_heads=2)
    x_real = torch.randn(2, 5, 8)
    x_imag = torch.randn(2, 5, 8)

    _, _, (h_real, h_imag) = module(x_real, x_imag)

    h_complex = torch.complex(h_real.to(torch.float32), h_imag.to(torch.float32))
    eigenvalues = torch.linalg.eigh(h_complex).eigenvalues

    trace = torch.diagonal(h_real, dim1=-2, dim2=-1).sum(dim=-1)
    assert torch.allclose(eigenvalues.sum(dim=-1), trace, atol=ATOL, rtol=RTOL)


def test_u04_fp16_overflow_documents_bf16_requirement():
    """U-04 : régression négative — le produit hermitien déborde en FP16
    pour des magnitudes réalistes, mais pas en BF16 (plage d'exposant FP32).
    """
    q16 = torch.full((2, 2), 300.0, dtype=torch.float16)
    k16 = torch.full((2, 2), 300.0, dtype=torch.float16)
    s16 = torch.matmul(q16, k16.transpose(-2, -1))
    assert torch.isinf(s16).any(), "l'overflow FP16 attendu ne s'est pas produit"

    q_bf16 = q16.to(torch.bfloat16)
    k_bf16 = k16.to(torch.bfloat16)
    s_bf16 = torch.matmul(q_bf16, k_bf16.transpose(-2, -1))
    assert not torch.isinf(s_bf16).any(), "BF16 ne devrait pas déborder ici"
