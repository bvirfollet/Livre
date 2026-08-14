# Plan de développement — simulations

Dernière mise à jour : 2026-08-14

## Objectif global

Donner un statut Strate 1 (testable) à l'extension hermitienne de BERT et à
son équivalence avec un pas de mise à jour de Hopfield, en la validant par
étapes croissantes de coût et de risque : PyTorch pur → portage de poids
pré-entraînés → comparaison empirique GLUE → simulation photonique → QPU réel.

Référence source : `contributions/gémini/BERT_hermitien_PoC` (racine du
dépôt RadioHumaine).

## Phase 0 — Initialisation ✓

- [x] Création du dossier et structure de base
- [x] CLAUDE.md et documents de base
- [ ] Environnement Python (venv, dépendances figées)

## Phase 1 — Classes PyTorch de l'adaptation hermitienne

**Objectif :** implémenter `ComplexLinear`, `HermitianSelfAttention`, et le
module d'équivalence Hopfield en 1 pas de mise à jour, sans dépendre d'un
modèle pré-entraîné.
**Critère de succès :** pour une matrice `S` construite par le module, `S`
est hermitienne (`S == S.conj().T` à la tolérance flottante près), son
spectre via `torch.linalg.eigh` est réel, et la sortie du pas Hopfield
coïncide avec l'attention softmax(Re(QK†)/√d) — la même formule, pas une
coïncidence numérique approximative.

### Tâches

- [x] feat(hermitian): `ComplexLinear` (couche linéaire complexe) — `src/hermitian/complex_linear.py`
- [x] feat(hermitian): `HermitianSelfAttention` (attention Q K†, symétrisation explicite) — `src/hermitian/attention.py`
- [x] feat(hopfield): module d'équivalence Hopfield 1-pas = attention hermitienne — `src/hopfield/equivalence.py`
- [x] test(hermitian): U-01 à U-04, cas N=2 calculés à la main directement dans les tests (la référence à `BERT_hermitien_PoC` était inexacte, cf. correction `test_plan.md` 2026-08-14) — 7/7 verts
- [x] docs: mise à jour SW_Design.md (décision d'architecture réel/imag), test_plan.md (tolérances + correction)

**Note (2026-08-14) :** décision d'architecture pendant l'implémentation —
représentation en paires (real, imag) de bout en bout plutôt que
`torch.complex64` matérialisé (pas de dtype "complex-bf16" natif en
PyTorch), validée avec Bertrand. Détail dans `SW_Design.md`.

### Dépendances / Bloquants

- Aucune — ce lot ne dépend d'aucun modèle externe ni service tiers.

## Phase 2 — Projecteur de poids HuggingFace

**Objectif :** charger un modèle HuggingFace existant (`bert-base-uncased`),
initialiser la partie réelle des couches avec ses poids pré-entraînés et la
partie imaginaire avec un bruit gaussien faible.
**Critère de succès :** avec partie imaginaire forcée à 0, la sortie du
modèle hermitien reproduit celle du BERT classique HuggingFace à une
tolérance numérique fixée à l'avance — **ce test doit être vert avant toute
autre affirmation sur l'effet de l'architecture hermitienne** (cf.
`docs/test_plan.md`, séparation stricte portage/effet).

**Portée réduite actée avec Bertrand le 2026-08-14 :** le critère ci-dessus
porte sur le **bloc d'attention seul** (`BertAttention` = self-attention +
`output.dense`), pas sur un `BertModel` complet — les embeddings, le FFN,
les `LayerNorm` et l'empilement multi-couches ne sont pas conçus dans
`SW_Design.md` (point ouvert consigné dans `docs/TODO.md`). Le comparatif
GLUE bout-en-bout (Phase 3) nécessitera de trancher ce point avant de
démarrer.

### Tâches

- [x] spike(weights): correspondance state_dict BERT ↔ `ComplexLinear`
  (`docs/spike-weights-state-dict-mapping.md`) — confirmée, avec la
  contrainte `BertModel` explicite (pas `AutoModel`) sur les checkpoints
  anciens type `bert-tiny`.
- [x] feat(weights): `WeightProjector` (`project_bert_attention`, bloc
  d'attention, injection Re/Im) — `src/weights/projector.py`
- [x] test(weights): I-01 vert — régression Im≈0 ⇒ sortie ≈
  `BertAttention` HuggingFace (`prajjwal1/bert-tiny`) — `tests/test_weights.py`
- [x] docs: mise à jour SW_Design.md, test_plan.md, TODO.md, CorrectifPlan.md

**Deux bugs Phase 1 découverts et corrigés pendant cette passe** (détail
dans `docs/CorrectifPlan.md`, BUG-001 et BUG-002) : fuite de biais réel
dans la partie imaginaire de `ComplexLinear`, et softmax appliqué par
erreur sur le `S` symétrisé au lieu du `S` brut dans
`HermitianSelfAttention` — tous deux indétectables par les seuls tests
Phase 1 (aucune référence externe à biais/projections Q≠K non nuls), tous
deux détectés par la conception du test I-01 avant même son premier run
réel. Conséquence positive du correctif BUG-002 : l'équivalence Hopfield
1-pas ≡ attention hermitienne est désormais inconditionnelle (Q, K, V
quelconques), plus forte que le résultat Phase 1 initial.

`transformers==5.15.0` installé dans `.venv` pour cette phase (pas encore
figé dans un fichier de lock, cf. `docs/TODO.md`).

### Dépendances / Bloquants

- Dépend de la Phase 1 (modules hermitiens stables).

## Phase 3 — Validation GLUE

**Objectif :** comparer le BERT hermitien (partie imaginaire activée) au
BERT classique sur un ou plusieurs tâches GLUE, avec seuil de tolérance
et critère de significativité fixés **avant** de lancer les runs.
**Critère de succès :** un rapport reproductible (config + seed archivés)
concluant OUI/NON/PARTIEL sur la question : l'extension hermitienne
change-t-elle le score GLUE au-delà du bruit de mesure ?

### Tâches

- [ ] feat(glue): harnais d'évaluation (réutilise `datasets`)
- [ ] experiment(glue): premier run comparatif, seeds fixées
- [ ] docs: entrée dans `Simulations_API.md` si le résultat est jugé citable

### Dépendances / Bloquants

- Dépend de la Phase 2 (portage de poids validé).
- Budget de calcul GPU à définir avec Bertrand avant de lancer les runs.

## Phase 4 — Simulation Perceval (photonique)

**Objectif :** traduire les rotations de Givens de la décomposition
hermitienne en circuit optique Perceval, vérifier l'unitarité du circuit
assemblé.
**Critère de succès :** `U_computed @ U_computed.conj().T ≈ I` pour le
circuit reconstruit, sur un nombre de modes cohérent avec la dimension du
modèle testé.

### Tâches

- [ ] spike(perceval): installation locale, prise en main de l'API (aucun coût, cf. règle spike)
- [ ] feat(perceval): pont Givens → circuit Perceval
- [ ] test(perceval): vérification d'unitarité

### Dépendances / Bloquants

- Dépend de la Phase 1 (décomposition de Givens du modèle hermitien).
- Indépendant des Phases 2/3 (peut démarrer en parallèle si prioritaire).

## Phase 5 — QPU réel (Quandela Cloud)

**Objectif :** exécuter une version réduite (4-8 dimensions) sur le
matériel photonique réel de Quandela.
**Critère de succès :** job exécuté sur QPU réel, distribution de sortie
comparée à la simulation Perceval locale.

### Tâches

- [ ] spike(qpu): accès Quandela Cloud, authentification, coût réel constaté
- [ ] feat(qpu): pont vers `perceval.providers.quandela`
- [ ] docs: mise à jour `security_analysis.md` (gestion de la clé API)

### Dépendances / Bloquants

- Dépend de la Phase 4.
- Limite matérielle connue (documentée dans `BERT_hermitien_PoC`) : les QPUs
  Quandela Cloud actuels (~6-12 modes) sont en-deçà des 32 modes visés — à
  reconfirmer par le spike avant tout run payant.

## Backlog (non planifié)

- Plan Monte-Carlo superposition/intrication généralisée (Leggett-Garg à N
  arbitraire, couplage de phase entre deux réseaux) —
  `contributions/claude/plan_dev_simulation_superposition_intrication.md`.
  Arbitrage non tranché avec Bertrand : lot de ce projet ou piste séparée
  (cf. `CLAUDE.md`, Problèmes ouverts P1).
- Kernel OpenCL (reconstruction de Givens) — mentionné en fin de
  `BERT_hermitien_PoC`, non prioritaire.
- Décomposition en chaînes de Pauli pour registre 5 qubits — idem.
- Wrapper d'intégration mobile — idem, non mûr.

---

## Historique des phases complétées

<!-- Déplacer ici les phases terminées avec date de complétion -->
