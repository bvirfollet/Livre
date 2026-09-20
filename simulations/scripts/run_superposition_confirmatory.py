#!/usr/bin/env python3
"""Protocole confirmatoire pré-enregistré (cf. docs/DevPlan.md, section
« Protocole confirmatoire pré-enregistré (2026-09-13) ») : teste, sur des
tirages de motifs FRAIS (jamais vus dans l'exploration précédente), si le
taux de tirages violant significativement (5σ) la borne de Leggett-Garg
est statistiquement incompatible avec un taux nul (test binomial).

Ce script doit être lancé TEL QUEL, sans modifier les paramètres après
avoir vu un résultat partiel — le protocole (nN, n_realizations,
sigma_target, max_m, seed_start) est fixé dans docs/DevPlan.md avant tout
run.

Exemple :
    python scripts/run_superposition_confirmatory.py --n-nodes 3 10 --n-realizations 30
"""

import argparse
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.superposition.experiment import DT, run_confirmatory_binomial_test


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--n-nodes", type=int, nargs="+", default=[3, 10])
    parser.add_argument("--n-realizations", type=int, default=30)
    parser.add_argument("--dt", type=float, default=DT)
    parser.add_argument("--sigma-target", type=float, default=5.0)
    parser.add_argument("--max-m", type=int, default=200_000)
    parser.add_argument("--seed-start", type=int, default=90_000)
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    results = [
        run_confirmatory_binomial_test(
            n_nodes=n,
            n_realizations=args.n_realizations,
            dt=args.dt,
            sigma_target=args.sigma_target,
            seed_start=args.seed_start,
            max_m=args.max_m,
        )
        for n in args.n_nodes
    ]

    print(f"{'nN':>4} | {'succès':>8} | {'p_null':>12} | {'p_value':>12}")
    print("-" * 46)
    for r in results:
        print(f"{r['n_nodes']:>4} | {r['k_successes']:>3}/{r['n_realizations']:<4} | {r['p_null']:>12.3e} | {r['p_value']:>12.3e}")

    output_path = args.output or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "docs", "results", f"confirmatory_run_{datetime.date.today().isoformat()}.json",
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nArchivé : {output_path}")


if __name__ == "__main__":
    main()
