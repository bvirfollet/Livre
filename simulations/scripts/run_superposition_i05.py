#!/usr/bin/env python3
"""Lance le run I-05 (test de Leggett-Garg généralisé, cf. docs/DevPlan.md
et docs/test_plan.md) et archive le résultat.

Exemples (depuis `simulations/`, environnement activé) :

    # Protocole pré-enregistré initial (2026-09-13), M fixe pour tout nN :
    python scripts/run_superposition_i05.py --n-nodes 2 3 5 10 20 --dt 1.0 --m-samples 300

    # M recalculé par nN à partir de la marge exacte (sans bruit), cible 5σ :
    python scripts/run_superposition_i05.py --auto-m --sigma-target 5.0

    # Sortie par défaut : docs/results/i05_run_<date>.json (--output pour changer)
"""

import argparse
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.superposition.experiment import DT, M_SAMPLES, generate_patterns, run_nN_protocol
from src.superposition.harness import (
    CLASSICAL_BOUND_K3,
    QUANTUM_BOUND_K3,
    exact_leggett_garg_k3,
    required_m_for_significance,
)
from src.superposition.measurement import dichotomic_projectors
from src.superposition.patterns import build_two_pattern_weights, global_axis


def compute_auto_m(n_nodes_values: list[int], dt: float, sigma_target: float) -> dict[int, int]:
    """`M` par `nN`, recalculé à partir de la marge de violation exacte
    (sans bruit) observée pour ce `nN`, cf. `docs/DevPlan.md` (limite 1
    identifiée après le run initial du 2026-09-13)."""
    m_by_n = {}
    for n in n_nodes_values:
        pattern1, pattern2 = generate_patterns(n, seed=1000 + n)
        w = build_two_pattern_weights(pattern1, pattern2, zero_diagonal=True)
        z0 = pattern1 + pattern2
        z0 = z0 / z0.norm()
        axis = global_axis(pattern1, pattern2)
        p_plus, p_minus = dichotomic_projectors(axis)
        k3_exact = exact_leggett_garg_k3(z0, w, p_plus, p_minus, dt=dt)
        delta = abs(abs(k3_exact) - CLASSICAL_BOUND_K3)
        m_by_n[n] = required_m_for_significance(delta, n_s=3, z_target=sigma_target)
    return m_by_n


def clean_result(r: dict) -> dict:
    return {
        "n_nodes": r["n_nodes"],
        "dt": r["dt"],
        "m_samples": r["m_samples"],
        "seeds": r["seeds"],
        "global": {k: r["global"][k] for k in ("k3", "standard_error", "sigma", "C12", "C23", "C13")},
        "local": {
            "k3": r["local"]["k3"],
            "standard_error": r["local"]["standard_error"],
            "sigma": r["local"]["sigma"],
            "per_node_k3": [n["k3"] for n in r["local"]["per_node"]],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--n-nodes", type=int, nargs="+", default=[2, 3, 5, 10, 20])
    parser.add_argument("--dt", type=float, default=DT)
    parser.add_argument("--m-samples", type=int, default=M_SAMPLES, help="Ignoré si --auto-m")
    parser.add_argument(
        "--auto-m",
        action="store_true",
        help="Recalcule M par nN à partir de la marge exacte (sans bruit) observée à ce dt",
    )
    parser.add_argument("--sigma-target", type=float, default=5.0)
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    if args.auto_m:
        m_by_n = compute_auto_m(args.n_nodes, args.dt, args.sigma_target)
    else:
        m_by_n = {n: args.m_samples for n in args.n_nodes}

    results = [run_nN_protocol(n, dt=args.dt, m_samples=m_by_n[n]) for n in args.n_nodes]

    print(f"{'nN':>4} | {'M':>7} | {'K3_global':>10} | {'σ_global':>9} | {'K3_local':>10} | {'σ_local':>9}")
    print("-" * 66)
    for r in results:
        g, l = r["global"], r["local"]
        print(
            f"{r['n_nodes']:>4} | {r['m_samples']:>7} | {g['k3']:>+10.4f} | {g['sigma']:>9.3f} "
            f"| {l['k3']:>+10.4f} | {l['sigma']:>9.3f}"
        )

    output_path = args.output or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "docs",
        "results",
        f"i05_run_{datetime.date.today().isoformat()}.json",
    )
    payload = {
        "protocol": {
            "dt": args.dt,
            "auto_m": args.auto_m,
            "sigma_target": args.sigma_target,
            "n_nodes_values": args.n_nodes,
            "classical_bound_K3": CLASSICAL_BOUND_K3,
            "quantum_bound_K3": QUANTUM_BOUND_K3,
        },
        "results": [clean_result(r) for r in results],
    }
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"\nArchivé : {output_path}")


if __name__ == "__main__":
    main()
