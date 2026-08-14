"""Test unitaire U-03 (cf. docs/test_plan.md) : équivalence Hopfield 1-pas
≡ attention hermitienne dans le cas auto-associatif (Q = K = V)."""

import math

import torch

from src.hermitian.attention import HermitianSelfAttention
from src.hopfield.equivalence import hopfield_step
from tests.conftest import ATOL, RTOL


def _force_identity(proj):
    with torch.no_grad():
        proj.fc_real.weight.copy_(torch.eye(proj.fc_real.weight.shape[0]))
        proj.fc_real.bias.zero_()
        proj.fc_imag.weight.zero_()
        proj.fc_imag.bias.zero_()


def test_u03_equivalence_auto_associative():
    """Q = K = V (projections partagées) : le pas de Hopfield et l'attention
    hermitienne calculent exactement la même sortie — même formule, pas une
    coïncidence numérique (cf. docstring de `equivalence.py`).

    Dans ce cas S = Q Q^dagger est déjà symétrique (Re(S) l'est toujours
    quand Q = K), donc la symétrisation de `HermitianSelfAttention` est un
    no-op et les deux chemins de calcul coïncident.
    """
    d_model = 4
    module = HermitianSelfAttention(d_model=d_model, num_heads=1)
    module.k_proj = module.q_proj
    module.v_proj = module.q_proj
    _force_identity(module.out_proj)

    x_real = torch.randn(2, 3, d_model)
    x_imag = torch.randn(2, 3, d_model)

    actual_out_real, actual_out_imag, (h_real, _h_imag) = module(x_real, x_imag)

    q_real, q_imag = module.q_proj(x_real, x_imag)
    beta = 1.0 / math.sqrt(d_model)
    expected_out_real, expected_out_imag, s_real_raw = hopfield_step(
        q_real, q_imag, q_real, q_imag, q_real, q_imag, beta
    )

    assert torch.allclose(actual_out_real, expected_out_real, atol=ATOL, rtol=RTOL)
    assert torch.allclose(actual_out_imag, expected_out_imag, atol=ATOL, rtol=RTOL)
    # h_real du module a un axe "tête" (num_heads=1) que s_real_raw n'a pas.
    assert torch.allclose(h_real.squeeze(1), beta * s_real_raw, atol=ATOL, rtol=RTOL)


def test_u03_hopfield_step_hand_n2():
    """Cas N=2 calculé à la main : Q=K=V=I(2x2), beta=1.

    S_real = Q Q^T = I (lignes orthonormées) => softmax(I) par ligne donne
    [e/(e+1), 1/(e+1)] et [1/(e+1), e/(e+1)]. Comme V = I, out_real = les
    poids d'attention eux-mêmes ; out_imag = 0 (V_imag = 0).
    """
    identity = torch.eye(2).unsqueeze(0)
    zeros = torch.zeros(1, 2, 2)

    out_real, out_imag, s_real = hopfield_step(
        identity, zeros, identity, zeros, identity, zeros, beta=1.0
    )

    e = math.e
    expected = torch.tensor(
        [[e / (e + 1), 1 / (e + 1)], [1 / (e + 1), e / (e + 1)]]
    ).unsqueeze(0)

    assert torch.allclose(s_real, identity, atol=ATOL, rtol=RTOL)
    assert torch.allclose(out_real, expected, atol=ATOL, rtol=RTOL)
    assert torch.allclose(out_imag, torch.zeros_like(out_imag), atol=ATOL, rtol=RTOL)
