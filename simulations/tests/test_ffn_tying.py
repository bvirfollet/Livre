"""Test de décroissance d'énergie pour le FFN à poids liés (W2=W1†,
gate radial conservatif) — même protocole que l'étape 1 du tying
attention (`test_hopfield_tying.py`), cf. docs/DevPlan.md.
"""

import torch

from src.hermitian.norm import HermitianRMSNorm
from src.hermitian.tied_ffn import TiedHermitianFFN
from src.hopfield.ffn_tied_dynamics import ffn_state_energy, ffn_tied_iteration

D_MODEL = 16
D_FF = 32
T_TOKENS = 5
NUM_STEPS = 20
NUM_SEEDS = 20
ENERGY_TOL = 1e-4


def _run_ffn_trajectory(seed: int) -> list[float]:
    torch.manual_seed(seed)
    ffn = TiedHermitianFFN(D_MODEL, D_FF)
    ffn.eval()
    norm = HermitianRMSNorm(D_MODEL)
    norm.eval()

    x_real = torch.randn(T_TOKENS, D_MODEL)
    x_imag = torch.randn(T_TOKENS, D_MODEL)

    energies = [ffn_state_energy(x_real, x_imag, ffn).item()]
    with torch.no_grad():
        for _ in range(NUM_STEPS):
            x_real, x_imag = ffn_tied_iteration(x_real, x_imag, ffn, norm)
            energies.append(ffn_state_energy(x_real, x_imag, ffn).item())
    return energies


def test_u09_ffn_tied_gradient_property_matches_lagrangian():
    """Garde-fou analytique : FFN_lié(x) = ∇_x Σ_a F(|h_a(x)|) exactement
    (dérivation de Wirtinger, docs/DevPlan.md) — vérifié par différences
    finies sur un point aléatoire, avant tout test de décroissance."""
    torch.manual_seed(0)
    ffn = TiedHermitianFFN(D_MODEL, D_FF)
    ffn.eval()

    x_real = torch.randn(T_TOKENS, D_MODEL, requires_grad=True)
    x_imag = torch.randn(T_TOKENS, D_MODEL, requires_grad=True)

    h_real, h_imag = ffn.fc1(x_real, x_imag)
    r = torch.sqrt(h_real**2 + h_imag**2)
    from src.hermitian.gating import radial_gate_lagrangian

    potential = radial_gate_lagrangian(r).sum()
    grad_real, grad_imag = torch.autograd.grad(potential, (x_real, x_imag))

    with torch.no_grad():
        out_real, out_imag = ffn(x_real, x_imag)

    assert torch.allclose(grad_real, out_real, atol=1e-5, rtol=1e-4)
    assert torch.allclose(grad_imag, out_imag, atol=1e-5, rtol=1e-4)


def test_u09_ffn_tied_energy_nonincreasing():
    """Décroissance d'énergie du FFN lié, K/W1 fixe, x itéré — même
    protocole (seeds, tol) que l'étape 1 du tying attention."""
    for seed in range(NUM_SEEDS):
        energies = _run_ffn_trajectory(seed)
        for t in range(len(energies) - 1):
            assert energies[t + 1] <= energies[t] + ENERGY_TOL, (
                f"seed={seed}, pas={t} : énergie croissante "
                f"({energies[t]:.6f} -> {energies[t + 1]:.6f})"
            )
