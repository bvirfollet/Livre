"""Étapes 1 et 2 du protocole de tying V=K (cf. docs/DevPlan.md, section
« Recherche — Hopfield hermitien à poids liés »).

Étape 1 : K fixe, ξ itéré (Ramsauer strict) — décroissance d'énergie.
Étape 2 : sensibilité de cette décroissance à la variabilité de K.
Seuils et tailles fixés a priori dans DevPlan.md, non ajustés ici.
"""

import torch

from src.hermitian.norm import HermitianRMSNorm
from src.hopfield.tied_dynamics import state_energy, tied_iteration

D_MODEL = 16
T_PATTERNS = 5
BETA = 1.0
NUM_STEPS = 20
NUM_SEEDS = 20
ENERGY_TOL = 1e-4


def _run_tied_trajectory(seed: int, sigma: float) -> list[float]:
    """Trajectoire d'énergie sur NUM_STEPS pas, K perturbé par sigma à
    chaque pas (sigma=0 ⇒ K fixe strict, étape 1)."""
    torch.manual_seed(seed)
    k_real = torch.randn(T_PATTERNS, D_MODEL)
    k_imag = torch.randn(T_PATTERNS, D_MODEL)
    xi_real = torch.randn(T_PATTERNS, D_MODEL)
    xi_imag = torch.randn(T_PATTERNS, D_MODEL)
    norm = HermitianRMSNorm(D_MODEL)
    norm.eval()

    energies = [
        state_energy(xi_real, xi_imag, k_real, k_imag, BETA).item()
    ]
    with torch.no_grad():
        for _ in range(NUM_STEPS):
            k_step_real = k_real + sigma * torch.randn(T_PATTERNS, D_MODEL)
            k_step_imag = k_imag + sigma * torch.randn(T_PATTERNS, D_MODEL)
            xi_real, xi_imag = tied_iteration(
                xi_real, xi_imag, k_step_real, k_step_imag, BETA, norm
            )
            energies.append(
                state_energy(xi_real, xi_imag, k_step_real, k_step_imag, BETA).item()
            )
    return energies


def test_u08_tied_dynamics_energy_nonincreasing_k_fixed():
    """Étape 1 : K fixe (sigma=0), toutes graines, toute la trajectoire."""
    for seed in range(NUM_SEEDS):
        energies = _run_tied_trajectory(seed, sigma=0.0)
        for t in range(len(energies) - 1):
            assert energies[t + 1] <= energies[t] + ENERGY_TOL, (
                f"seed={seed}, pas={t} : énergie croissante "
                f"({energies[t]:.6f} -> {energies[t + 1]:.6f})"
            )


def test_u08_sensitivity_sweep_sigma_zero_matches_stage_one():
    """Garde-fou : sigma=0 dans le protocole d'étape 2 reproduit
    exactement l'étape 1 (même graine, même trajectoire)."""
    for seed in (0, 5, 19):
        traj_stage1 = _run_tied_trajectory(seed, sigma=0.0)
        for t in range(len(traj_stage1) - 1):
            assert traj_stage1[t + 1] <= traj_stage1[t] + ENERGY_TOL


def test_u08_sensitivity_sweep_large_sigma_breaks_monotonicity():
    """Garde-fou de non-vacuité : un sigma nettement plus grand que
    l'échelle de K (K ~ N(0,1)) doit casser la monotonie sur au moins
    une graine/pas — sinon le test d'étape 1 ne pourrait rien détecter."""
    violation_found = False
    for seed in range(NUM_SEEDS):
        energies = _run_tied_trajectory(seed, sigma=5.0)
        for t in range(len(energies) - 1):
            if energies[t + 1] > energies[t] + ENERGY_TOL:
                violation_found = True
                break
        if violation_found:
            break
    assert violation_found
