"""Empilement complet (attention liée + FFN liée), poids fixes — teste
si combiner les deux composantes déjà validées séparément (étape 1
attention, étape 1 FFN) préserve la décroissance d'énergie une fois
assemblées dans une couche Post-LN complète. Cf. docs/DevPlan.md,
section « Hopfield hermitien à poids liés — empilement complet ».
"""

import torch

from src.hermitian.norm import HermitianRMSNorm
from src.hermitian.tied_ffn import TiedHermitianFFN

from .equivalence import hopfield_step
from .ffn_tied_dynamics import ffn_state_energy
from .tied_dynamics import state_energy


def full_stack_tied_step(
    x_real: torch.Tensor,
    x_imag: torch.Tensor,
    k_real: torch.Tensor,
    k_imag: torch.Tensor,
    beta: float,
    ffn: TiedHermitianFFN,
    norm_attn: HermitianRMSNorm,
    norm_ffn: HermitianRMSNorm,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Un pas de couche complète Post-LN : attention liée (V=K=k_fixe)
    puis FFN liée (W2=W1†), chacune suivie de sa propre rétraction RMSNorm."""
    attn_real, attn_imag, _ = hopfield_step(
        x_real, x_imag, k_real, k_imag, k_real, k_imag, beta
    )
    x1_real, x1_imag = norm_attn(x_real + attn_real, x_imag + attn_imag)

    ffn_real, ffn_imag = ffn(x1_real, x1_imag)
    x2_real, x2_imag = norm_ffn(x1_real + ffn_real, x1_imag + ffn_imag)
    return x2_real, x2_imag


def full_stack_state_energy(
    x_real: torch.Tensor,
    x_imag: torch.Tensor,
    k_real: torch.Tensor,
    k_imag: torch.Tensor,
    beta: float,
    ffn: TiedHermitianFFN,
) -> float:
    """Énergie diagnostique = énergie attention(x; K fixe) + énergie
    FFN(x; W1 fixe), les deux évaluées au même état x — pas une preuve
    d'existence d'un potentiel combiné, un indicateur empirique."""
    e_attn = state_energy(x_real, x_imag, k_real, k_imag, beta).item()
    e_ffn = ffn_state_energy(x_real, x_imag, ffn).item()
    return e_attn + e_ffn
