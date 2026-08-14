Génère un plan de test TU/TI structuré pour la feature ou le composant fourni en argument.

## Utilisation

`/test-plan [scope] [description de la feature]`

Exemple : `/test-plan hermitian symétrisation de la matrice d'attention`

## Étapes à suivre

1. **Analyse le contexte** :
   - Lis `docs/SW_Design.md` pour comprendre l'architecture du composant concerné
   - Lis `docs/CorrectifPlan.md` pour identifier les bugs passés dans ce scope (risques de régression)
   - Lis le code source du composant identifié

2. **Identifie les niveaux de test applicables** :
   - **Unitaire** : maths déterministes, sans dépendance externe (hermiticité, spectre, équivalence Hopfield)
   - **Intégration** : comparaison empirique nécessitant un modèle/dataset externe (portage de poids HF, GLUE, unitarité Perceval)
   - **Matériel réel** : QPU Quandela — coûteux, non systématique, réservé à la Phase 5

3. **Rappelle le principe de séparation strict** (`docs/test_plan.md`) : ne jamais évaluer un effet architectural avant d'avoir confirmé le test de régression du portage de poids correspondant.

4. **Génère le fichier** `docs/test_plan_[scope]_[date].md` avec :

```markdown
# Plan de test — simulations : [feature]

Date : [date du jour]
Scope : [scope]

## Niveau applicable
- [x/] Unitaire
- [x/] Intégration
- [x/] Matériel réel

## Condition de succès
[phrase unique vérifiable par un tiers]

## Tests unitaires
| ID | Ce qui est testé | Entrée | Résultat attendu |
|---|---|---|---|
| U-01 | [cas nominal] | [entrée] | [résultat] |
| U-02 | [cas limite] | [entrée] | [résultat] |
| U-03 | [cas d'erreur] | [entrée] | [exception / valeur défaut] |

## Tests d'intégration
| ID | Précondition | Action | Résultat attendu | Résultat obtenu |
|---|---|---|---|---|
| I-01 | [modèle/dataset chargé] | [action] | [résultat] | |

## Cas limites systématiques
- [ ] Comportement en précision réduite (BF16/FP16)
- [ ] Idempotence (même seed ⇒ même résultat)
- [ ] Limite matérielle Perceval/QPU si applicable

## Non-régression
- [ ] [test existant 1] doit rester vert
- [ ] [test existant 2] doit rester vert
```

5. **Identifie les risques de régression** en croisant avec `docs/CorrectifPlan.md` — signale tout scope ayant déjà eu ≥ 2 correctifs.
