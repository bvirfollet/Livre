"""Run complet I-05 (cf. docs/test_plan.md) : 10 tests (`Q_global`×5 `nN`,
`Q_i` agrégé×5 `nN`), protocole et seuils fixés dans `docs/DevPlan.md`.

Motifs concrets : deux vecteurs complexes à phases aléatoires indépendantes
par composante, normalisés à norme 1 (`||ξᵏ||=1`, pas module 1 par
composante) — convention qui garde les valeurs propres de `W` proches de 1
quel que soit `nN` (chaque `ξᵏξᵏ†` a pour valeur propre `‖ξᵏ‖²=1`), ce qui
permet de réutiliser le **même** `dt` pour tous les `nN` sans recalibrage
ad hoc par taille (qui serait un ajustement a posteriori interdit par la
règle de falsifiabilité, cf. `CLAUDE.md`).

`dt=1.0` : valeur fixée *avant* ce run, sur la base du cas `nN=2` calculé
à la main dans `tests/test_superposition_harness.py` (I-04, violation
≈1,248 observée) — pas ajustée ensuite pour ce run.
"""

import math

import torch

from .harness import (
    CLASSICAL_BOUND_K3,
    aggregated_local_k3,
    exact_aggregated_local_k3,
    exact_leggett_garg_k3,
    leggett_garg_k3,
    significance_sigma,
)
from .measurement import dichotomic_projectors
from .patterns import build_two_pattern_weights, global_axis, local_axis

DT = 1.0
M_SAMPLES = 300
SIGMA_THRESHOLD = 5.0


def generate_patterns(n_nodes: int, seed: int) -> tuple[torch.Tensor, torch.Tensor]:
    """Deux motifs à phases aléatoires indépendantes par composante,
    normalisés (`‖ξᵏ‖=1`). Seed fixée et journalisée (cf. `run_nN_protocol`)."""
    generator = torch.Generator().manual_seed(seed)
    phases1 = torch.rand(n_nodes, generator=generator) * 2 * math.pi
    phases2 = torch.rand(n_nodes, generator=generator) * 2 * math.pi
    pattern1 = torch.polar(torch.ones(n_nodes), phases1).to(torch.complex64)
    pattern2 = torch.polar(torch.ones(n_nodes), phases2).to(torch.complex64)
    return pattern1 / pattern1.norm(), pattern2 / pattern2.norm()


def run_nN_protocol(n_nodes: int, dt: float = DT, m_samples: int = M_SAMPLES) -> dict:
    """Exécute les deux tests (`Q_global`, `Q_i` agrégé) pour une taille de
    réseau `n_nodes`. Seeds dérivées déterministiquement de `n_nodes` et
    journalisées dans le résultat retourné (reproductibilité, cf. CLAUDE.md).
    """
    pattern_seed = 1000 + n_nodes
    global_mc_seed = 2000 + n_nodes
    local_mc_seed = 3000 + n_nodes

    pattern1, pattern2 = generate_patterns(n_nodes, seed=pattern_seed)
    w = build_two_pattern_weights(pattern1, pattern2, zero_diagonal=True)
    z0 = pattern1 + pattern2
    z0 = z0 / z0.norm()

    axis_global = global_axis(pattern1, pattern2)
    p_plus_g, p_minus_g = dichotomic_projectors(axis_global)
    global_result = leggett_garg_k3(
        z0, w, p_plus_g, p_minus_g, dt, m_samples,
        generator=torch.Generator().manual_seed(global_mc_seed),
    )
    global_result["sigma"] = significance_sigma(global_result["k3"], global_result["standard_error"])

    node_projectors = [
        dichotomic_projectors(local_axis(pattern1, pattern2, node=i)) for i in range(n_nodes)
    ]
    local_result = aggregated_local_k3(
        z0, w, node_projectors, dt, m_samples,
        generator=torch.Generator().manual_seed(local_mc_seed),
    )
    local_result["sigma"] = significance_sigma(local_result["k3"], local_result["standard_error"])

    return {
        "n_nodes": n_nodes,
        "dt": dt,
        "m_samples": m_samples,
        "seeds": {
            "pattern_seed": pattern_seed,
            "global_mc_seed": global_mc_seed,
            "local_mc_seed": local_mc_seed,
        },
        "global": global_result,
        "local": local_result,
    }


def run_full_experiment(
    n_nodes_values: list[int] = (2, 3, 5, 10, 20),
    dt: float = DT,
    m_samples: int = M_SAMPLES,
) -> list[dict]:
    """I-05 complet : `run_nN_protocol` pour chaque valeur de `nN`."""
    return [run_nN_protocol(n, dt=dt, m_samples=m_samples) for n in n_nodes_values]


def exact_realization(n_nodes: int, pattern_seed: int, dt: float = DT) -> dict:
    """`K(3)` exact (`Q_global`, `Q_i` agrégé — sans bruit d'échantillonnage)
    pour un tirage de motifs donné. Sert à explorer beaucoup de tirages à
    faible coût (pas de Monte-Carlo par tirage), cf. répétition `nN=3`/`nN=10`
    du 2026-09-13, `docs/DevPlan.md`."""
    pattern1, pattern2 = generate_patterns(n_nodes, seed=pattern_seed)
    w = build_two_pattern_weights(pattern1, pattern2, zero_diagonal=True)
    z0 = pattern1 + pattern2
    z0 = z0 / z0.norm()

    axis_global = global_axis(pattern1, pattern2)
    p_plus_g, p_minus_g = dichotomic_projectors(axis_global)
    k3_global = exact_leggett_garg_k3(z0, w, p_plus_g, p_minus_g, dt)

    node_projectors = [
        dichotomic_projectors(local_axis(pattern1, pattern2, node=i)) for i in range(n_nodes)
    ]
    k3_local = exact_aggregated_local_k3(z0, w, node_projectors, dt)

    return {"pattern_seed": pattern_seed, "k3_global": k3_global, "k3_local": k3_local}


def run_multi_realization_exact(
    n_nodes: int, n_realizations: int, dt: float = DT, seed_start: int = 50000
) -> list[dict]:
    """`n_realizations` tirages de motifs indépendants pour `n_nodes`,
    seeds `seed_start + n_nodes*1000 + i` (namespace distinct des seeds de
    `run_nN_protocol`, pas de recoupement). Retourne la liste des résultats
    `exact_realization`."""
    return [
        exact_realization(n_nodes, pattern_seed=seed_start + n_nodes * 1000 + i, dt=dt)
        for i in range(n_realizations)
    ]
