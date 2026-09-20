"""Tests unitaires U-05 à U-07 (cf. docs/test_plan.md) — sous-track
Superposition Leggett-Garg, régime unitaire cohérent (γ=0).

Cas nN=2 calculé à la main : ξ¹=[1,0], ξ²=(1/√2)[1,1] (normalisé).
  W = ξ¹ξ¹† + ξ²ξ²† = [[1,0],[0,0]] + 0.5·[[1,1],[1,1]] = [[1.5,0.5],[0.5,0.5]]
  Avec diagonale à zéro (hypothèse Hopfield standard) :
  W' = [[0,0.5],[0.5,0]] = 0.5·σx (Pauli X)
  U = exp(-i·0.5·σx·dt) = cos(0.5dt)·I − i·sin(0.5dt)·σx   (identité de Pauli)
"""

import math

import torch

from src.superposition.dynamics import evolution_operator, evolve
from src.superposition.patterns import build_n_pattern_weights, build_two_pattern_weights
from tests.conftest import ATOL, RTOL

PATTERN1 = torch.tensor([1.0, 0.0])
PATTERN2 = torch.tensor([1.0, 1.0]) / math.sqrt(2)


def test_u05_hermiticity_random():
    """U-05 : W construit à partir de deux motifs aléatoires est hermitien."""
    d = 6
    p1 = torch.randn(d, dtype=torch.complex64)
    p2 = torch.randn(d, dtype=torch.complex64)
    w = build_two_pattern_weights(p1, p2)
    assert torch.allclose(w, w.conj().T, atol=ATOL, rtol=RTOL)


def test_u05_hermiticity_hand_n2():
    """U-05 : cas nN=2 calculé à la main, avec et sans diagonale à zéro."""
    w_with_diag = build_two_pattern_weights(PATTERN1, PATTERN2, zero_diagonal=False)
    expected_with_diag = torch.tensor(
        [[1.5, 0.5], [0.5, 0.5]], dtype=torch.complex64
    )
    assert torch.allclose(w_with_diag, expected_with_diag, atol=ATOL, rtol=RTOL)
    assert torch.allclose(w_with_diag, w_with_diag.conj().T, atol=ATOL, rtol=RTOL)


def test_u05_n_pattern_matches_two_pattern_for_n2():
    """build_n_pattern_weights([p1,p2]) == build_two_pattern_weights(p1,p2) —
    garde-fou de non-régression avant d'utiliser la généralisation à N motifs."""
    w_two = build_two_pattern_weights(PATTERN1, PATTERN2, zero_diagonal=False)
    w_n = build_n_pattern_weights([PATTERN1, PATTERN2], zero_diagonal=False)
    assert torch.allclose(w_two, w_n, atol=ATOL, rtol=RTOL)


def test_u05_n_pattern_hermiticity_random_n8():
    """W construit à partir de 8 motifs aléatoires est hermitien."""
    d = 12
    patterns = [torch.randn(d, dtype=torch.complex64) for _ in range(8)]
    w = build_n_pattern_weights(patterns)
    assert torch.allclose(w, w.conj().T, atol=ATOL, rtol=RTOL)

    w_zero_diag = build_two_pattern_weights(PATTERN1, PATTERN2, zero_diagonal=True)
    expected_zero_diag = torch.tensor(
        [[0.0, 0.5], [0.5, 0.0]], dtype=torch.complex64
    )
    assert torch.allclose(w_zero_diag, expected_zero_diag, atol=ATOL, rtol=RTOL)


def test_u06_unitarity_random():
    """U-06 : U=exp(-iWdt) est unitaire pour W hermitien aléatoire."""
    d = 6
    p1 = torch.randn(d, dtype=torch.complex64)
    p2 = torch.randn(d, dtype=torch.complex64)
    w = build_two_pattern_weights(p1, p2)
    u = evolution_operator(w, dt=0.7)
    identity = torch.eye(d, dtype=torch.complex64)
    assert torch.allclose(u @ u.conj().T, identity, atol=ATOL, rtol=RTOL)

    z0 = torch.randn(d, dtype=torch.complex64)
    z0 = z0 / z0.norm()
    z1 = u @ z0
    assert torch.allclose(z1.norm(), z0.norm(), atol=ATOL, rtol=RTOL)


def test_u07_hand_n2_evolution():
    """U-07 : cas nN=2, U=exp(-i·0.5·σx·dt) calculé analytiquement."""
    w = build_two_pattern_weights(PATTERN1, PATTERN2, zero_diagonal=True)
    dt = 1.0
    theta = 0.5 * dt

    expected_u = torch.tensor(
        [
            [math.cos(theta), -1j * math.sin(theta)],
            [-1j * math.sin(theta), math.cos(theta)],
        ],
        dtype=torch.complex64,
    )
    u = evolution_operator(w, dt=dt)
    assert torch.allclose(u, expected_u, atol=ATOL, rtol=RTOL)

    z0 = torch.tensor([1.0, 0.0], dtype=torch.complex64)
    traj = evolve(z0, w, n_steps=3, dt=dt)
    assert traj.shape == (4, 2)

    expected_z1 = expected_u @ z0
    assert torch.allclose(traj[1], expected_z1, atol=ATOL, rtol=RTOL)

    # U^n = exp(-i W n·dt) pour un même générateur W (forme close directe).
    # Tolérance locale élargie (1e-4 au lieu de ATOL global) : trois appels
    # indépendants à matrix_exp (approximation de Padé, FP32) composent une
    # dérive d'arrondi ~1e-4, mesurée et documentée — pas un bug de
    # traj/evolution_operator (vérifié : evolution_operator(w, dt=3) en un
    # seul appel reproduit la forme close à ATOL près).
    theta3 = 3 * theta
    expected_z3 = torch.tensor(
        [math.cos(theta3), -1j * math.sin(theta3)], dtype=torch.complex64
    )
    assert torch.allclose(traj[3], expected_z3, atol=1e-4, rtol=1e-3)
