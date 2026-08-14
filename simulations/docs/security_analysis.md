# Analyse de sécurité — simulations

Recentré sur le seul sujet identifié à ce stade : la gestion de la clé API
Quandela Cloud (Phase 5, accès QPU réel). À étendre si de nouveaux services
tiers sont intégrés.

## Surfaces d'attaque

| Surface | Vecteur | Risque | Mitigation |
|---|---|---|---|
| Clé API Quandela Cloud | Commit accidentel dans git | majeur (facturation, accès QPU au nom de Bertrand) | `.env` ignoré par `.gitignore`, jamais en dur dans le code |
| Clé API Quandela Cloud | Fuite via logs/notebooks partagés | majeur | ne jamais logger la clé, révoquer immédiatement en cas de doute |

## TODOs de sécurité ouverts

| Réf | Description | Fichier | Priorité |
|-----|-------------|---------|----------|
| S1 | Définir le mécanisme de stockage (variable d'env locale vs gestionnaire de secrets) avant le premier run Phase 5 | `docs/security_analysis.md` | critique avant Phase 5, non bloquant avant |

## Modèle de menace

### Hypothèses de confiance

- La machine locale de Bertrand est considérée de confiance.
- Le dépôt git (même privé) n'est **pas** un endroit de confiance pour des secrets.

### Vecteurs d'attaque identifiés

#### V1 — Fuite de la clé API Quandela Cloud via commit git

**Description :** un `.env` ou une clé en dur committée par erreur, poussée
sur un remote partagé.
**Impact :** facturation non autorisée sur le compte Quandela, accès au
matériel QPU au nom de Bertrand.
**Mitigation :** `.env` dans `.gitignore` (déjà en place), revue de
`git status`/`git diff` avant tout commit touchant la configuration Phase 5.
**Statut :** ouvert (mitigation préventive en place, pas encore testée en
conditions réelles — aucune clé émise à ce stade).

## Règles de sécurité absolues

- [ ] La clé API Quandela Cloud n'est jamais committée, jamais loggée, jamais
  passée en argument de ligne de commande visible dans l'historique shell.

## Audit de sécurité

| Date | Scope | Résultat | Actions |
|---|---|---|---|
| <!-- à remplir au premier audit --> | | | |
