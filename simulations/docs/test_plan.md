# Plan de test — simulations

## Niveau applicable

- [x] Unitaire — maths déterministes, sans dépendance externe
- [x] Intégration — comparaison empirique (poids HF, GLUE, Perceval)
- [ ] Matériel réel — QPU Quandela (Phase 5 uniquement, coûteux, non systématique)

## Condition de succès

Chaque affirmation citée dans `Simulations_API.md` est accompagnée d'un test
reproductible (config + seed archivés) et d'un seuil fixé *avant* le run.

## Principe de séparation strict (à ne jamais violer)

Un test de **portage de poids** (le modèle hermitien avec partie imaginaire
≈ 0 reproduit-il le BERT classique ?) et un test d'**effet architectural**
(l'architecture hermitienne change-t-elle le comportement au-delà du bruit
de mesure ?) répondent à deux questions différentes. Ne jamais lancer
seulement le second sans avoir d'abord fait passer le premier : un bug de
portage et un effet réel de l'architecture sont sinon indiscernables.

## Tests unitaires (Phase 1)

| ID | Ce qui est testé | Entrée | Résultat attendu |
|---|---|---|---|
| U-01 | Hermiticité de `S = QK†` après symétrisation | Q, K aléatoires | `S == S.conj().T` à la tolérance flottante près |
| U-02 | Réalité du spectre | `S` hermitienne | `torch.linalg.eigh(S).eigenvalues` sans partie imaginaire résiduelle significative |
| U-03 | Équivalence Hopfield 1-pas ≡ attention hermitienne | cas N=2 et N=3 (vérifiés à la main dans `BERT_hermitien_PoC`) | sorties identiques à la tolérance flottante près |
| U-04 | Overflow FP16 sur le produit hermitien | valeurs de grande magnitude, dtype FP16 | reproduit l'overflow documenté (test de régression négatif — sert à documenter *pourquoi* BF16 est requis) |

## Tests d'intégration — portage de poids (Phase 2)

| ID | Précondition | Action | Résultat attendu | Résultat obtenu |
|---|---|---|---|---|
| I-01 | Modèle hermitien instancié, partie imaginaire forcée à 0 | Forward sur un batch de test | Sortie ≈ sortie de `bert-base-uncased` HuggingFace (tolérance à fixer avant le run) | |

## Tests d'intégration — effet architectural GLUE (Phase 3)

| ID | Précondition | Action | Résultat attendu | Résultat obtenu |
|---|---|---|---|---|
| I-02 | I-01 vert | Éval GLUE, BERT classique vs BERT hermitien, seeds fixées | Score comparé à un seuil de significativité fixé avant le run | |

## Tests d'intégration — Perceval (Phase 4)

| ID | Composant tiers | Stimulus | Comportement attendu | Observé |
|---|---|---|---|---|
| I-03 | Circuit Perceval reconstruit depuis la décomposition de Givens | `compute_unitary()` | `U @ U.conj().T ≈ I` | |

## Cas limites à couvrir systématiquement

- [ ] Comportement si le nombre de modes Perceval demandé dépasse la limite
  matérielle actuelle (~6-12 modes en Cloud)
- [ ] Idempotence (rejouer le même run avec la même seed donne le même résultat)
- [ ] Comportement en précision réduite (BF16) sur le gap spectral — doit
  être documenté comme dégradé, pas silencieusement ignoré

## Critères de non-régression

- [ ] U-01 à U-04 doivent rester verts à chaque modification des modules hermitiens
- [ ] I-01 doit rester vert avant tout nouveau run GLUE cité dans `Simulations_API.md`
