"""Évolution unitaire cohérente (γ=0) — pas la dynamique dissipative de Hopfield.

`U = exp(-i W Δt)` est exactement unitaire pour tout `W` hermitien (le
générateur d'une évolution de Schrödinger sans dissipation) — c'est ce qui
préserve les franges d'interférence pendant la fenêtre de test Leggett-Garg
(cf. `docs/DevPlan.md`, contrainte `γ=0` pendant la mesure).
"""

import torch


def evolution_operator(w: torch.Tensor, dt: float = 1.0) -> torch.Tensor:
    """U = exp(-i W dt). Cast FP32 local avant `matrix_exp`, cf. CLAUDE.md
    (contrainte de précision sur toute opération spectrale)."""
    w32 = w.to(torch.complex64)
    return torch.linalg.matrix_exp(-1j * w32 * dt)


def evolve(z0: torch.Tensor, w: torch.Tensor, n_steps: int, dt: float = 1.0) -> torch.Tensor:
    """Trajectoire complète z(0), z(1), ..., z(n_steps) sous U=exp(-iWΔt).

    Une seule itération = un pas de mise à jour de Hopfield (au sens de ce
    sous-track : le rôle du "temps" nS, cf. DevPlan.md).
    Retourne un tenseur (n_steps+1, d).
    """
    u = evolution_operator(w, dt)
    traj = [z0.to(torch.complex64)]
    z = traj[0]
    for _ in range(n_steps):
        z = u @ z
        traj.append(z)
    return torch.stack(traj)
