# CLAUDE.md — simulations (RadioHumaine)

## Documents projet chargés en permanence

@README.md
@docs/TODO.md
@docs/DevPlan.md

---

## Documents à charger avant de toucher certains domaines

| Domaine | Lire avant de commencer |
|---|---|
| Architecture des modules, flux de données | `docs/SW_Design.md` |
| Plan de développement, tâches en cours | `docs/DevPlan.md` |
| Correctifs appliqués, historique des bugs | `docs/CorrectifPlan.md` |
| Plan de test (TU/TI) | `docs/test_plan.md` |
| Gestion de la clé API Quandela Cloud | `docs/security_analysis.md` |
| Contrat de résultats exposé à RadioHumaine | `docs/Simulations_API.md` |

---

## Rôle du projet

| Rôle | Description | Fichiers activés |
|---|---|---|
| ☑ **Producteur** | Produit des résultats/figures/métriques que le manuscrit `RadioHumaine` cite comme preuve Strate 1 | `docs/Simulations_API.md`, `docs/Simulations_API_CHANGELOG.md` |
| ☐ Consommateur | — | — |
| ☐ Autonome | — | — |

### Règles Producteur

- Maintenir `docs/Simulations_API.md` : seul fichier décrivant ce qui est
  **stable et citable** dans le manuscrit (définitions de métriques, figures,
  seuils de significativité, tables de résultats) — jamais l'implémentation.
- Toute modification d'un résultat déjà cité (nouvelle méthode de calcul,
  correction d'un bug affectant un chiffre déjà publié dans le livre, seuil
  révisé) → bumper `contract_version` + ajouter une entrée
  `[PENDING: RadioHumaine]` dans `docs/Simulations_API_CHANGELOG.md` dans le
  **même commit**.
- Ne jamais présenter un résultat comme stable avant qu'il ait passé son
  propre plan de test (`docs/test_plan.md`) — un chiffre sans test
  statistique documenté n'est pas un résultat, conformément à la
  méthodologie du manuscrit (falsifiabilité, cf. `RadioHumaine/CLAUDE.md`).

---

## Contraintes absolues du projet

- **Falsifiabilité avant calcul** : tout seuil de significativité (p-value,
  taille d'échantillon, tolérance de comparaison GLUE) doit être fixé
  *avant* de lancer les runs, jamais ajusté après coup pour faire coller un
  résultat.
- **Reproductibilité** : seeds fixées et journalisées pour tout run cité
  dans `Simulations_API.md` ; versions de dépendances figées (fichier de
  lock, pas de `pip install` sans version dans un run cité).
- **Précision numérique** : BF16 pour le forward des couches complexes
  (FP16 classique proscrit — risque d'overflow documenté sur le produit
  hermitien QK†). Toute décomposition spectrale (`torch.linalg.eigh`) doit
  être castée en FP32 localement avant l'appel, jamais exécutée en BF16 —
  perte de résolution du gap spectral sinon. Quantification INT8/INT4
  proscrite tant que la phase complexe est physiquement signifiante.
- **Séparation stricte des strates de test** : ne jamais confondre un test
  de portage de poids (partie imaginaire ≈ 0 doit reproduire BERT classique)
  et un test d'effet de l'architecture hermitienne — un même run ne peut pas
  répondre aux deux questions à la fois (cf. `docs/test_plan.md`).
- La clé API Quandela Cloud ne doit **jamais** être commitée — variable
  d'environnement uniquement (`.env` ignoré par git, voir `.gitignore`).

---

## Règles de commit

- Format **Conventional Commits** obligatoire : `type(scope): description`
- Types valides : `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `build`,
  `style`, `perf`, `experiment`, `spike`, `release`
  - `experiment` : ajout/modification d'un run d'entraînement ou d'évaluation
    dont le résultat est destiné à `Simulations_API.md` — le commit doit
    référencer la config et le seed utilisés.
- Scopes valides pour ce projet : `hermitian` (couches complexes, attention),
  `hopfield` (équivalence 1-pas), `weights` (projecteur HuggingFace), `glue`
  (harnais d'évaluation), `perceval` (pont photonique), `qpu` (accès matériel
  Quandela Cloud), `superposition` (Monte-Carlo Leggett-Garg, cf.
  `docs/DevPlan.md`), `docs`.
- Ne **jamais** ajouter de trailer `Co-Authored-By` ni aucune mention d'un
  modèle ou service d'IA.
- **1 commit = 1 responsabilité** : si un diff touche > 1 scope logique,
  splitter avant de committer.
- Après chaque tâche complète, mettre à jour `docs/TODO.md` et
  `docs/DevPlan.md`.

---

## Stratégie de branches

| Branche | Rôle |
|---|---|
| `main` | Résultats validés — protégée, merge uniquement via revue |
| `dev/[feature]` | Développement de feature, durée max 2 semaines |
| `hotfix/[desc]` | Correction urgente d'un résultat déjà cité dans le livre |
| `explore/[scope]-[slug]` | Spike de faisabilité uniquement, jamais mergé directement |

**Règle** : ne jamais développer directement sur `main`. Les branches
`explore/` sont supprimées après squash.

---

## Procédure de release

Lors d'un commit `release: vX.Y.Z` :

1. Vérifier que tous les runs cités dans cette version sont reproductibles
   (config + seed + résultat archivés).
2. Mettre à jour `RELEASES.md` avec le changelog de la version.
3. Archiver les items résolus dans `docs/TODO.md` (déplacer vers "Historique").
4. Créer un tag Git : `git tag vX.Y.Z`.
5. Pousser le tag : `git push origin vX.Y.Z`.
6. Si des résultats cités changent, bumper `Simulations_API.md` +
   `Simulations_API_CHANGELOG.md` dans le même commit (cf. règles Producteur).

---

## Cycle de développement obligatoire

1. **Planification** — Q&R initiale, réponses aux questions non précisées
   dans `docs/SW_Design.md`
2. **Revue des objectifs** — définir les TU et TI avant de coder, fixer les
   seuils de falsifiabilité à l'avance
3. **Codage**
4. **Tests unitaires** — maths déterministes (hermiticité, unitarité, cas
   N=2/N=3 vérifiés à la main), ~50 % de couverture du code essentiel
5. **Boucle debug TU** + mise à jour `docs/`
6. **Tests d'intégration** — comparaison empirique (GLUE, Perceval)
7. **Boucle debug TI** + mise à jour `docs/`
8. **Revue des résultats** + décision de citation dans `Simulations_API.md`

Les features doivent être implémentées **dans une seule session de contexte**
autant que possible.

---

## Workflow spike — obligatoire avant toute API/librairie non maîtrisée

### Règle de déclenchement

Un spike est obligatoire si la feature implique :
- Une librairie externe non encore utilisée dans le projet (`perceval-quandela`,
  `transformers` au-delà de ce qui est déjà validé)
- Un comportement numérique non documenté dans `docs/` (stabilité d'un
  algorithme de diagonalisation en précision réduite, comportement d'un
  simulateur Perceval sur un circuit > 12 modes)
- Une interaction avec un service tiers non encore validée (Quandela Cloud :
  authentification, quota, latence, coût réel)

**Durée max : 2h.** Au-delà → non concluant, décomposer ou escalader.

### Template spike

```
# Spike — [scope] : [question de faisabilité]

Branche : explore/[scope]-[slug]
Commit final : spike([scope]): [résultat en une ligne]  puis squash avant merge

## Question
<!-- Une seule question, précise et binaire -->

## Contraintes identifiées a priori

## Protocole de test minimal
- [ ] Vérification 1 :
- [ ] Vérification 2 :
- [ ] Vérification 3 (si nécessaire) :

## Résultat
- Réponse : OUI / NON / PARTIEL
- Contrainte découverte :
- Impact sur le design :
- Condition de succès pour le feat :

## Décision
- [ ] Le feat peut démarrer tel que spécifié
- [ ] Le feat nécessite une adaptation (décrire)
- [ ] Bloquer — contrainte insurmontable dans le scope actuel
```

### Cadre exploratoire

**Ne jamais explorer sur `main` ou une branche de feature.**

```
Étape 1 — Formuler l'hypothèse AVANT tout code
  "Je pense que [X] se comporte [ainsi] parce que [raison]"
  "L'hypothèse est fausse si [observation concrète]"

Étape 2 — Ouvrir une branche explore/[scope]-[slug]

Étape 3 — Définir la preuve minimale
  La plus petite vérification possible — pas d'implémentation complète.

Étape 4 — Exécuter : UN seul changement à la fois
  | Tentative | Changement unique | Observation | Hypothèse ? |
  Règle : ≥ 3 tentatives sans convergence → STOP. Reformuler ou consulter
  la documentation primaire (papier source, doc officielle de la librairie).

Étape 5 — Commit de conclusion (obligatoire avant de quitter la branche)
  explore([scope]): [conclusion en une ligne]
  Hypothèse : / Résultat : CONFIRMÉ / INFIRMÉ / PARTIEL / Cause réelle : / Impact :

Étape 6 — Retour sur la branche de travail
  Squash → spike([scope]): [résultat], branche explore/ supprimée après merge.
```

**Interdit :** commits `test: hypothesis-X` dans `main`, mélanger hypothèse
et correction, code debug sans retrait planifié.

---

## TODOs de sécurité ouverts

| Réf | Description | Fichier |
|-----|-------------|---------|
| S1 | Définir le mécanisme de stockage de la clé API Quandela Cloud (variable d'env vs gestionnaire de secrets) avant la Phase 5 | `docs/security_analysis.md` |

---

## Problèmes ouverts

| Réf | Description | Fichier/Scope |
|-----|-------------|--------------|
| P1 | **Résolu (2026-09-13)** : rattaché à ce projet comme sous-track de recherche, scope de commit `superposition`. Protocole complet (nN, nS, Q, seuils de significativité) fixé avec Bertrand. | `docs/DevPlan.md`, section « Recherche — Superposition quantique » |
