# Plan de développement — simulations

Dernière mise à jour : 2026-09-13

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

- Kernel OpenCL (reconstruction de Givens) — mentionné en fin de
  `BERT_hermitien_PoC`, non prioritaire.
- Décomposition en chaînes de Pauli pour registre 5 qubits — idem.
- Wrapper d'intégration mobile — idem, non mûr.

### Recherche — Superposition quantique (Monte-Carlo Leggett-Garg)

**P1 résolu (2026-09-13) :** rattaché à ce projet comme sous-track de
recherche indépendant, pas un projet séparé (arbitré avec Bertrand — même
environnement PyTorch, mêmes objets hermitiens déjà construits en Phase 1,
même discipline de falsifiabilité). Indépendant du pipeline Phase 3 (GLUE)/
Phase 4 (Perceval)/Phase 5 (QPU). Origine : `contributions/claude/plan_dev_simulation_superposition_intrication.md`
(Objectif 1 de ce plan ; l'Objectif 2, intrication entre deux réseaux
séparés, est différé — question distincte, non commencée).

**Objectif :** vérifier si le remplacement d'un nœud réel par un nœud
hermitien fait apparaître une authentique superposition (au sens
opérationnel : violation d'une inégalité de Leggett-Garg généralisée),
plutôt que de le supposer par analogie.

**Séparation de régime (rappel, cf. `plan_dev_simulation_superposition_intrication.md` §0) :**
le test ci-dessous porte sur le régime **unitaire cohérent** (`γ=0` pendant
la fenêtre de test — une évolution dissipative effacerait les franges
d'interférence avant la mesure). C'est un régime distinct de la dynamique
**dissipative** déjà codée et validée en Phase 1/2
(`HermitianSelfAttention`/Hopfield 1-pas, softmax = convergence vers un
attracteur). Les deux coexistent dans le projet sans se substituer l'une à
l'autre.

**Notation (fixée le 2026-09-13, corrige une confusion initiale) :**
- `nN` — taille du réseau (nombre de nœuds hermitiens), `nN ∈ {2, 3, 5, 10, 20}`
  (plafonné à 20 par Bertrand pour raisons de coût calculatoire — `50`
  écarté).
- `nS` — nombre de temps de mesure dans le test de Leggett-Garg généralisé,
  fixé à `nS=3` pour cette première itération (LG standard, le mieux
  caractérisé dans la littérature ; simplifie le plan d'expérience et
  suffit à démontrer l'objectif). Le rôle du « temps » = les itérations de
  mise à jour de Hopfield (l'input reste fixe pendant les `nS` itérations).

**Formule et bornes (vérifiées à la source, corrige une erreur de
citation du plan initial — la bonne référence est Emary, Lambert & Nori,
*Rep. Prog. Phys.* **77**, 016001 (2014), pas « 76, 2013 ») :**

```
K(nS) = C₂₁ + C₃₂ + ... + C_{nS(nS-1)} − C_{nS 1},   Cᵢⱼ = ⟨QᵢQⱼ⟩ (Q dichotomique, ±1)

Borne classique (macroréalisme) :
  −nS ≤ K(nS) ≤ nS−2        (nS impair ≥ 3)
  −(nS−2) ≤ K(nS) ≤ nS−2    (nS pair ≥ 4)

Violation quantique maximale (mesures idéales) : K(nS) = nS·cos(π/nS)
```

Pour `nS=3` : borne classique 1, borne quantique 3/2 (résultat de Lüders).

**Représentation :** phasor scalaire `zⱼ=Rⱼe^{iθⱼ}` (recommandation du
plan source, non contestée — scalable, suffit pour ce test ; le modèle
qubit 2×2 par nœud est réservé à l'Objectif 2 différé).

**Observable dichotomique `Q` :** deux motifs mémorisés concurrents
`ξ¹`, `ξ²` (deux attracteurs Hopfield stockés dans `W`) définissent l'axe
de mesure. Deux niveaux, formant deux familles de test distinctes (aucune
n'implique l'autre logiquement — cf. discussion du 2026-09-13, ci-dessous) :
- `Q_global(z)` : signe de la projection de l'état **complet** du réseau
  sur l'axe `ξ¹`/`ξ²` — teste la superposition à l'échelle du réseau.
- `Q_i(z)` (par nœud), agrégé en une moyenne sur les `nN` nœuds — teste la
  superposition élémentaire, au niveau d'un seul nœud. **Ne pas tester
  chaque nœud individuellement** : ferait passer la famille de tests de 10
  à ~45 (un test par nœud par taille de réseau), invalidant la correction
  de Bonferroni fixée ci-dessous.

**Précision logique actée (2026-09-13)** : une violation de `Q_global`
implique qu'il n'est pas possible que *(tous les nœuds aient une
trajectoire classique définie) ET (Q_global soit une composition
déterministe non perturbatrice de ces trajectoires)* — pas qu'un nœud
précis, testé isolément, violerait lui-même son propre `Q_i`. La
non-classicité peut être localisée dans un nœud (source 1) ou purement
relationnelle, portée par le couplage `W` lui-même sans qu'aucun nœud
isolé ne viole sa propre borne (source 2, analogue à la non-localisabilité
de la violation dans un test de Bell/EPR). D'où la nécessité du test `Q_i`
agrégé — aucune des deux affirmations n'implique l'autre.

**Piste ouverte notée pour distinguer les deux sources (Bertrand,
2026-09-13)** : étudier le cas `Wᵢᵢ ≠ 0` (self-couplage d'un nœud sur
lui-même) — enfreint l'hypothèse standard de Hopfield (`Wᵢᵢ=0`), mais
permet de tester si la dynamique propre d'un nœud seul (sans couplage
inter-nœuds réel) peut déjà produire une violation sur son propre `Q_i` —
un signal en faveur de la source 1 si c'est le cas. Non implémenté dans
cette première itération.

**Protocole statistique (falsifiabilité fixée avant tout run, 2026-09-13) :**
- `M=300` tirages Monte-Carlo par corrélation `Cᵢⱼ` (calcul de puissance :
  `M ≥ 25·nS/Δ(nS)²` pour une séparation à 5σ, où `Δ(nS)` est l'écart
  borne quantique − borne classique ; `M=300` couvre `nS=3` à `50` avec
  marge). Budget total par test : `nS × M` runs (chaque paire de temps
  nécessite son propre sous-ensemble frais, non réutilisable, pour
  respecter l'hypothèse de mesurabilité non invasive).
- Seuil de significativité : violation au-delà de la borne classique par
  **≥5 erreurs standard** (unilatéral), par test.
- Correction de Bonferroni sur la famille de **10 tests** (`Q_global` ×
  5 valeurs de `nN`, `Q_i` agrégé × 5 valeurs de `nN`).

**Piste différée, non formalisée (Bertrand, 2026-09-13)** : modéliser la
sortie d'un nœud comme l'effondrement de la probabilité conjointe de
(input externe, état précédent du nœud) — reformulation bipartite
intéressante (un nœud n'est jamais vraiment isolé, toujours couplé à un
input), mais formalisation non aboutie. Ne bloque pas le protocole
ci-dessus (le test LG ne requiert pas cette formalisation — contrairement
à l'intrication, la superposition testée ici ne requiert pas ≥2 parties
séparées). À reprendre plus tard, possiblement pertinent pour l'Objectif 2
ou pour affiner ce que « mesurer » signifie opérationnellement.

**Objectif 2 du plan source (intrication entre deux réseaux couplés)** :
différé, non commencé — question distincte (corrélation de phase non
factorisable entre deux systèmes séparés), pas ce que teste le protocole
ci-dessus.

#### Tâches (implémentation)

- [x] feat(superposition): primitives — construction de `W` hermitien à
  partir de deux motifs, pas d'évolution unitaire (`U=e^{-iWΔt}`, cast
  FP32 pour `matrix_exp`/`eigh`), mesure projective dichotomique avec
  collapse (règle de Born) — `src/superposition/`
- [x] test(superposition): TU — hermiticité de `W`, unitarité de `U`
  (`U U† ≈ I`), cas `nN=2` vérifié à la main — U-05 à U-07 verts
  (`tests/test_superposition.py`)
- [ ] feat(superposition): harnais Monte-Carlo (`nS×M` sous-ensembles,
  calcul de `K(nS)`, `Q_global` et `Q_i` agrégé)
- [ ] test(superposition): TI — régression sur la violation théorique
  connue (`K(3)=3/2` en mesure idéale, cas non bruité) avant tout run
  statistique sur le modèle réseau
- [ ] experiment(superposition): premier run complet, 10 tests, seuils
  fixés ci-dessus, seeds archivées
- [ ] docs: mise à jour `Simulations_API.md` si un résultat est jugé citable

### Recherche — Compression hermitienne pour portage mobile

### Recherche — Compression hermitienne pour portage mobile

**Statut :** non planifié, non chiffré en phase numérotée. Indépendant du
pipeline Phase 3 (GLUE)/Phase 4 (Perceval)/Phase 5 (QPU), qui continuent à
l'échelle native `d_model` (`HermitianSelfAttention` telle que construite en
Phase 1/2). Objectif de recherche distinct posé par Bertrand le 2026-08-14 :
vérifier s'il est possible de réduire la taille et le nombre de nœuds d'un
réseau hermitien **sans perdre la quantité d'information stockée**, pour
faciliter un portage mobile.

**Origine et correction du cadrage (2026-08-14) :** `contributions/gémini/BERT_hermitien_PoC`
propose un nœud hermitien `d×d` avec `d=28` ou `32`, calibré par
`d² ≥ 768` — c'est-à-dire un budget de réels **égal ou supérieur** (784 ou
1024 réels contre 768), pas une compression. Analyse détaillée (échange du
2026-08-14) :
- Le comptage `N_params = d²` pour une matrice hermitienne `d×d` est
  correct, mais choisir `d² ≈ 768` ne réduit rien — c'est une
  reparamétrisation à budget quasi constant (+33 % pour `d=32`).
- L'argument « les phases portent 93-96 % de l'information » confond la
  proportion d'*emplacements matriciels* hors-diagonale (qui domine pour
  tout `d` grand, y compris pour une matrice symétrique réelle — ce n'est
  pas spécifique au complexe) avec la proportion d'*information sémantique*
  effectivement encodée. Le fait spécifiquement complexe est plus modeste :
  chaque paire hors-diagonale porte 2 réels (amplitude + phase) contre 1
  seul pour une paire symétrique réelle.
- Le projecteur `π(x) = φ(x)φ(x)† + diag(W_diag·x)` proposé pour
  peupler le nœud est un **produit extérieur, donc de rang 1** : il ne
  peuple que ~`3d` réels effectifs sur les `d²` disponibles, quel que soit
  `d`. Tout protocole testant « l'hermitien préserve-t-il mieux
  l'information » doit utiliser un encodeur `R^768 → Herm(d)` **plein
  rang** (sortie linéaire non contrainte de dimension `d²`, reshapée sous
  contrainte hermitienne), sinon la comparaison handicape artificiellement
  le côté hermitien.

**Objectif reformulé :** pour que la question soit une vraie recherche sur
la compression (et falsifiable), choisir `d` tel que `d² ≪ 768` (ex.
`d=16` → `d²=256`, facteur ×3 ; `d=8` → `d²=64`, facteur ×12 — valeur(s)
à arbitrer avec Bertrand), pas `d² ≈ 768`.

**Protocole de comparaison (à budget de réels strictement égal) :**
1. **Baseline réelle** : encodeur `R^768 → R^{d²}` (bottleneck non
   contraint), décodeur vers tâche/reconstruction, mesure de dégradation.
2. **Variante hermitienne** : encodeur `R^768 → Herm(d)` plein rang (même
   budget `d²` réels), traitement hermitien (attention/FFN à adapter à
   l'échelle `d`), décodeur équivalent, même mesure.
3. Comparaison à budget de réels égal, seuil de significativité fixé
   *avant* le run (falsifiabilité, cf. `CLAUDE.md`).

**Métrique d'« information utile préservée » — à arbitrer avec Bertrand
avant tout run** (ne pas mélanger, cf. principe de séparation stricte,
`docs/test_plan.md`) : fidélité de reconstruction (distance
Hilbert-Schmidt/MSE), perplexité après distillation, ou score GLUE après
fine-tuning — chacune répond à une question différente.

**Note d'architecture générale (Bertrand, 2026-08-14) :** le travail à `d`
réduit doit rester généralisable à `d` couvrant l'espace d'origine
(`d² ≥ 768`) si le coût est accepté — paramétrer `d` comme hyperparamètre
du code, pas dupliquer l'implémentation par taille.

**Point ouvert avant tout codage :** valeur(s) de `d` cible et métrique de
succès à fixer avec Bertrand (cycle de développement obligatoire,
`CLAUDE.md` : Q&R et seuils de falsifiabilité avant de coder).

---

## Historique des phases complétées

<!-- Déplacer ici les phases terminées avec date de complétion -->
