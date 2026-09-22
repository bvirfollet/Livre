"""Signal de collapse fondé sur le couplage attention/FFN — Piste 1 de
la contribution Gémini (`implications_théorème_Stone_suite`), reconnectée
à l'architecture réelle (K de l'attention liée, W1 du FFN lié) plutôt
qu'au modèle jouet à motifs. Cf. docs/DevPlan.md.

a_rel(t) = (1/Y)⟨ψ|i[W_ffn,W_att]|ψ⟩ — utilise W (les poids), pas
seulement ψ (contrairement à R(t) et S_liens), sans construire de base
de concepts externe. Contrairement à ΔE², n'est pas une quantité
conservée puisque [W_att,W_ffn]≠0 par construction (vérifié ci-dessous).

**Simplification assumée** : W_att et W_ffn sont construits comme deux
opérateurs hermitiens FIXES (linéarisation), pas la dynamique non
linéaire complète (softmax, gate) — cohérent avec l'esprit de la piste
proposée, à documenter comme approximation.

Exploration, pas confirmatoire.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import math

import torch

from src.hermitian.tied_ffn import TiedHermitianFFN

D_MODEL, D_FF, T_TOKENS = 16, 32, 5
EMBED_DIM = T_TOKENS * D_MODEL
LANDSCAPE_SEED = 14
DT_TOTAL = 60.0
N_SUBSTEPS = 600
GAMMA_GRID = [1.0, 3.0, 6.0, 12.0]
K0 = 10.0
M_TRAJECTORIES = 20
SEED = 1414


def build_w_att(k_real: torch.Tensor, k_imag: torch.Tensor) -> torch.Tensor:
    """Bloc-diagonal, un bloc 16x16 par token = kₜkₜ† (le K de ce token
    spécifique) — capture la structure *par token* de l'attention."""
    k = torch.complex(k_real, k_imag)  # (T, d)
    w = torch.zeros(EMBED_DIM, EMBED_DIM, dtype=torch.complex64)
    for t in range(T_TOKENS):
        kt = k[t]  # (d,)
        block = torch.outer(kt, kt.conj())
        w[t * D_MODEL:(t + 1) * D_MODEL, t * D_MODEL:(t + 1) * D_MODEL] = block
    return w


def build_w_ffn(w1_real: torch.Tensor, w1_imag: torch.Tensor) -> torch.Tensor:
    """Bloc-diagonal, le MÊME bloc 16x16 = W1†W1 répété pour chaque
    token (le FFN est "position-wise", mêmes poids partout)."""
    w1 = torch.complex(w1_real, w1_imag)  # (d_ff, d)
    block = (w1.conj().T @ w1)  # (d, d), hermitien PSD
    w = torch.zeros(EMBED_DIM, EMBED_DIM, dtype=torch.complex64)
    for t in range(T_TOKENS):
        w[t * D_MODEL:(t + 1) * D_MODEL, t * D_MODEL:(t + 1) * D_MODEL] = block
    return w


def a_rel(psi: torch.Tensor, w_att: torch.Tensor, w_ffn: torch.Tensor) -> float:
    """a_rel(ψ) = <ψ| i[W_ffn,W_att] |ψ> (Y=1 dans nos unités)."""
    comm = w_ffn @ w_att - w_att @ w_ffn
    val = torch.vdot(psi, (1j * comm) @ psi)
    assert val.imag.abs().item() < 1e-3, f"a_rel devrait être réel, imag={val.imag.item()}"
    return val.real.item()


def main() -> None:
    torch.manual_seed(LANDSCAPE_SEED)
    k_real = torch.randn(T_TOKENS, D_MODEL)
    k_imag = torch.randn(T_TOKENS, D_MODEL)
    ffn = TiedHermitianFFN(D_MODEL, D_FF)
    ffn.eval()
    w1_real = ffn.fc1.fc_real.weight.detach()
    w1_imag = ffn.fc1.fc_imag.weight.detach()

    w_att = build_w_att(k_real, k_imag)
    w_ffn = build_w_ffn(w1_real, w1_imag)

    # Garde-fous
    assert torch.allclose(w_att, w_att.conj().T, atol=1e-4), "W_att doit être hermitien"
    assert torch.allclose(w_ffn, w_ffn.conj().T, atol=1e-4), "W_ffn doit être hermitien"
    comm_norm = (w_ffn @ w_att - w_att @ w_ffn).norm().item()
    print(f"||[W_att,W_ffn]|| = {comm_norm:.4f} (doit être non nul)")
    assert comm_norm > 1e-6, "le commutateur ne doit pas être nul (sinon a_rel est trivialement 0)"

    w_total = w_att + w_ffn
    eigvals, eigvecs = torch.linalg.eigh(w_total)
    print(f"W_total hermitien, spectre : min={eigvals.min():.3f} max={eigvals.max():.3f}\n")

    dt_small = DT_TOTAL / N_SUBSTEPS
    u_small = torch.linalg.matrix_exp(-1j * w_total * dt_small)

    # z0 : vecteur propre de W_att SEUL (pas de W_total) — sinon la
    # trajectoire est stationnaire sous W_total (piège déjà rencontré
    # avec ΔE²). Comme [W_att,W_ffn]≠0, ce n'est généralement pas un
    # état propre de W_total : la dynamique est non triviale.
    eigvals_att, eigvecs_att = torch.linalg.eigh(w_att)
    z0 = eigvecs_att[:, -1].clone().to(torch.complex64)  # état propre dominant de W_att

    # 1) Sous Y seul : plage naturelle de a_rel(t)
    z = z0.clone()
    trace = []
    with torch.no_grad():
        for _ in range(N_SUBSTEPS):
            z = u_small @ z
            trace.append(a_rel(z, w_att, w_ffn))
    trace_t = torch.tensor(trace)
    print(f"Sous Y seul : a_rel(t) min={trace_t.min():.4f} max={trace_t.max():.4f} "
          f"moyenne={trace_t.mean():.4f} |a_rel| max={trace_t.abs().max():.4f}\n")

    a_min, a_max = trace_t.abs().min().item(), trace_t.abs().max().item()

    def normalize(a: float) -> float:
        return max(0.0, min(1.0, (abs(a) - a_min) / (a_max - a_min + 1e-12)))

    generator = torch.Generator().manual_seed(SEED)
    print(f"{'gamma':>6}  {'% effondrées':>13}  {'<pas du 1er saut>':>18}  {'<|a_rel| au saut>':>18}")

    for gamma in GAMMA_GRID:
        collapses, first_jump_steps, a_jumps = 0, [], []
        for _ in range(M_TRAJECTORIES):
            z = z0.clone()
            collapsed_at, a_at_jump = None, None
            with torch.no_grad():
                for step in range(N_SUBSTEPS):
                    z = u_small @ z
                    a = a_rel(z, w_att, w_ffn)
                    rate = K0 * (normalize(a) ** gamma)
                    p_jump = 1.0 - math.exp(-rate * dt_small) if rate > 0 else 0.0
                    if p_jump > 0 and torch.rand((), generator=generator).item() < p_jump:
                        probs = (eigvecs.conj().T @ z).abs() ** 2
                        probs = probs / probs.sum()
                        outcome = torch.multinomial(probs, 1, generator=generator).item()
                        z = eigvecs[:, outcome].clone().to(torch.complex64)
                        collapsed_at, a_at_jump = step, a
                        break
            if collapsed_at is not None:
                collapses += 1
                first_jump_steps.append(collapsed_at)
                a_jumps.append(a_at_jump)

        pct = 100.0 * collapses / M_TRAJECTORIES
        mean_step = sum(first_jump_steps) / len(first_jump_steps) if first_jump_steps else float("nan")
        mean_a = sum(abs(v) for v in a_jumps) / len(a_jumps) if a_jumps else float("nan")
        print(f"{gamma:>6.1f}  {pct:>12.1f}%  {mean_step:>18.1f}  {mean_a:>18.4f}")

    print(f"\nRepère : |a_rel(t)| sous Y seul varie entre {a_min:.4f} et {a_max:.4f}.")


if __name__ == "__main__":
    main()
