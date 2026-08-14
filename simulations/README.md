# simulations — Validation computationnelle pour RadioHumaine

## Description

Projet PyTorch/ML compagnon du manuscrit `RadioHumaine`. Objectif : donner un
statut Strate 1 (testable, falsifiable) à des affirmations du livre en les
implémentant et en les mesurant, plutôt qu'en les laissant à l'état d'analogie.

Point de départ : la contribution `contributions/gémini/BERT_hermitien_PoC`
(racine du dépôt), qui propose d'étendre l'architecture BERT à un espace
hermitien (couches complexes, attention Q K†, spectre de cohérence) et
d'en démontrer l'équivalence avec un pas de mise à jour d'un réseau de
Hopfield complexe.

## Objectifs

- Implémenter et valider (TU) les briques mathématiques de l'extension
  hermitienne de BERT et son équivalence avec la dynamique de Hopfield.
- Vérifier empiriquement (TI, GLUE) que le portage de poids pré-entraînés
  HuggingFace est correct avant d'attribuer un effet à l'architecture
  hermitienne elle-même.
- Étendre ensuite vers une simulation photonique (Perceval/Quandela), puis
  vers une exécution sur QPU réel — chaque étape gardée derrière un spike de
  faisabilité tant que le comportement n'est pas documenté ici.
- Produire des résultats citables (figures, tables, seuils de significativité)
  que le manuscrit `RadioHumaine` peut référencer comme preuve Strate 1 — voir
  `docs/Simulations_API.md`.

## Stack technique

| Composant | Technologie |
|---|---|
| Langage | Python 3.11+ |
| Framework ML | PyTorch (autograd nécessaire — couches complexes, fine-tuning réel) |
| Modèles pré-entraînés | `transformers` (HuggingFace), `bert-base-uncased` comme point de départ |
| Benchmark | `datasets` (GLUE) |
| Précision numérique | BF16 pour le forward, cast FP32 ciblé pour toute décomposition spectrale (`torch.linalg.eigh`) |
| Phase ultérieure | `perceval-quandela` (simulation photonique), Quandela Cloud (QPU réel) |

## Structure du projet

```
simulations/
├── CLAUDE.md               — Instructions pour les agents IA (ce projet est Producteur)
├── README.md                — Ce fichier
├── RELEASES.md               — Historique des versions
├── docs/
│   ├── SW_Design.md           — Architecture des modules (ComplexLinear, HermitianSelfAttention, ...)
│   ├── DevPlan.md             — Plan de développement par phases
│   ├── TODO.md                — Backlog actif
│   ├── CorrectifPlan.md       — Historique des correctifs
│   ├── test_plan.md           — Plan de test TU/TI
│   ├── security_analysis.md   — Gestion de la clé API Quandela Cloud
│   ├── Simulations_API.md     — Contrat de résultats exposé à RadioHumaine
│   └── Simulations_API_CHANGELOG.md
├── scripts/
│   ├── release.sh
│   └── check_api_deps.sh
└── .claude/
    └── commands/           — Skills Claude Code spécifiques à ce projet
```

## Démarrage rapide

```bash
cd simulations
python3 -m venv .venv
source .venv/bin/activate
pip install torch transformers datasets
# perceval-quandela installé seulement à partir de la Phase 4 (voir DevPlan.md)

# Lancer les tests unitaires (dès qu'ils existent, cf. DevPlan Phase 1)
pytest tests/
```

## Skills disponibles

| Commande | Description |
|---|---|
| `/spike` | Créer une branche spike avant toute intégration d'API non documentée (Perceval, Quandela Cloud) |
| `/test-plan` | Générer un plan de test TU/TI pour la feature courante |
| `/release` | Exécuter la procédure de release complète |
