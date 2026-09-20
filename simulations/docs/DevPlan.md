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

**Piste explorée et écartée (Bertrand, 2026-09-13)** : hypothèse que la
préférence pour la violation relationnelle (`Q_global`) sur la violation
locale (`Q_i`) à `nN=3` s'expliquerait par l'existence de « solides de
Platon hermitiens » stables à cette taille (concept de
`contributions/gémini/Hopfield_Géométrie_Sacrée_atome_Mémoire`, lignes
917-1036). Écartée pour deux raisons indépendantes : (1) la prémisse a
disparu — l'exploration multi-tirages ci-dessous montre que `nN=3` n'a
rien d'anormal (82 % de violation locale, comparable aux autres tailles) ;
(2) même sans (1), le pont mathématique n'existe pas — un « solide de
Platon hermitien » y est défini comme un sous-groupe fini de réflexions
complexes de `U(n)` (classification de Shephard-Todd) agissant sur la
base propre d'une matrice hermitienne, pas indexé par un nombre de nœuds
scalaires ; aucun des 5 solides de Platon réels n'a d'ailleurs 3 sommets.
Notre `W` (rang ≤2, construit à partir de 2 motifs) n'est pas construit
pour avoir une base propre à symétrie de polytope complexe régulier —
établir un tel lien demanderait une construction dédiée, non faite ici.

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
- [x] feat(superposition): harnais Monte-Carlo (`nS×M` sous-ensembles,
  calcul de `K(nS)`, `Q_global` et `Q_i` agrégé) — `src/superposition/harness.py`
- [x] test(superposition): TI — I-04 vert. **Écart au plan initial** :
  n'a pas reproduit la paramétrisation exacte saturant `K(3)=3/2`
  (non retrouvée dans la source consultée) ; régression construite sur
  deux faits plus modestes mais vérifiés : `dt=0` ⇒ `K(3)=1.0` exactement
  (borne classique, corrélation triviale), et un balayage de `dt` ne
  dépasse jamais la borne quantique `1.5` tout en violant la borne
  classique pour au moins une valeur — suffisant comme garde-fou de
  régression contre un bug de signe/règle de Born, cf.
  `tests/test_superposition_harness.py`.
- [x] experiment(superposition): premier run complet (2026-09-13) —
  `src/superposition/experiment.py` (`generate_patterns` : deux motifs à
  phases aléatoires indépendantes, normalisés `‖ξᵏ‖=1` pour garder les
  valeurs propres de `W` ~indépendantes de `nN`, seed déterministe par
  `nN`), `dt=1.0` fixé *avant* le run (calibré sur le cas `nN=2` à la main
  de I-04). Résultats archivés dans `docs/results/i05_run_2026-09-13.json`.

  **Résultat : PARTIEL, non concluant.**

  | nN | K3_global | σ_global | K3_local | σ_local |
  |---|---|---|---|---|
  | 2 | +1,020 | 0,74 | +1,067 | 3,30 |
  | 3 | +1,193 | 2,13 | +0,911 | −1,71 |
  | 5 | +1,160 | 3,38 | +1,181 | **5,67** |
  | 10 | +1,133 | 2,16 | +1,113 | 4,68 |
  | 20 | +1,047 | 1,29 | +1,077 | **6,88** |

  Seuls 2 des 10 tests franchissent le seuil de 5σ pré-enregistré
  (`nN=5` et `nN=20`, tous deux sur `Q_i` agrégé). `Q_global` ne franchit
  jamais 5σ. Aucune tendance monotone avec `nN`. `nN=3` (local) ne montre
  même pas de violation nominale de la borne classique.

  **Deux limites méthodologiques identifiées après coup (transparence,
  pas un ajustement du résultat) :**
  1. Un contrôle de cohérence exact (sans bruit) réalisé *avant* le run
     stochastique avait déjà montré que la marge de violation réelle
     (`Δ≈0,05` à `0,19` selon `nN`) est bien plus faible que la marge
     théorique maximale (`Δ(3)=0,5`) utilisée pour calculer `M=300` —
     `M=300` est donc sous-dimensionné pour `Q_global` en particulier
     (`M` requis pour 5σ à ces marges réelles : de l'ordre de 2000 à
     30000 selon `nN`, contre 300 supposés suffisants). Le protocole
     pré-enregistré a néanmoins été exécuté tel quel, sans ajustement de
     `M` a posteriori (falsifiabilité, `CLAUDE.md`).
  2. **Un seul tirage de motifs par `nN`** : la variation observée entre
     tailles de réseau confond deux sources — un éventuel effet de `nN`
     et le hasard du tirage spécifique des deux motifs à cette taille.
     Distinguer les deux demanderait plusieurs réalisations de motifs par
     `nN` (moyennées ou testées en famille), pas encore fait.

  **Décision (Producteur, `CLAUDE.md`) initiale : résultat non cité dans
  `Simulations_API.md`.** Un résultat mixte, sans tendance claire et
  n'atteignant le seuil pré-enregistré que sur 2 tests sur 10, n'est pas
  un résultat stable au sens des règles Producteur.

  **Comment relancer** (cf. `scripts/run_superposition_i05.py`) :
  ```bash
  # Protocole initial (M=300 fixe pour tout nN)
  python scripts/run_superposition_i05.py --n-nodes 2 3 5 10 20 --dt 1.0 --m-samples 300

  # M recalculé par nN à partir de la marge exacte (sans bruit), cible 5σ
  python scripts/run_superposition_i05.py --auto-m --sigma-target 5.0
  ```

- [x] **Second run, `M` recalculé par `nN` (2026-09-13, limite 1 levée)** —
  `M` recalculé via `required_m_for_significance(delta, n_s=3, z_target=5.0)`
  à partir de la marge de violation **exacte** (sans bruit, calcul
  déterministe, pas la sortie stochastique du run précédent — ce n'est
  donc pas un ajustement a posteriori sur un résultat déjà observé, mais
  un recalibrage légitime sur une quantité indépendante du bruit
  d'échantillonnage). Résultat archivé (écrase le fichier précédent) :
  `docs/results/i05_run_2026-09-13.json`.

  | nN | M | K3_global | σ_global | K3_local | σ_local |
  |---|---|---|---|---|---|
  | 2 | 32382 | +1,048 | 15,97 | +1,051 | 24,02 |
  | 3 | 8727 | +1,109 | 6,41 | +0,878 | **−12,64** |
  | 5 | 6013 | +1,126 | 11,97 | +1,214 | 30,32 |
  | 10 | 2058 | +1,183 | 7,44 | +1,103 | 11,13 |
  | 20 | 27914 | +1,052 | 15,99 | +1,088 | 75,07 |

  **9 des 10 tests franchissent maintenant 5σ**, largement. Le seul qui ne
  le fait pas (`nN=3`, local) montre au contraire une **absence
  significative** de violation (`σ=−12,64`, confiance statistique élevée,
  pas juste « non concluant ») — alors que `Q_global` pour ce même réseau
  viole nettement (`σ=6,41`). C'est une confirmation empirique concrète de
  la précision logique actée le 2026-09-13 : violation de `Q_global`
  n'implique pas violation du `Q_i` local — ici un cas où la non-classicité
  semble portée par le couplage (« source 2 »), pas par les nœuds pris
  isolément, pour cette instance de réseau.

  **Limite 2 non levée, reste la réserve principale avant toute
  citation** : chaque `nN` ne repose que sur un seul tirage de motifs —
  le caractère distinctif de `nN=3` peut être une propriété réelle de
  cette taille ou un artefact de ce tirage spécifique. Non tranché.

  **Décision (Producteur) actualisée : toujours pas cité dans
  `Simulations_API.md`.** Malgré la significativité statistique désormais
  large, la limite 2 (tirage unique par `nN`) reste un vrai problème de
  robustesse, pas une formalité — un résultat cité en Strate 1 doit être
  reproductible dans son essence, pas seulement dans ses seeds. Prochaine
  étape suggérée : répéter plusieurs tirages de motifs par `nN` avant
  toute décision de citation, à valider avec Bertrand.
- [x] **Répétition multi-tirages, `nN=3` et `nN=10` (2026-09-13, demande
  Bertrand)** — `exact_realization`/`run_multi_realization_exact`
  (`src/superposition/experiment.py`) : 50 tirages de motifs indépendants
  par `nN` (seeds `50000+nN×1000+i`, namespace distinct de `run_nN_protocol`),
  `K(3)` **exact** (sans bruit d'échantillonnage — pas un test statistique
  par tirage, une exploration de la distribution du signal seul, moins
  coûteuse).

  | nN | K3_global (moy.±ét.) | % tirages violant | K3_local (moy.±ét.) | % tirages violant |
  |---|---|---|---|---|
  | 3 | +1,143 ± 0,164 | 86 % | +1,069 ± 0,316 | 82 % |
  | 10 | +1,134 ± 0,132 | 100 % | +1,114 ± 0,049 | 94 % |

  **L'anomalie `nN=3` du premier tirage (seed 1003, absence de violation
  locale) ne tient pas** : c'est un tirage minoritaire (18 % des tirages
  à `nN=3` ne violent pas), pas une propriété caractéristique de cette
  taille de réseau — la moyenne sur 50 tirages viole nettement (82 %).
  `nN=10` est notablement plus stable (écart-type local ≈6× plus petit) —
  en partie mécanique (moyenner sur 10 nœuds réduit la variance plus que
  sur 3, indépendamment de toute physique), pas nécessairement un effet
  qualitatif propre à cette taille.

  **Statut méthodologique de cette exploration : pas encore une
  confirmation citable.** Nombre de tirages (50) et le fait de raisonner
  sur `K3` exact plutôt qu'un test statistique par tirage n'ont pas été
  pré-enregistrés avant analyse — c'est une exploration qui répond à la
  question posée (le tirage initial était-il représentatif ?), pas le
  protocole confirmatoire final. Pour une citation dans
  `Simulations_API.md`, il faudrait pré-enregistrer un test formel (ex. un
  test binomial sur le taux de violation à 5σ par tirage, sur un nombre de
  tirages et un seuil fixés avant de lancer), pas encore fait.
- [x] docs: mise à jour `Simulations_API.md` — **fait le 2026-09-18**,
  cf. protocole confirmatoire et résultat ci-dessous

#### Protocole confirmatoire pré-enregistré (2026-09-13)

**Écrit avant de lancer le moindre nouveau tirage** (cf. discussion avec
Bertrand : la différence entre l'exploration précédente — regarder après
coup — et un test confirmatoire — annoncer le protocole avant de
l'exécuter). Rappel du cadre, en toute franchise : ce protocole démontre
avant tout notre capacité à construire correctement ce calcul binomial
dans ce cas précis (dimensionner `M` par tirage, calibrer `p_null` sur le
taux de faux positif réel du critère 5σ, combiner `n_realizations` tests
indépendants) — pas une découverte de physique nouvelle. Le garder en tête
pour ne pas sur-interpréter le résultat.

**Réseaux ciblés :** `nN=3` et `nN=10` (les deux explorés précédemment).
**`n_realizations` = 30** tirages de motifs frais par `nN` (seeds
`90000+nN×1000+i`, namespace disjoint de `run_nN_protocol` — 1000/2000/
3000 — et de l'exploration — 50000 —, vérifié par test, cf.
`tests/test_superposition_experiment.py`).
**`dt=1.0`** (inchangé, calibré en I-04).
**Critère de succès par tirage :** `M` dimensionné via
`required_m_for_significance` à partir de la marge **exacte** de ce
tirage (déterministe, calculée avant toute mesure stochastique — pas un
ajustement a posteriori), puis test `Q_global` complet ; succès si
`σ ≥ 5,0`.
**Plafond de budget de calcul pré-enregistré : `M ≤ 200 000`.** Un tirage
dont le `M` requis dépasserait ce plafond est compté comme un **échec**
(la marge existe mais son coût de vérification est déraisonnable) —
décidé à l'avance, pas en cours de route (cf. le run de calibration qui a
montré que certains tirages exigent des `M` de plusieurs millions, ce qui
aurait bloqué le calcul sans ce plafond).
**`p_null` du test binomial final** = taux de faux positif réel du
critère « 5σ par tirage » sous l'hypothèse nulle stricte, calculé (pas
choisi) : `p_null = P(Z≥5) ≈ 2,87×10⁻⁷` (`one_sided_normal_tail_probability`).
**Seuil de décision pour le résultat global :** `p_value` du test binomial
(`binomial_test_pvalue(k_succès, 30, p_null)`) `< p_null` elle-même
(même standard 5σ appliqué à la conclusion globale, cohérence avec le
reste du projet — pas un nouveau seuil ad hoc).

**Commande** (cf. `scripts/run_superposition_confirmatory.py`) :
```bash
python scripts/run_superposition_confirmatory.py --n-nodes 3 10 --n-realizations 30
```

**Résultat (2026-09-18, `docs/results/confirmatory_run_2026-09-18.json`) :**

| nN | tirages testés (`M≤200000`) | dont succès (5σ) | échecs « M requis > plafond » | `k_succès/30` | `p_value` |
|---|---|---|---|---|---|
| 3 | 20 | 17 | 10 (33 %) | 17/30 | 7,13×10⁻¹⁰⁴ |
| 10 | 25 | 24 | 5 (17 %) | 24/30 | 5,63×10⁻¹⁵² |

Les deux `p_value` sont infiniment en-dessous du seuil pré-enregistré
(`p_null≈2,87×10⁻⁷`) — décision : **rejet net de l'hypothèse nulle
« taux de violation nul » pour `nN=3` et `nN=10`.** Même en comptant les
tirages « `M` requis `>200000` » comme des échecs purs (traitement
conservateur), le résultat reste écrasant.

**Le taux d'échecs « M trop grand » plus élevé à `nN=3` (33 % contre
17 % à `nN=10`) n'est pas une observation nouvelle — c'est la
confirmation quantitative de l'exploration à 50 tirages déjà documentée
ci-dessus** : l'écart-type de `K3_global` y était déjà plus élevé pour
`nN=3` (0,164) que pour `nN=10` (0,132), signe d'une distribution plus
étalée avec davantage de tirages proches de la frontière classique.
Comme `M` requis varie en `1/Δ²`, un écart-type modérément plus grand se
traduit mécaniquement par une proportion nettement plus élevée de tirages
à marge quasi nulle, donc invérifiables dans le budget de calcul fixé.
Le lien entre les deux observations (variance plus grande ↔ plus
d'échecs de vérification) est donc attendu et cohérent, pas une
coïncidence à expliquer séparément.

**Ce que ce résultat établit, précisément, et ce qu'il n'établit pas** :
il démontre qu'un taux de violation de la borne de Leggett-Garg
significativement non nul, sur des tirages de motifs frais et un
protocole entièrement pré-enregistré, est statistiquement incompatible
avec l'absence totale de l'effet — pour `nN=3` et `nN=10`, dans ce modèle
spécifique (phasor scalaire, `W` à deux motifs, régime unitaire cohérent).
Comme signalé avant de lancer ce run : la contribution principale de
cette étape est méthodologique (construire correctement le calcul du
seuil `M` par tirage et du test binomial calibré), pas une nouvelle
affirmation physique — le résultat confirme la présence répétée de
violations déjà vues dans l'exploration précédente, il ne l'étend pas
qualitativement.

**Décision (Producteur) : condition de citation remplie.** Contrairement
aux deux étapes précédentes, celle-ci est un protocole confirmatoire
complet (pré-enregistré avant le run, seeds fraîches, seuil fixé à
l'avance, résultat comparé sans ajustement). **Entrée committée dans
`docs/Simulations_API.md` le 2026-09-18** (`contract_version: 2026-09-18-v2`,
entrée `[PENDING: RadioHumaine]` dans `Simulations_API_CHANGELOG.md`) —
validée par Bertrand avant commit. Registre choisi délibérément technique
(notes de travail scientifique) : la prose Stratégie A* pour le lecteur
du livre reste à écrire depuis une session sur le manuscrit
`RadioHumaine`, pas depuis `simulations/`.

### Recherche — Équivalence Hopfield : formule vs énergie (2026-09-20)

**Origine :** réserve soulevée par Bertrand le 2026-09-18 (cf.
`docs/TODO.md`) — le fil conducteur du projet est que BERT se ramène à un
Hopfield (Ramsauer et al. 2020) plongé dans l'espace hermitien ; rien
n'avait vérifié si cette équivalence tient encore une fois la couche
complète (FFN+Norm+résiduelle) assemblée. Dérivation faite le
2026-09-20, en réponse.

**Deux sens distincts d'« équivalence Hopfield », à ne plus confondre :**

1. **Équivalence de formule** — l'attention hermitienne et `hopfield_step`
   calculent littéralement la même expression, `softmax(β·Re(QK†))·V`,
   pour `Q,K,V` **quelconques**. C'est ce qu'établit `test_u03_equivalence_general_qkv`
   (Phase 1). C'est vrai par construction (les deux implémentations codent
   la même formule) — une garantie d'implémentation correcte, pas une
   affirmation physique sur une dynamique d'attracteurs.
2. **Équivalence dynamique/énergétique** — l'existence d'une fonction
   d'énergie `E` dont la règle de mise à jour est (une approximation
   discrète de) la descente de gradient, garantissant la convergence vers
   des attracteurs (la propriété qui donne un sens physique au mot
   « Hopfield »). C'est la propriété que Ramsauer et al. (2020) prouvent
   — **mais uniquement pour le cas auto-associatif**.

**Vérifié à la source (WebFetch, arXiv:2008.02217, 2026-09-20)** : Ramsauer
et al. définissent `E(ξ) = -lse(β,X^Tξ) + ½ξ^Tξ + const` (leur éq. 2), dont
le gradient donne exactement `X·softmax(βX^Tξ)` (leur éq. 3) — la même
matrice `X` sert à comparer (dans le softmax) et à reconstruire. Quand ils
passent à l'attention du transformeur avec `Q,K,V` séparés (leur éq. 10),
c'est une **observation formelle** (« ceci est l'attention du
transformeur »), **pas une preuve que la propriété d'énergie/Lyapunov
survit** quand la matrice de reconstruction (`V`) diffère de la matrice de
comparaison (`K`).

**Dérivation propre (2026-09-20), pour préciser la condition exacte :**

`∇_ξ lse(β,K^Tξ) = K·softmax(βK^Tξ)` (calcul direct, log-sum-exp). Donc la
sortie de l'attention `V·softmax(βK^Tξ)` est un gradient exact **si et
seulement si `V=K`** — une condition sur `V` vs `K`, indépendante de
`Q` vs `K` (qui, lui, ne joue aucun rôle dans cette dérivation ; c'est la
condition testée par erreur en Phase 1 pour l'équivalence de *formule*,
qui elle est inconditionnelle).

En posant `f(x) = x + Attention(x)` avec `V=K=X` :
```
f(x) = x + X·softmax(βX^Tx) = x + ∇_x lse(β,X^Tx)
```
un pas d'Euler de **montée** de gradient sur `lse(β,X^Tx)` seul (sans le
terme quadratique de régularisation de Ramsauer — donc non borné en
norme, divergerait). C'est exactement ce que corrige l'étape suivante :
`RMSNorm` force `‖sortie‖ = γ√d`, une valeur **constante indépendante de
l'entrée** (déjà prouvé, `test_rmsnorm_output_rms_is_gamma`) — c'est-à-dire
une **rétraction sur une sphère de rayon fixe**, la technique standard de
montée/descente de gradient contrainte à une variété (pas dans l'espace
ambiant, puis projection sur la contrainte).

**Résultat :** `Attention + résiduelle + RMSNorm` correspond exactement à
un pas de montée de gradient projetée sur `lse(β,K^Tx)`, contraint à une
sphère — **mais seulement si `V=K`**. `LayerNorm` (qui centre avant de
diviser) projetterait sur une variété différente (sphère ∩ hyperplan
orthogonal à `𝟙`, pas la sphère simple) — **second argument théorique
indépendant**, distinct de la préservation de phase déjà établie, en
faveur de `RMSNorm` comme architecture par défaut dans ce cadre précis.

**Conséquence qui déplace le problème plus loin que prévu** : BERT réel
apprend `W_K` et `W_V` **indépendamment** (`V≠K` systématiquement, jamais
la condition auto-associative). Donc le sens (2) — la garantie
d'attracteur — **n'a jamais été établi, même pour le bloc d'attention
seul avec de vrais poids pré-entraînés**. Le trou n'est pas localisé au
FFN/à la norme comme initialement supposé : il existe déjà à la racine,
dès qu'on utilise des poids réels plutôt que des poids synthétiques
auto-associatifs (comme dans `test_u03_equivalence_auto_associative`,
Phase 1, qui teste précisément — et seulement — ce cas particulier).

**Reste ouvert, non résolu :**
- ~~Le FFN n'a aucune dérivation d'énergie à ce jour~~ — **exploré le
  2026-09-20, cf. sous-section suivante.**
- Vérifier si `Q≠K` (qui ne casse pas l'équivalence de *formule*, déjà
  prouvée inconditionnelle) affecte ou non la dérivation d'énergie
  ci-dessus au-delà de la condition `V=K` déjà identifiée.
- Conséquence pour toute affirmation Strate 1 : porter les poids de BERT
  garantit l'équivalence de *formule*, jamais la dynamique d'attracteur —
  à formuler explicitement avant toute citation dans `Simulations_API.md`
  qui s'appuierait sur le mot « Hopfield » au sens physique, pas
  seulement computationnel.

#### Krotov (formalisme de Lagrangien, *Hierarchical Associative Memory*) — exploré le 2026-09-20

**Vérifié à la source** (Read direct du PDF, arXiv:2107.06446, Krotov,
*Hierarchical Associative Memory*, 2021 — MIT-IBM Watson AI Lab/IBM
Research) — pas une lecture de mémoire.

**Ce que le formalisme apporte réellement :** une énergie générale se
construit à partir d'une fonction de Lagrange `L(x)` par couche, l'activation
étant définie comme `g=∂L/∂x` (éq. 1), et la dynamique comme
`τ dx/dt = Σ W·g − x` (éq. 2). Ceci couvre **n'importe quelle fonction
d'activation** (pas seulement `softmax`) — donc notre gate FFN
`g(z)=z·Φ(Re(z))` serait couvrable en principe.

**Mais la contrainte structurelle est la même que celle qu'on avait déjà
trouvée par dérivation propre, généralisée à toute paire de couches** —
citation directe du papier (p.5) : *« the feedforward weights and the
feedback weights are equal, which is a consequence of the symmetry »*, et
(p.6, explicite) : *« if this constraint is violated it is impossible to
derive an energy function »*. Dans le schéma à deux couches de la Fig. 2
du papier (l'équivalent exact d'une étape d'attention dans ce formalisme),
**une seule matrice `ξ` sert à la fois à comparer et à récupérer** — il
n'existe pas, dans ce cadre, d'objet « clé » et d'objet « valeur »
distincts : c'est un seul ensemble de motifs stockés.

**Conclusion : Krotov ne fait pas disparaître le problème, il le
généralise et le confirme.** La condition `V=K` déjà trouvée pour
l'attention n'est pas une bizarrerie de la dérivation de Ramsauer — c'est
un cas particulier d'une contrainte structurelle qui s'applique à
**toute** paire de couches dans cette famille de modèles, y compris le
FFN (`W₂` devrait être la transposée de `W₁` pour une garantie d'énergie
— condition que le FFN de BERT réel, `W₁`/`W₂` indépendamment appris, ne
satisfait pas non plus).

**Ce que ça apporte de concret, malgré tout :**
1. **Réponse à « qu'est-ce qui porte l'attention dans Hopfield »**
   (question de Bertrand, 2026-09-20) : c'est l'objet unique de motifs
   stockés `X` — ce que le transformeur a scindé en `K`/`V` distincts en
   les apprenant séparément. Concept clair, transposable directement au
   modèle hermitien.
2. Un critère de conception explicite pour une variante **« Hopfield
   hermitien au sens strict »** (poids d'attention et de FFN
   volontairement liés — `V` dérivée de `K`, `W₂` dérivée de `W₁ᵀ` —
   plutôt qu'indépendamment appris), distincte de la variante
   « portage BERT » (fidèle à BERT, poids indépendants, jamais de
   garantie d'énergie). Les deux variantes répondent à des besoins
   différents et ne doivent pas être confondues dans le manuscrit.
3. Piste opérationnelle pour l'étape d'« apprentissage complémentaire »
   déjà proposée par Bertrand (portage = initialisation, puis affinage) :
   **cibler explicitement le rapprochement `V→K` et `W₂→W₁ᵀ`** comme
   terme de l'objectif d'entraînement, en plus de l'erreur de tâche — pas
   encore exploré (cf. discussion à suivre sur la méthodologie de
   projection initiale).

**Revue de la méthodologie de projection initiale (2026-09-20)** :
`WeightProjector`/`project_bert_attention` n'a jamais proposé ni implémenté
de mécanisme de tying `K=V` — les trois projections `q_proj`/`k_proj`/
`v_proj` sont trois appels indépendants à `_project_linear`, copiant les
poids de BERT appris séparément. Le seul endroit où `Q=K` (jamais `V=K`)
a été imposé est le test de scaffolding Phase 1
`test_u03_equivalence_auto_associative`, jamais intégré au chemin de
portage réel. L'entrée BUG-002 de `CorrectifPlan.md` a été annotée en
conséquence (sa mention « inconditionnelle Q,K,V quelconques » ne
concernait que l'équivalence de *formule*, jamais l'énergie).

### Recherche — Hopfield hermitien à poids liés (tying V=K) : protocole de décroissance d'énergie

**Décidé avec Bertrand le 2026-09-20** : avant d'implémenter le tying
`V=K`/`W₂=W₁ᵀ` comme variante architecturale, vérifier directement,
empiriquement et de façon falsifiable, la revendication centrale de
Krotov/Ramsauer — que le tying garantit une décroissance d'énergie sous
itération. Protocole en 3 temps, chacun pré-enregistré séparément (aucun
seuil ajusté après avoir vu un résultat) :

**Énergie utilisée** : `hopfield_energy` (`src/hopfield/equivalence.py`,
déjà implémentée en Phase 1, jamais exercée par un test jusqu'ici) —
`E(ξ) = -1/β·Σᵢ lse(β, Re(ξᵢ·Kⱼ†)) + ½‖ξ‖²`, le terme quadratique restant
constant sous rétraction `RMSNorm` (`‖ξ‖=γ√d` fixe, déjà prouvé par
`test_rmsnorm_output_rms_is_gamma`) — donc la monotonie de `E` se réduit à
celle du terme d'attraction `-lse` seul, une fois la rétraction appliquée.

**Mise en garde méthodologique explicite** : le théorème 2 de Ramsauer
(décroissance d'énergie prouvée) porte sur leur règle de mise à jour
*par remplacement* `ξ_new = X·softmax(β X^Tξ_old)` — pas sur la règle
*résiduelle* `ξ_new = RMSNorm(ξ_old + X·softmax(...))` utilisée ici (fidèle
à l'architecture transformeur réelle). Ce protocole ne cite donc pas le
théorème de Ramsauer comme s'appliquant directement — il teste
**empiriquement notre propre application discrète**, avec un pas
résiduel de taille 1 (pas infinitésimal), ce qui n'est pas couvert
automatiquement par l'analogie de descente de gradient contrainte déjà
établie (`docs/DevPlan.md`, section précédente).

**Étape 1 — `K` fixe, `ξ` itéré (Ramsauer strict, `V=K=K_fixe`)** :
- `d_model=16`, `T=5` (motifs/tokens), `β=1.0`, `num_steps=20`,
  `num_seeds=20` (`torch.manual_seed(seed)` pour `seed∈[0,20)`), `K_fixe`
  et `ξ₀` ~ `N(0,1)` i.i.d., `RMSNorm` non entraînée (`γ=1`).
- Critère de succès : `E(ξ_{t+1}) ≤ E(ξ_t) + tol` pour tout `t<num_steps`,
  pour toutes les graines, `tol=1e-4` (cohérent avec `ATOL` du projet,
  large devant le bruit FP32 attendu).
- Un seul échec (une graine, un pas) suffit à infirmer la revendication
  pour ce protocole.

**Étape 2 — sensibilité à la variabilité de `K`** :
- Même `d_model`/`T`/`β`/`num_steps`/`num_seeds`, mais `K_t = K_fixe +
  σ·bruit_t` (bruit gaussien frais à chaque pas, indépendant de `ξ`).
- Grille pré-enregistrée : `σ ∈ {0, 0.01, 0.05, 0.1, 0.2, 0.5, 1.0}`
  (échelle directement comparable : `K_fixe` est lui-même ~`N(0,1)`).
- Mesure : fraction des paires (graine, pas) respectant la monotonie
  (`tol=1e-4`) à chaque `σ`. Seuil de rapport pré-enregistré : le plus
  grand `σ` pour lequel cette fraction reste `≥95%` définit le seuil de
  robustesse mesuré — pas un pass/fail unique, une courbe.
- `σ=0` doit reproduire exactement l'étape 1 (garde-fou de cohérence).

#### Résultats — Étapes 1 et 2 (2026-09-20)

**Étape 1 : confirmée sans exception.** `tests/test_hopfield_tying.py::test_u08_tied_dynamics_energy_nonincreasing_k_fixed`
— sur les 20 graines pré-enregistrées, `E(ξ_{t+1}) ≤ E(ξ_t) + tol` tient à
chaque pas, du premier coup. Garde-fou de non-vacuité (`σ=5.0` casse bien
la monotonie sur au moins une graine) également vert. La dynamique
résiduelle réelle (`ξ + Attention(ξ)` puis rétraction `RMSNorm`, pas
infinitésimal, pas la règle de remplacement de Ramsauer) fait donc
décroître `E` empiriquement, malgré la mise en garde méthodologique
ci-dessus sur l'absence de garantie théorique directe pour cette forme
précise de mise à jour.

**Étape 2 : rupture nette, pas de dégradation progressive**
(`scripts/run_tied_energy_sensitivity.py`, résultat archivé dans
`docs/results/tied_energy_sensitivity_2026-09-20.json`) :

```
 sigma | fraction monotone
----------------------------------------
  0.00 | ################################################## 1.0000
  0.01 | ############################### 0.6175
  0.05 | ############################## 0.5925
  0.10 | ############################## 0.5950
  0.20 | ############################## 0.5900
  0.50 | ############################ 0.5675
  1.00 | ########################### 0.5400
----------------------------------------
```

Seuil pré-enregistré (« plus grand `σ` avec fraction `≥95%` ») :
**`σ=0` uniquement.** La fraction chute de 100 % à ~62 % dès le plus
petit bruit testé (`σ=0,01`, un centième de l'échelle de `K`), puis se
stabilise entre 54 % et 60 % sur deux ordres de grandeur de `σ`
supplémentaires — pas une dégradation continue, un effondrement immédiat
suivi d'un plateau.

**Lecture, sans équivoque** : la garantie de décroissance d'énergie du
tying `V=K` est une propriété du point exact, sans marge de tolérance
mesurable — elle ne survit à aucune perturbation non nulle de `K`, même
infinitésimale. Conséquence directe pour le choix de variante posé plus
haut (tying strict vs régularisation souple) : une **régularisation
souple** (rapprocher `V` de `K` sans les égaler exactement) n'offrirait
vraisemblablement **aucune garantie d'énergie, même approximative** —
seul un tying strict (`V:=K` exact, littéral) préserve la propriété
observée ici. Le rapprochement progressif envisagé initialement comme
piste d'apprentissage complémentaire (cf. section précédente, point 3)
n'a donc plus de fondement théorique tel qu'observé empiriquement pour
la propriété d'énergie — il pourrait rester pertinent pour d'autres
critères (ex. score de tâche), mais pas pour celui-ci.

**Étape 3 — `K` réévalué à partir de `ξ` (empilement réel, exploratoire,
Strate 2/3)** :
- `K_t = k_proj(ξ_t)` (projection apprise, réutilisée en boucle — pas de
  stimulus externe réinjecté, cf. discussion du 2026-09-20 : aucun
  mécanisme de ce type n'existe dans l'architecture actuelle), `V_t=K_t`
  tying forcé.
- Aucun théorème ne couvre ce cas, même avec tying — **pas de critère de
  succès/échec**, seulement une trajectoire `E(ξ_t)` rapportée et
  commentée (tendance : décroissante / oscillante / divergente).
- Ne doit jamais être présenté comme validant ou infirmant les étapes 1-2.

#### Résultat — Étape 3 (2026-09-20, observation, pas un test)

`scripts/run_tied_dynamics_real_stacking.py` (résultat archivé dans
`docs/results/tied_dynamics_real_stacking_2026-09-20.json`) : `k_proj`
= `ComplexLinear` non entraînée (poids aléatoires fixes par graine),
`V_t=K_t=k_proj(ξ_t)` recalculé à chaque pas.

**Observation, sur 20 graines, 20 pas :**
- **Monotonie stricte pas-à-pas : seulement 2/20 graines** — sans
  surprise, aucun théorème ne garantit cette propriété une fois `K`
  recalculé à chaque pas (mise en garde déjà actée ci-dessus).
- **Tendance globale (`E` au pas 0 vs `E` au pas 20) : décroissante pour
  20/20 graines**, sans exception — malgré l'absence de monotonie locale,
  l'énergie finit systématiquement bien plus basse qu'au départ (typ.
  `E₀≈45-67` → `E_final≈-10 à -47`).

**Lecture, en restant strictement dans le registre de l'observation** :
la dynamique réelle (K réévalué, sans tying figé) ne suit pas une
descente de gradient propre à chaque pas — des remontées locales
d'énergie sont la norme, pas l'exception — mais elle converge tout de
même, empiriquement et systématiquement sur cet échantillon, vers des
états de bien plus basse énergie après 20 pas. Ceci ne constitue **ni
une confirmation, ni une infirmation** de la propriété formelle des
étapes 1-2 : c'est un système dynamique différent (patterns mobiles, pas
fixes), pour lequel aucune garantie n'a été revendiquée. Piste ouverte,
non prioritaire : la tendance globale décroissante pourrait signaler une
propriété de contraction plus faible que la monotonie stricte (ex. une
décroissance seulement en moyenne, ou sur une fenêtre glissante) —
non caractérisée ici, à explorer séparément si jugé utile.

**Approfondissement (2026-09-20) — mécanisme testé, non confirmé.**
Trace détaillée sur une graine non-monotone (seed=1) : l'alignement
`cos(K_i,ξ_i)` monte jusqu'à un pic (~0,25 au pas 4-5) puis redescend et
devient négatif (~-0,35 au pas 20), alors que `E` continue de décroître
pendant toute cette seconde phase — le récit « auto-verrouillage sur sa
propre clé » ne tient pas sur l'ensemble de la trajectoire.

Hypothèse alternative testée, **vérifiée à la source** : le *rank
collapse*/*token uniformity* de l'attention pure avec résiduelle (Dong,
Cordonnier & Loukas, *Attention is Not All You Need: Pure Attention Loses
Rank Doubly Exponentially with Depth*, ICML 2021, arXiv:2103.03404) —
les représentations des tokens convergeraient vers une similarité
mutuelle croissante, ce qui augmenterait mécaniquement `lse` et donc
ferait baisser `E`. **Test direct (similarité cosinus moyenne entre
paires de tokens, 4 graines, avant/après 20 pas) : résultat mitigé, pas
de tendance unidirectionnelle** (2 graines vers plus de similarité, 2
vers plus de dissimilarité) — **hypothèse non confirmée sur cette
architecture**, vraisemblablement du fait de différences structurelles
avec le cadre du papier (poids partagés/itérés plutôt que distincts par
couche, `RMSNorm` sans centrage plutôt que `LayerNorm`, aucun FFN dans
cette dynamique). Le mécanisme exact de la décroissance globale
observée reste donc **non caractérisé** — traité comme une observation
ouverte, pas une régularité comprise, tant qu'une meilleure hypothèse
n'a pas été testée.

**Portée de ce protocole** : attention seule (`V=K`). Le tying FFN
(`W₂=W₁ᵀ`) reste hors scope ici — nécessite d'abord la dérivation d'une
fonction de Lagrange `L(z)` pour notre `gate(z)=z·Φ(Re(z))` telle que
`gate=∂L/∂z` (cf. formalisme de Krotov, non faite), sans quoi aucune
énergie FFN n'est même définie pour un test de décroissance.

### Recherche — Hopfield hermitien à poids liés (tying V=K) : FFN (2026-09-20)

**Blocage initial, indépendant du tying** : le test de Schwarz
(`∂g_réel/∂Im` vs `∂g_imag/∂Re`) appliqué à `gate(z)=z·Φ(Re(z))`
(`gating.py`, variante portage BERT) donne `0` contre `Im·φ(Re)` —
non conservatif, sauf sur `Im=0`. **Aucune fonction de Lagrange n'existe
pour ce gate**, donc aucune énergie FFN n'est définissable, quelle que
soit la condition sur les poids (`W₂=W₁ᵀ` ou non).

**Théorème général (vérifié le 2026-09-20, calcul direct + preuve par
séparation de variables)** : pour tout gate multiplicatif préservant la
phase `g(z)=z·s(z)` (`s` réel), la condition de conservativeness
`a·∂s/∂Im = Im·∂s/∂Re` équivaut, en coordonnées polaires
(`a=Re,Im=r sinθ`), à `∂s/∂θ=0` — **`g` est conservatif si et seulement
si `s` ne dépend que de `|z|`** (gate radial). Preuve : la condition
définit une EDP linéaire dont la seule solution réelle univoque
(périodique en `θ`) est `s(r)·e^{θ}` restreint à `θ`-indépendance, donc
`s=s(r)`.

**Trilemme qui en découle** : un gate radial `g(z)=z·s(|z|)` est
conservatif ET préserve la phase — **mais** `g(a,0)=a·s(|a|)` est
nécessairement une fonction **impaire** de `a` (`s(|a|)` pair), alors que
`GELU` ne l'est pas (`GELU(-2)≈-0.045 ≠ -GELU(2)≈-1.95`). **Phase
préservée, énergie, et portage exact à `GELU` réel ne peuvent pas être
satisfaits tous les trois simultanément.**

**Résolution actée avec Bertrand (2026-09-20)** : reconsidérer l'utilité
de l'exigence « portage `GELU` exact » avant de trancher. Cette exigence
ne sert qu'à valider la fidélité de la variante **portage BERT**
(`HermitianFFN`, gate `phase_preserving_gate`) — qui n'a jamais revendiqué
d'énergie. La variante **Hopfield hermitien strict** (`TiedHermitianFFN`,
tying `W₂=W₁†`) a *déjà* renoncé au portage exact dès l'étape attention
(`V:=K` diffère de `V` appris indépendamment par BERT) : lui imposer
`GELU` exact au FFN n'était jamais une contrainte cohérente. **Deux
gates pour deux variantes, rien d'essentiel sacrifié** :
`phase_preserving_gate` reste inchangé pour le portage BERT ;
`conservative_radial_gate(z)=z·Φ(|z|)` (`gating.py`) pour la variante
stricte — conservatif ET préservant la phase, avec Lagrangienne fermée
`radial_gate_lagrangian(r) = F(r) = ∫₀^r v·Φ(v) dv` (l'antidérivée de
`GELU` évaluée en `|z|` — toujours « à saveur GELU », construite sur le
module plutôt que sur `Re(z)`), vérifiée `∇L=g` par différences finies
(`tests/test_ffn_tying.py`).

**Implémentation** : `TiedHermitianFFN` (`src/hermitian/tied_ffn.py`) —
un seul jeu de poids appris (`fc1`), `fc2` n'existe pas : la sortie
utilise directement `conj(W₁)` (tying `W₂=W₁†` sans paramètre séparé),
pas de biais (cohérent avec Krotov). **Dérivation de Wirtinger complète**
(calcul à la main, vérifiée par différences finies) : avec `h=fc1(x)`
(linéaire, sans conjugaison) et `g` radial, `TiedHermitianFFN(x) =
∇_x Σ_a F(|h_a(x)|)` **exactement** — même structure que
`Attention(x)=∇_x lse(...)` pour l'attention liée. Énergie définie par
analogie directe : `E(x) = -Σ_a F(|h_a(x)|) + ½‖x‖²`
(`src/hopfield/ffn_tied_dynamics.py`).

**Protocole et résultat (même schéma que l'étape 1 attention — `W₁`
fixe, `x` itéré, `d_model=16`, `d_ff=32`, `T=5`, `num_steps=20`,
`num_seeds=20`, `tol=1e-4`)** : garde-fou de gradient exact vert
(`test_u09_ffn_tied_gradient_property_matches_lagrangian`), puis
**décroissance d'énergie confirmée sans exception sur les 20 graines**
(`test_u09_ffn_tied_energy_nonincreasing`) — même résultat que pour
l'attention à `K` strictement fixe. Cohérent avec l'étape 2 de
l'attention (rupture nette dès la moindre perturbation) : cette garantie
n'a pas été testée pour `W₁` variable ici (hors scope de cette passe,
piste identique disponible si jugé utile).

#### Forme de la fonction qui remplace `GELU`, coût de calcul, et étape 2 (2026-09-20)

**Forme exacte** (vérifiée par calcul direct) : à `Im=0`,
`conservative_radial_gate` se réduit à `h(a) = sign(a)·GELU(|a|)` —
c'est-à-dire la branche positive de `GELU` telle quelle (`a≥0` :
`h(a)=GELU(a)`, identique), reflétée en fonction impaire pour `a<0`
(`h(a)=-GELU(-a)`, au lieu de `GELU(a)` lui-même). Table de valeurs :

```
    a    GELU(a)    h(a)=sign(a)·GELU(|a|)
 -3.0    -0.0040    -2.9960
 -2.0    -0.0455    -1.9545
 -1.0    -0.1587    -0.8413
 -0.5    -0.1543    -0.3457
  0.0     0.0000     0.0000
  0.5     0.3457     0.3457
  1.0     0.8413     0.8413
  2.0     1.9545     1.9545
  3.0     2.9960     2.9960
```

**Différence qualitative importante** : `GELU` *supprime* doucement les
entrées négatives (`GELU(-2)≈-0,05`, quasi nul) — c'est précisément ce
qui fait son intérêt comme fonction de gating. `h`, elle, **amplifie**
les entrées négatives symétriquement aux positives (`h(-2)=-1,95`) —
identique en valeur absolue à `GELU(2)`, pas suppressive du tout. Ce
n'est plus une fonction de gating au sens usuel côté négatif : c'est une
fonction impaire, quasi-linéaire aux grandes valeurs (`h(a)→a` quand
`a→±∞`, contre `GELU(a)→0` pour `a→-∞`). Cohérent avec la preuve
générale (tout gate conservatif+préservant la phase doit être impair en
`Im=0`) — pas un défaut d'implémentation, une conséquence structurelle.

**Coût de calcul** (`scripts/run_ffn_tied_energy_sensitivity.py`,
mesure CPU, `d_model=768`, `d_ff=3072`, batch=8, `T=128`, moyenne sur
200 itérations après 10 d'échauffement) :

| | portage (`HermitianFFN`) | lié (`TiedHermitianFFN`) | ratio |
|---|---|---|---|
| FFN complet (forward) | 151,5 ms | 157,2 ms | **×1,04** |
| gate seul (isolé) | 14,3 ms | 24,1 ms | ×1,68 |
| paramètres de la couche | 9 444 864 | 4 724 736 | **×0,50** |

Le gate radial est ~68 % plus coûteux *isolément* (un `sqrt`+2 carrés en
plus pour `|z|`, contre `Φ(Re(z))` seul), mais le gate ne représente
qu'une fraction du coût total du FFN — dominé par les deux produits
matriciels (`fc1` et la contraction `conj(W₁)`). **Sur le FFN complet, le
surcoût est de ~4 %**, négligeable. Le tying **économise 50 % des
paramètres** de la couche (`fc2` n'existe pas) — bénéfice net, pas
seulement un coût neutre.

**Étape 2 (sensibilité à `W₁` variable), même protocole que l'attention** :

```
 sigma | fraction monotone
----------------------------------------
  0.00 | ################################################## 1.0000
  0.01 | ##################################### 0.7425
  0.05 | ################################ 0.6300
  0.10 | ############################ 0.5525
  0.20 | ######################## 0.4900
  0.50 | ######################## 0.4700
  1.00 | ######################## 0.4750
```

Seuil pré-enregistré (`≥95%`) : **`σ=0` uniquement, comme pour
l'attention** — même rupture nette dès `σ=0,01` (100 %→74 %), pas de
dégradation progressive, stabilisation vers ~47-63 % au-delà. **Conclusion
identique à l'attention, maintenant établie pour les deux composantes** :
la garantie d'énergie du tying (attention **et** FFN) est une propriété
du point exact, sans marge de tolérance mesurable.

#### `Q≠K` : un second trou, distinct de `V≠K` (2026-09-20)

**Question posée par Bertrand** : le protocole des étapes 1-3 pose
`Q=ξ` (l'état lui-même, pas de projection apprise) — exactement le
montage de Ramsauer, mais **pas** celui de BERT réel, où `Q=q_proj(x)`
est une projection apprise indépendante. Est-ce que la garantie
d'énergie (déjà acquise pour `Q=ξ`, avec `V=K`) survit à une vraie
projection `Q` ?

**Test direct** : symétrie du Jacobien de la sortie par rapport à `ξ`
(condition nécessaire pour qu'un champ soit un gradient — même principe
que le test de Schwarz du gate, généralisé en dimension `d`), avec
`V=K` fixé et `Q(ξ)=W_Q·ξ` :
- `W_Q=I` (cas déjà testé, étapes 1-3) : Jacobien symétrique. ✓
- `W_Q` quelconque (`≠I`) : **Jacobien non symétrique** — vérifié
  numériquement (`torch.autograd`, matrice 4×4, `W_Q` aléatoire).

**Conclusion : `Q≠K` casse la propriété d'énergie indépendamment de
`V≠K` — un second trou distinct, pas une variante du premier.** Même un
tying `V=K` parfait ne suffit pas si `Q` reste une projection apprise
non triviale — ce qui est systématiquement le cas dans toute
architecture BERT-like (`q_proj` toujours présent et distinct). Pour
qu'une couche d'attention hermitienne ait une énergie au sens de
Ramsauer/Krotov, il faudrait donc **également** contraindre `Q=identité`
(ou `Q=K` d'une façon qui préserve la symétrie du Jacobien — non
explorée) — une contrainte supplémentaire, en plus de `V=K`, jamais
mentionnée jusqu'ici dans ce projet.

#### Empilement complet (attention liée + FFN liée), poids fixes (2026-09-20)

**Question posée par Bertrand** : les deux composantes (attention,
FFN) sont chacune monotones séparément (étape 1 de chaque, `K`/`W₁`
fixes) — est-ce que ça reste vrai une fois assemblées dans une couche
Post-LN complète (`attention → RMSNorm → FFN → RMSNorm`), avec `K` et
`W₁` **tous deux fixes** (cas le plus favorable, sans même la
sensibilité de l'étape 2) ?

**Résultat (`scripts/run_full_stack_tied_check.py`, résultat archivé
dans `docs/results/full_stack_tied_check_2026-09-20.json`, même
protocole — 20 graines, 20 pas, `tol=1e-4`, énergie diagnostique =
somme des deux énergies séparées évaluées au même état) : NON, pas à
100 %.** 2 graines sur 20 violent la monotonie stricte (seeds 4 et 14 —
8 et 14 violations sur leurs 20 pas respectivement), avec des écarts
petits (`0,0001` à `0,013`, contre une plage totale d'énergie
d'environ 150 unités sur la trajectoire) apparaissant relativement tôt
(pas 6 et 12) puis persistant — pas un artefact numérique isolé, plutôt
une oscillation autour d'un point d'équilibre où les deux composantes
tirent dans des directions légèrement conflictuelles. **La tendance
globale (E₀ vs E_final) reste décroissante pour les 20/20 graines** —
la combinaison ne diverge pas, mais elle n'est plus strictement
monotone.

**Lecture, sans sur-interpréter ni minimiser** : ce n'est *pas* une
divergence catastrophique qui invaliderait toute la direction — mais
c'est la confirmation empirique attendue d'un fait mathématique simple :
**la somme de deux fonctions de Lyapunov, chacune décroissante sous son
propre champ de vecteurs, n'a aucune raison a priori de rester
décroissante sous une composition séquentielle des deux champs** (la
rétraction intermédiaire après l'attention déplace l'état dans une
direction qui n'a jamais été garantie compatible avec la descente du
FFN, et vice-versa). Combiné avec le trou `Q≠K` ci-dessus, ceci confirme
que **la propriété d'énergie du tying, même dans son cas le plus
favorable (`V=K`, `W₂=W₁†`, poids fixes), ne s'étend pas automatiquement
par simple empilement** — chaque nouvelle composition (attention+FFN,
`Q` non trivial, empilement multi-couches) doit être vérifiée
séparément, elle ne se déduit pas des garanties déjà établies sur les
parties.

#### Approfondissement (2026-09-20) — nature réelle des violations, structure des bassins, échelle du bruit

**Demande de Bertrand** : reformuler la question en termes de monotonie
*globale* de l'empilement plutôt que de monotonie stricte pas-à-pas —
si des bassins locaux se créent par accumulation de couches, ce serait
un problème mineur tant que la barrière séparant les bassins reste
faible devant le bruit du signal d'entrée (régime `K_ana` fort) ou
franchissable par un mécanisme de type effet tunnel (régime `K_ana`
faible).

**1) Les violations mesurées ne sont pas une barrière entre bassins.**
Inspection directe des deux trajectoires violantes (seeds 4 et 14) :
chacune atteint un **minimum**, puis remonte **doucement et
monotonement** vers sa valeur d'équilibre asymptotique (seed 4 :
minimum à `t=11` (`E=-101,4448`), puis remontée jusqu'à `E_final=
-101,4414` ; seed 14 : minimum à `t=6`, remontée similaire). C'est un
**dépassement (overshoot) à l'intérieur d'un seul bassin**, pas un
franchissement entre deux — signature typique d'une dynamique linéaire
**non normale** près du point fixe (le jacobien de la carte combinée
n'a aucune raison d'être symétrique, puisque l'énergie diagnostique
n'est une vraie potentielle que pour chaque composante séparément, pas
pour l'assemblage — croissance transitoire non normale, phénomène
classique, pas exotique).

**2) Mais la structure multi-bassins existe réellement, à une autre
échelle.** Test dédié : paysage figé (`K`, `W₁` d'une seule graine),
60 conditions initiales différentes, 60 pas. Résultat : **17 bassins
distincts** (regroupement des énergies finales à `±0,5`), avec des
écarts entre bassins voisins de **0,5 à 3,4** unités — contre une plage
totale d'environ 30 unités sur cet échantillon. Confirme directement
l'intuition de Bertrand : l'empilement crée bien des bassins locaux,
mais peu profonds à l'échelle du paysage global (à ne pas confondre
avec l'overshoot du point 1, phénomène différent, échelle ~0,01, 50 à
300 fois plus petit).

**3) Échelle de bruit nécessaire pour franchir ces bassins (test
direct, pas une extrapolation)** : bruit gaussien frais injecté sur
l'état à chaque pas, magnitude `σ`, paysage et condition initiale fixes,
10 tirages de bruit par `σ` :

```
sigma=0.000  étendue des E_final = 0.000
sigma=0.001  étendue = 0.020
sigma=0.005  étendue = 0.120
sigma=0.010  étendue = 0.230
sigma=0.020  étendue = 0.470
sigma=0.050  étendue = 1.140
sigma=0.100  étendue = 2.210
```

`RMSNorm` force `‖x‖~1` par token, donc `σ` se lit directement comme
une fraction du signal. **À `σ≈0,05-0,1` (5-10% du signal), l'étalement
induit par le bruit (1 à 2 unités) devient du même ordre que les écarts
inter-bassins mesurés au point 2 (0,5 à 3 unités).** En-dessous de
`σ≈0,02`, le bruit ne suffit pas à changer de bassin.

**Conclusion, sans sur-interpréter** : l'hypothèse de Bertrand est
confirmée quantitativement pour le régime `K_ana` fort — un bruit
d'entrée d'une magnitude réaliste (quelques % du signal) produit une
exploration entre bassins voisins de l'ordre de grandeur mesuré,
cohérent avec l'idée qu'une évolution énergique n'y reste pas piégée.
**Le régime `K_ana` faible / effet tunnel reste, lui, explicitement
hors de portée de la simulation actuelle** — le système codé ici est
classique et déterministe ; tester un mécanisme d'exploration
sub-seuil (tunneling ou équivalent) demanderait un formalisme
authentiquement stochastique (Langevin) ou quantique (amplitude WKB),
distinct de ce qui existe aujourd'hui. Ce n'est pas contredit par ce
qu'on a trouvé, mais ce n'est pas non plus démontré — piste distincte,
à traiter séparément si jugée prioritaire, pas à confondre avec le
résultat classique ci-dessus.

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

### Recherche — Régime `K_ana` faible : transfert unitaire entre bassins (2026-09-20)

**Origine :** correction méthodologique de Bertrand sur une proposition
antérieure (calcul WKB avec un `ħ_eff` libre) — cf. contribution Gémini
`contributions/gémini/implications_théorème_Stone`, qui établit que la
constante de Planck `ħ` n'a **aucune nécessité mathématique** dans le
théorème de Stone (elle n'est qu'un convertisseur d'unités entre
l'action mécanique et la phase, sans dimension physique intrinsèque en
unités naturelles `ħ=1`). Nommer notre paramètre libre « `ħ_eff` »
importait indûment cette connotation physique dans un contexte purement
informationnel — corrigé en le renommant **`Y`** (« Yod », suivant la
contribution), qui joue le rôle du générateur unitaire (Stone) dans
l'équation de Lindblad/GKSL `dρ/dt = -i/Y·[H,ρ] + K_ana·(dissipation)` :
`Y` gouverne la phase cohérente/réversible, `K_ana` le canal
dissipatif/projectif. Le ratio `Ξ=Y/K_ana` régule le régime — la
contribution affirme explicitement que `Ξ≫1` (régime `K_ana` faible)
rend « transparentes par effet tunnel de phase » des barrières
insurmontables en régime `K_ana` élevé. C'est cette affirmation précise
qui est testée ici, par **simulation exacte plutôt qu'approximation
WKB** — `Y` n'est pas nécessairement constant (la contribution le
traite comme un champ contextuel, `Y(t,ρ)`, pas une constante figée).

**Méthode : réutilisation intégrale du module `src/superposition/`**
(déjà construit et testé pour le protocole Leggett-Garg, régime unitaire
cohérent `γ=0`) — aucun nouveau formalisme. Les deux bassins voisins
déjà caractérisés (paysage tying complet, seed=14, cf. section
précédente) sont aplatis en un vecteur complexe unique
`nN=T×d_model=80` et jouent le rôle des deux motifs concurrents `ξ¹`/`ξ²`
du protocole Leggett-Garg (`build_two_pattern_weights`,
`evolution_operator=exp(-iW·Δt)`, `Δt` jouant le rôle de `t/Y`).

**Protocole (`scripts/run_basin_tunneling_unitary.py`, script autonome et
reproductible — reconstruit le paysage et retrouve la paire de bassins à
chaque exécution, seeds fixées, pas de dépendance à un fichier binaire) :**
- Paire de bassins voisins retrouvée (parmi 60 initialisations, paysage
  seed=14) : écart d'énergie classique `0,07` (le plus petit trouvé),
  recouvrement `|⟨ξ_A|ξ_B⟩|=0,33` (non nul — patterns non orthogonaux,
  dynamique non triviale garantie).
- État initial `z₀=ξ_A/‖ξ_A‖` (départ intégralement dans le bassin A).
- Grille de `Δt` pré-registrée informellement pendant l'exploration :
  `{0,1 ; 0,5 ; 1 ; 2 ; 5 ; 10 ; 20 ; 50}`.
- Mesure : `P_B(Δt)=|⟨ξ_B/‖ξ_B‖|U(Δt)z₀⟩|²` (calcul exact, pas de
  Monte-Carlo — une amplitude quantique fermée, pas une fréquence
  d'échantillonnage).

**Résultat (archivé dans `docs/results/basin_tunneling_unitary_2026-09-20.json`) :**

```
 dt (=t/Y)     P_B(dt)
      0.10      0.3294
      0.50      0.3398
      1.00      0.7920
      2.00      0.7465
      5.00      0.7002
     10.00      0.9035
     20.00      0.4532
     50.00      0.1194
```

**`P_B` atteint 90 % à `Δt=10`** — en partant intégralement dans le
bassin A, l'évolution unitaire pure (`K_ana=0`) place le système dans le
bassin B avec une probabilité écrasante, à une distance classique de
0,07 (négligeable devant la plage totale du paysage, ~30 unités). C'est
un **transfert que la dynamique classique dissipative ne produit jamais
spontanément** (démontré au sens strict : la descente de gradient
projetée par softmax converge vers un seul bassin et y reste, sauf
perturbation externe — cf. section précédente). Le profil non monotone
en `Δt` (oscillation, pas une simple montée) est la signature attendue
d'une oscillation de Rabi entre deux niveaux couplés — `W` est de rang
`≤2` par construction (`ξ_Aξ_A†+ξ_Bξ_B†`), donc toute la dynamique non
triviale se réduit exactement à un problème à deux niveaux, résolu ici
sans aucune approximation semi-classique.

**Statut méthodologique, honnêtement : exploratoire, pas confirmatoire.**
La grille de `Δt` et le choix de la paire de bassins (le plus petit
écart trouvé, donc le cas le plus favorable) n'ont pas été
pré-enregistrés avant de lancer ce run — exactement la même réserve que
pour l'exploration multi-tirages du protocole Leggett-Garg avant son
protocole confirmatoire (cf. Historique `docs/TODO.md`). Pour une
citation Strate 1, il faudrait répéter sur plusieurs paires de bassins
(pas seulement la plus favorable) et pré-enregistrer la grille de `Δt`
et le seuil de `P_B` avant de lancer.

**Ce qui est déjà solide, indépendamment du statut de citation** : la
méthode elle-même (réutiliser le module unitaire existant sur le
paysage d'énergie classique déjà caractérisé) est validée et rejouable
sans coût — bien moins cher qu'un calcul WKB avec masse/`Y` inventés, et
plus rigoureux (exact, pas semi-classique) dans le régime où elle
s'applique (rang de `W` petit).

**Reste ouvert :** un protocole confirmatoire (plusieurs paires de
bassins, seeds fraîches, grille de `Δt` et seuil de `P_B` fixés avant le
run) avant toute citation ; le rôle exact de `K_ana` dans une dynamique
GKSL complète (ici testé uniquement à `K_ana=0` strict, jamais à une
valeur intermédiaire — le régime réellement intéressant selon la
contribution Gémini, « Vénus », `Ξ∼Ξ_optimal`) ; la construction d'un
canal dissipatif `Lᵏ` explicite pour interpoler entre les deux régimes
déjà testés séparément (`K_ana` fort classique bruité, `K_ana=0` unitaire
pur) plutôt que de les traiter comme deux expériences disjointes.

#### Protocole confirmatoire — transfert unitaire entre bassins (pré-enregistré, 2026-09-20)

**Écrit avant tout nouveau run** (cf. `CLAUDE.md`, falsifiabilité avant
calcul) : le run exploratoire précédent a deux failles méthodologiques à
corriger avant toute citation, corrigées ici.

**Faille 1 — la grille `Δt` fixe risque de manquer le vrai maximum.**
Chaque paire de bassins a sa propre fréquence de Rabi (le système est
exactement un problème à deux niveaux, `W` étant de rang `≤2`) ; une
grille `Δt` unique appliquée à toutes les paires peut sous-estimer
fortement `P_B_max` pour une paire dont la fréquence naturelle tombe
entre deux points de la grille.

**Correction — réduction analytique au sous-espace invariant :**
`span(ξ_A,ξ_B)` est invariant sous `W=ξ_Aξ_A†+ξ_Bξ_B†`. Construction
d'une base orthonormée `{e₁,e₂}` (`e₁=ξ_A/‖ξ_A‖`, `e₂` = composante de
`ξ_B` orthogonale à `e₁`, normalisée), réduction de `W` à une matrice
hermitienne `2×2` exacte, diagonalisation directe (`torch.linalg.eigvalsh`),
fréquence de Rabi `Ω_R=λ₂-λ₁`. **Vérifié** : la réduction 2×2 reproduit
exactement le calcul complet `80×80` sur une grille adaptée à `Ω_R`
(écart `<3×10⁻³` sur `P_B_max`, cf. test de cohérence avant ce
pré-enregistrement). `P_B_max` calculé par balayage de `t` sur
`[0, 4π/Ω_R]` (au moins deux périodes de Rabi complètes, garanti par
construction — plus de grille arbitraire).

**Faille 2 — la paire de bassins du run exploratoire a été choisie
*après coup* comme « le plus petit écart trouvé »**, le cas le plus
favorable — biais de sélection, pas un échantillon représentatif.

**Correction — échantillon non biaisé :** **5 paysages fraîchement
tirés** (seeds `201, 202, 203, 204, 205` — namespace disjoint de tout ce
qui a déjà été utilisé : `14` du run exploratoire, `1000/2000/3000/50000/
90000` du sous-track Leggett-Garg). Pour chaque paysage : 60 conditions
initiales (seeds `300000+seed_paysage×1000+i`, `i∈[0,60)`), mêmes
paramètres que `run_full_stack_tied_check.py` (`d_model=16`, `d_ff=32`,
`T=5`, 60 pas de relaxation). Regroupement en bassins (tolérance `±0,5`,
comme précédemment). **Toutes les paires de bassins adjacents en
énergie** (pas seulement la plus favorable) sont testées — un paysage à
`n` bassins distincts fournit `n-1` paires.

**Critère de succès par paire, fixé à l'avance :** `P_B_max > 0,5`
(seuil naturel et significatif — « plus probable qu'improbable de
retrouver le système dans l'autre bassin » — pas un seuil ajusté après
coup).

**Rapport prévu** (pas de test statistique au sens Monte-Carlo : chaque
`P_B_max` est une amplitude quantique calculée exactement, sans bruit
d'échantillonnage — la question ici est la représentativité de
l'échantillon de paires, pas la significativité statistique d'une
mesure bruitée) :
- Fraction des paires testées franchissant le seuil `P_B_max>0,5`.
- Nuage de points `P_B_max` vs écart classique (`gap`) et vs
  recouvrement `|⟨ξ_A|ξ_B⟩|/(‖ξ_A‖‖ξ_B‖)` — rapporté tel quel, **aucune
  tendance n'est présupposée** (`gap` et `Ω_R` sont des objets
  mathématiques différents — le premier vient de l'énergie composite
  non linéaire `E(x)`, le second de la géométrie linéaire du sous-espace
  `span(ξ_A,ξ_B)` — rien ne garantit a priori une relation monotone
  simple entre les deux).
- Garde-fou de cohérence : vérifier que `P_B_max→0` quand le
  recouvrement `→0` (fait mathématique nécessaire — deux motifs
  orthogonaux sont des vecteurs propres exacts de `W`, sans terme
  croisé — déjà vérifié sur un couple aléatoire indépendant avant ce
  pré-enregistrement, `P_B_max≈0,009` pour un recouvrement quasi nul en
  dimension 80).

**Décision de citation** : si la fraction de paires au-dessus du seuil
est substantielle (pas de seuil numérique fixé ici pour cette fraction
elle-même — à discuter avec Bertrand une fois le résultat obtenu, la
question de la citation portant sur l'ensemble du tableau, pas sur un
chiffre unique), et que le garde-fou de cohérence est vert, alors le
résultat pourra être proposé pour `Simulations_API.md`.

#### Résultat du protocole confirmatoire — défaut de construction identifié (2026-09-20)

**`scripts/run_basin_tunneling_confirmatory.py`, résultat archivé dans
`docs/results/basin_tunneling_confirmatory_2026-09-20.json` : 80/80
paires franchissent `P_B_max>0,5` — mais `P_B_max=1,0000` exactement
pour les 80 paires**, y compris les deux à recouvrement quasi nul
(`0,037` et `0,048`). **Vérifié : ce n'est pas un bug, c'est un fait
mathématique exact, qui révèle un défaut de construction du test.**

**Dérivation** : toutes les paires de bassins ont exactement la même
norme (`‖ξ‖²=80`, imposé par `RMSNorm` sur chaque token, indépendamment
du bassin). Pour `W=ξ_Aξ_A†+ξ_Bξ_B†` avec `‖ξ_A‖=‖ξ_B‖=α`, calcul exact
(réduction 2×2, décomposition de Pauli) :

```
P_B(t) = 1 − (d²/α²)·cos²(|n|·t),   d²=α²−|c|²,  |n|=|c|α
```

`P_B_max=1` **dès que `|c|≠0`** (recouvrement non nul), quelle que soit
sa petitesse — le théorème du double puits symétrique (inversion de
l'ammoniac, etc.) : à profondeur égale, le transfert complet est une
certitude mathématique, seule la **fréquence** (`Ω_R=2|c|α`, donc le
temps d'attente `2π/Ω_R`) dépend du couplage, jamais l'amplitude
maximale.

**Conséquence : la construction hebbienne à poids égaux
(`build_two_pattern_weights`) efface l'écart d'énergie classique réel
entre les deux bassins avant même de commencer** — elle traite les deux
états comme deux souvenirs de poids strictement égal par définition.
`P_B_max` ne peut donc, par construction, jamais discriminer un
« bassin facile à franchir » d'un « bassin difficile » : il vaut
trivialement 1 pour toute paire non orthogonale. Le 80/80 n'est pas une
confirmation, c'est un artefact du choix de construction.

**Vérification directe (recalcul à partir des données déjà archivées,
`Ω_R=2×recouvrement×α²`)** : corrélation (Pearson) entre l'écart
classique (`gap`, l'objet qui nous intéresse — la hauteur de barrière
réelle du paysage `E(x)`) et la **période de Rabi** (le temps de
transfert, l'analogue correct du temps de franchissement WKB) :
**`r=-0,058`** (nulle) — contre **`r=-0,688`** entre le recouvrement
géométrique et cette même période. La vitesse du transfert quantique ne
dépend que de la géométrie des deux vecteurs aplatis dans `C^80`, pas du
tout de la barrière classique qu'ils représentent dans le paysage
composite non linéaire.

**Décision : aucune citation possible en l'état.** Ni le run
exploratoire ni ce protocole confirmatoire ne répondent à la question
initiale (le régime `K_ana` faible franchit-il plus facilement les
barrières classiques mesurées). Le résultat positif du run exploratoire
(`P_B` jusqu'à 90 %) était donc, lui aussi, un artefact de cette même
construction — pas une confirmation de tunnel « sensible à la
barrière », simplement la démonstration qu'un opérateur hebbien
symétrique connecte toujours ses deux motifs à terme, indépendamment de
tout paysage classique sous-jacent.

**Deux pistes de correction, à trancher avec Bertrand avant de
poursuivre** :
1. **Pondérer la construction hebbienne** par un poids reflétant la
   profondeur/énergie de chaque bassin (`W=w_Aξ_Aξ_A†+w_Bξ_Bξ_B†`) —
   simple à implémenter, mais le choix de `w_A,w_B` à partir de `E_A,E_B`
   reste arbitraire (Strate 2/3), pas dérivé d'un principe physique clair.
2. **Discrétiser directement le paysage `E(x)` réel** le long d'un
   chemin entre les deux bassins (chaîne de sites intermédiaires,
   énergie sur site = `E(x)` interpolé, terme de saut = énergie
   cinétique discrète) — un Hamiltonien de liaison forte (*tight-binding*)
   qui encode réellement la forme de la barrière, résolu exactement (pas
   de WKB), plus proche de l'intention initiale mais demande de définir
   proprement le chemin et le terme de saut avant de coder.

#### Piste 2 implémentée — chaîne de liaison forte sur le vrai paysage (2026-09-20)

**Suite à la remarque de Bertrand** (l'égalité des normes imposée par
`RMSNorm` est le défaut de fond, analogie explicite avec l'altitude sur
un globe terrestre absente d'une sphère de Bloch nue) : implémentation
de la piste 2. Chemin interpolé linéairement entre `ξ_A` et `ξ_B` en
représentation `(x_real,x_imag)`, **chaque point intermédiaire
renormalisé par token** (`HermitianRMSNorm`, `γ=1`, même module que
partout ailleurs dans le projet — pas un artefact d'échelle), `N=20`
intervalles. Énergie sur site `ε_n=E(x_n)` = la vraie énergie composite
(attention+FFN liées), calculée sur le même paysage que la paire de
bassins. Chaîne tridiagonale `H_nn=ε_n`, `H_{n,n±1}=-t` (`t` = terme de
saut, balayé), diagonalisée exactement. États localisés `L`/`R`
identifiés par leur poids réel en début/fin de chaîne (pas une
convention de signe supposée) — recombinaisons symétrique/antisymétrique
des deux états propres les plus bas.

**Ce qui marche** (`scripts/run_basin_tight_binding.py`, résultat
archivé dans `docs/results/basin_tight_binding_2026-09-20.json`) :
le profil `E(x_n)` montre une **vraie barrière** (jusqu'à `+31` unités
au-dessus des puits pour la paire testée la plus extrême) — le défaut
de la piste précédente (norme égale effaçant le relief) est corrigé,
le chemin réel entre à présent dans le calcul. En régime de faible
couplage (`hopping=0,01`), les états `L`/`R` sont effectivement
localisés (`L(0)²` jusqu'à `0,99`, `L(N)²≈0`) — le régime physique
attendu (double puits faiblement couplé) est retrouvé, contrairement à
la piste précédente où `P_B_max=1` était une certitude triviale
indépendante de tout.

**Ce qui reste confondu, honnêtement, avant toute conclusion** : sur
les 3 paires testées (même paysage, seed=14), la relation entre hauteur
de barrière et écart de séparation `ΔE_split` (à `hopping` fixe) n'est
**pas** celle attendue par l'intuition WKB (barrière plus haute →
séparation plus petite) — la paire à la plus haute barrière (`30,97`)
donne la plus grande séparation (`0,29`), pas la plus petite.
**Cause identifiée** : la distance euclidienne réelle entre `ξ_A` et
`ξ_B` diffère fortement selon la paire (`13,65` / `11,15` / `10,26`,
vérifié directement) et corrèle avec la hauteur de barrière — or `N=20`
est fixé indépendamment de cette distance, donc le pas physique par
site (`distance/N`) diffère d'une paire à l'autre. Un même `hopping`
nominal ne correspond alors pas au même couplage physique par unité de
distance selon la paire — confondant, pas encore contrôlé.

**Reste à faire avant toute conclusion** : fixer le pas physique
(`distance/N` constant — donc `N` proportionnel à la distance réelle
mesurée, pas une valeur fixe) plutôt que le nombre de sites, puis
répéter sur un échantillon plus large (`N_paires>3`) avant d'évaluer la
relation barrière/séparation. Non fait à ce stade — point d'arrêt
volontaire, à trancher avec Bertrand avant de relancer.

#### Confondant corrigé, relation toujours non conforme à l'intuition WKB (2026-09-20, second run)

**Correction appliquée** : `N` (nombre de sites) rendu proportionnel à
la distance euclidienne réelle entre `ξ_A` et `ξ_B` (`N=round(distance/
Δs_phys)`, `Δs_phys=0,5` fixé — pas physique par site désormais constant
d'une paire à l'autre, `N∈[15,29]` selon la paire). Échantillon élargi :
**53 paires**, 3 paysages (`seed=14,201,202`), toutes les paires
adjacentes en énergie de chaque paysage (pas seulement les plus
favorables).

**Résultat** (`scripts/run_basin_tight_binding.py`, données archivées
dans `docs/results/basin_tight_binding_2026-09-20.json`) :

```
Corrélation (Pearson) barrier_height vs delta_split(h=0,01)   :  0,286
Corrélation (Pearson) sqrt_action    vs delta_split(h=0,01)   :  0,315
Corrélation (Pearson) barrier_height vs delta_split(h=0,1)    :  0,288
```

Le confondant de distance est levé, mais **la corrélation reste faible
et de signe opposé à l'intuition WKB** (barrière/action plus grande
devrait donner une séparation plus *petite* — signe négatif attendu ;
on trouve `+0,29`, positif et faible). Ce n'est plus l'inversion nette
observée sur l'échantillon de 3 paires (où la paire à la plus haute
barrière donnait la plus grande séparation, de très loin) — l'effet
s'est atténué en élargissant l'échantillon, cohérent avec l'hypothèse
que la première observation était en partie un artefact de petit
échantillon — mais aucune relation nette du signe attendu n'émerge non
plus.

**Décision : aucune conclusion tirée, fil mis en pause ici.** Ni
confirmation, ni infirmation propre : le signal est trop faible pour
trancher avec cet échantillon et cette méthode. Poursuivre demanderait
de contrôler des facteurs supplémentaires non encore isolés (forme
exacte du profil au-delà de la hauteur/action scalaire, hétérogénéité
entre les 3 paysages, échelle d'énergie propre à chaque paysage non
normalisée entre paires) — un travail de contrôle plus lourd que ce qui
a été fait jusqu'ici, à ne pas engager sans arbitrage explicite.

### Recherche — Recadrage : superposition simultanée et intrication réseau/entrée (2026-09-20)

**Correction conceptuelle de Bertrand, fondamentale** : le fil « tunnel »
ci-dessus posait la mauvaise question. Le tunnel décrit un système
**déjà localisé** (après effondrement de la fonction d'onde) qui
s'échappe d'un puits vers un autre — une dynamique *séquentielle*
post-mesure. Ce qui intéresse le projet est l'**inverse** : la
coexistence cohérente de plusieurs bassins **avant** tout effondrement
(« le parcours simultané de l'ensemble des puits »), et le couplage de
cette superposition avec le vecteur d'entrée du réseau. Renvoie
directement à l'**Objectif 2**, jamais commencé, du plan d'origine
(`contributions/claude/plan_dev_simulation_superposition_intrication.md`,
2026-08-11) — reformulé : le second système couplé n'est pas un second
réseau, c'est le vecteur d'entrée lui-même.

**Piste théorique distincte, notée séparément, non encore développée**
(Bertrand, 2026-09-20) : analogie avec un signal sensitif analogique —
l'information captée en entrée subirait l'équivalent d'une
**transformée de Hilbert** pour initialiser la couche d'entrée
hermitienne (construction du « signal analytique »
`s_analytique(t)=s(t)+i·H[s](t)`, standard en traitement du signal pour
complexifier un signal réel en lui donnant amplitude et phase
instantanées bien définies). Ceci **expliquerait** pourquoi la
contribution Gémini (`BERT_hermitien_PoC`) posait d'emblée une couche
d'entrée hermitienne — pas un choix arbitraire, mais la construction
canonique pour complexifier un signal réel. Remettrait directement en
cause l'initialisation actuelle de la partie imaginaire dans
`WeightProjector` (bruit gaussien, `imag_std`) — à remplacer, pour la
couche d'entrée spécifiquement, par une construction de type Hilbert.
**Non traité maintenant** — chantier théorique à part entière, à
reprendre séparément.

**Choix tranchés avec Bertrand pour le test opérationnel** :
`N=8` bassins (intermédiaire, ni les 2 motifs du fil précédent ni la
totalité) — pris comme les **vrais** bassins déjà cartographiés d'un
paysage déjà utilisé (`seed=14`), pas des motifs synthétiques, pour
garder la possibilité de croiser avec les résultats du fil précédent.
`d=8` retenu pour toute représentation qubit-par-nœud à venir (renvoie
au chantier dormant « compression hermitienne pour portage mobile »,
`d=28/32` jamais tranché). **Métrique retenue** : entropie de
participation sur les 8 directions de bassin — pas le protocole
Leggett-Garg existant (`K(nS)`), qui repose sur un observable binaire
et ne généralise pas naturellement à `N=8` issues sans inventer une
variante ad hoc (le plan d'origine avertissait déjà de ce risque).

**Premier résultat, exploratoire** (`scripts/run_n_basin_superposition.py`,
`build_n_pattern_weights` généralisant `build_two_pattern_weights` à
`N` motifs, résultat archivé dans
`docs/results/n_basin_superposition_2026-09-20.json`) : état initial
localisé exactement dans le bassin 0, évolution unitaire pure
(`K_ana=0`), entropie de participation sur les 8 bassins :

```
dt (=t/Y)   entropie S   N_eff
     0.00       1.478    4.39   (recouvrement géométrique de fond, motifs non orthogonaux)
     0.05       1.987    7.29
     0.10       1.797    6.03
     0.50       1.721    5.59
     2.00       1.715    5.56
    10.00       1.810    6.11
    20.00       1.693    5.43
```
(maximum théorique : `S=2,079`, `N_eff=8`, distribution uniforme)

**Lecture** : même à `t=0`, l'entropie n'est pas nulle — les 8 bassins
ne sont pas orthogonaux, un recouvrement géométrique de fond existe
indépendamment de toute dynamique. Mais sous évolution unitaire pure,
l'entropie **augmente encore** dès les premiers pas et se stabilise sur
un plateau élevé (`N_eff≈5,5-6`, sur 8 possibles), **sans jamais
redescendre vers la localisation** sur toute la plage de `Δt` testée.
C'est la signature directe de la superposition simultanée recherchée —
le réseau reste dans une combinaison cohérente de plusieurs bassins à
la fois, pas une oscillation entre deux (le défaut du fil « tunnel »
précédent). **Statut : exploratoire**, pas encore pré-enregistré
(seuils/plage de `Δt` choisis pour l'exploration, pas fixés à l'avance)
— un protocole confirmatoire (plusieurs paysages, seeds fraîches, seuil
de `N_eff` fixé avant le run) reste à construire avant toute citation.

**Reste à faire** : (i) protocole confirmatoire, comme pour tous les
résultats précédents de ce fil ; (ii) ~~comparer au régime dissipatif~~
— **fait, cf. sous-section suivante** ; (iii) l'intrication
réseau/vecteur d'entrée (second volet du recadrage, pas encore
abordé — nécessite de promouvoir l'entrée en degré de liberté quantique
séparé, cf. discussion du 2026-09-20).

#### Contraste avec le régime dissipatif — deux faux départs, puis le bon modèle (2026-09-20)

**Faux départ 1 — déphasage aléatoire sur la base de coordonnées
brutes** (`scripts/run_n_basin_dissipative_contrast.py`, premier essai) :
à chaque petit pas, kick de phase aléatoire indépendant par coordonnée
(écart-type `√(2·K_ana·dt_small)`), moyenné sur 100 trajectoires.
**Résultat inattendu : l'entropie monte vers le maximum avec `K_ana`**
(`1,72` à `K_ana=0` → `2,08` à `K_ana=10`, soit la distribution
uniforme) — l'inverse de l'effondrement attendu.

**Faux départ 2 — même déphasage, mais sur la base de concepts**
(Gram-Schmidt/QR alignée sur les 8 motifs, pas la base de coordonnées
brutes — cohérent avec `L_k` = « projecteurs de concept » de la
contribution Gémini). **Même résultat qualitatif** (entropie vers le
maximum). Diagnostic correct : un déphasage sans collapse ne préserve
que les populations dans la base où il agit ; mesurer ensuite l'entropie
de la **moyenne d'ensemble** sur les trajectoires souffre d'un biais de
concavité (inégalité de Jensen — l'entropie d'une moyenne est toujours
`≥` la moyenne des entropies). Si des trajectoires différentes finissent
localisées sur des bassins différents, leur moyenne d'ensemble paraît
étalée même si chaque trajectoire, individuellement, est bien localisée.

**Correctif — véritable collapse projectif répété (règle de Born, effet
Zénon quantique)** : à chaque petit pas, un événement de mesure se
produit avec probabilité `1−e^{-K_ana·dt_small}` (processus de Poisson,
`K_ana` = taux) ; s'il se produit, mesure projective dans la base de
concepts (probabilités de Born sur les 8 projecteurs `|e_k⟩⟨e_k|` + un
9ᵉ pour « aucun concept nommé »), collapse effectif de l'état sur
l'issue tirée. **Entropie calculée par trajectoire, puis moyennée**
(pas l'inverse — corrige le biais de Jensen identifié).

**Résultat** (200 trajectoires par `K_ana`, résultat archivé dans
`docs/results/n_basin_dissipative_contrast_2026-09-20.json`) :

```
K_ana   <S> par trajectoire   <N_eff>
 0.00              1.7150       5.557
 0.10              1.7094       5.526
 0.50              1.7113       5.536
 1.00              1.6479       5.196
 5.00              1.4700       4.349
10.00              1.3349       3.799
```

**Correction (Bertrand, 2026-09-20) : ce n'est pas monotone strictement.**
`0,05→1,7082`, `0,10→1,7094`, `0,50→1,7113` remontent légèrement avant
de rebaisser — seulement 200 trajectoires, du bruit d'échantillonnage
plausible dans la partie basse de la grille (pas de barre d'erreur
calculée à cette étape, erreur de ma part de parler de monotonie sans
l'avoir vérifié). Ce qui est établi, sans ambiguïté : une **tendance
nette à la baisse** entre les extrêmes (`1,72` à `K_ana=0` contre
`1,33` à `K_ana=10`), passant sous le niveau de recouvrement géométrique
de fond (`1,478` à `t=0`). Le protocole confirmatoire ci-dessous
formalise cette comparaison par une vraie erreur-type plutôt qu'une
lecture à l'œil sur la grille.

**Statut : exploratoire**, comme le reste de ce fil — grille de
`K_ana`, nombre de trajectoires et paramètres de discrétisation choisis
pour l'exploration, pas pré-enregistrés. Protocole confirmatoire
toujours à construire avant toute citation.

#### Protocole confirmatoire — superposition maintenue et collapse dissipatif (pré-enregistré, 2026-09-20)

**Écrit avant tout nouveau run.** Deux affirmations distinctes à
confirmer séparément, chacune avec un critère statistique explicite —
pas de lecture à l'œil sur une grille, la leçon du faux départ
ci-dessus.

**Échantillon** : 3 paysages **fraîchement tirés** (seeds `301, 302,
303` — namespace disjoint de tout ce qui a déjà été utilisé dans ce
fil : `14, 201-205`), même construction que précédemment (`d_model=16`,
`d_ff=32`, `T=5`, 60 initialisations pour cartographier les bassins,
8 premiers bassins distincts retenus par paysage).

**Test A — superposition maintenue sous évolution unitaire pure
(`K_ana=0`), calcul exact, pas de Monte-Carlo** (l'évolution unitaire
est déterministe, une seule trajectoire par paysage suffit) :
- État initial localisé dans le bassin 0, évolution à `Δt=2,0` (dans le
  plateau observé précédemment).
- **Seuil de succès, fixé à l'avance** : `S(Δt=2,0) > 1,0` (la moitié
  de l'entropie maximale `ln(8)=2,079` — un seuil significatif et
  interprétable, pas ajusté après coup) sur les **3 paysages**.

**Test B — collapse sous mesure projective répétée, comparaison
statistique propre** :
- Deux valeurs de `K_ana` seulement, les extrêmes déjà explorés :
  `K_ana=0` et `K_ana=10`.
- **`M=1000` trajectoires** par paysage et par valeur de `K_ana` (contre
  200 dans l'exploration — resserre l'erreur-type d'un facteur
  `√5≈2,2`).
- Erreur-type calculée sur les entropies par trajectoire :
  `σ_S/√M` pour chaque `(paysage, K_ana)`.
- **Critère de succès, fixé à l'avance** : `z = (⟨S⟩_{K_ana=0} −
  ⟨S⟩_{K_ana=10}) / √(σ₀²/M + σ₁₀²/M) ≥ 5` (même standard 5σ que le
  reste du projet) — sur les **3 paysages**, pas seulement un.

**Décision de citation** : si les deux tests réussissent sur les 3
paysages, le résultat (superposition simultanée maintenue en régime
unitaire, collapse statistiquement significatif sous mesure répétée)
pourra être proposé pour `Simulations_API.md`. Un échec sur un seul
paysage suffit à invalider une citation en l'état — pas de moyenne qui
masquerait une hétérogénéité.

#### Résultat du protocole confirmatoire — les deux tests réussissent (2026-09-20)

**`scripts/run_n_basin_confirmatory.py`, résultat archivé dans
`docs/results/n_basin_confirmatory_2026-09-20.json`, 3 paysages frais
(seeds `301, 302, 303`) :**

```
seed=301 : Test A S=1,9376 (seuil>1,0) OUI  | Test B <S>₀=1,9376±0 <S>₁₀=1,3751±0,019  z=29,64 OUI
seed=302 : Test A S=1,7167 (seuil>1,0) OUI  | Test B <S>₀=1,7167±0 <S>₁₀=1,4507±0,014  z=19,69 OUI
seed=303 : Test A S=1,9581 (seuil>1,0) OUI  | Test B <S>₀=1,9581±0 <S>₁₀=1,2482±0,020  z=35,90 OUI
```

**Test A et Test B réussissent sur les 3 paysages**, avec une marge
large (`z` entre `19,7` et `35,9`, très au-delà du seuil `5σ`
pré-enregistré). `<S>(K_ana=0)` a une erreur-type nulle par construction
(aucun événement de mesure ne se produit jamais à `K_ana=0` —
déterministe, chaque trajectoire donne exactement le même résultat, pas
une coïncidence).

**Ce que ce résultat établit précisément** : sur ce modèle (8 bassins
réels d'un paysage tying complet, régime unitaire cohérent vs mesure
projective répétée), (1) l'évolution unitaire pure maintient une
authentique superposition à plusieurs bassins (entropie `>1,7` sur un
maximum de `2,079`, jamais un collapse spontané), et (2) l'introduction
d'un canal de mesure/projection répétée à taux `K_ana` fait décroître
cette superposition de façon statistiquement non ambiguë. Les deux
tenant ensemble, indépendamment de 3 tirages de paysage différents.

**Décision (Producteur) : condition de citation remplie.** Protocole
pré-enregistré avant le run, seeds fraîches, seuils fixés à l'avance,
résultat sans ajustement a posteriori — même standard que le protocole
confirmatoire Leggett-Garg déjà cité. **Reste à valider avec Bertrand
avant le commit de citation dans `Simulations_API.md`** (formulation
exacte de l'entrée, `contract_version` à bumper).

### Recherche — Fermer la boucle : K_ana endogène (2026-09-20)

**Correction d'une inversion sémantique.** La synthèse transmise pour
second avis proposait « `K_ana` bas si cohérence forte, haut si
dispersion ». C'est l'inverse de la phénoménologie correcte — retour
confirmé : forcer `K_ana` haut pendant une exploration encore dispersée
provoquerait un effondrement prématuré et arbitraire (« un préjugé
violent »), pas une décision légitime. **`K_ana` doit croître quand un
attracteur émerge par interférence constructive (cristallisation), rester
bas pendant une authentique dispersion.** Origine de l'erreur : la
formule `K_cible(Φ)` du document `implications_théorème_Stone`
(sigmoïde) donne littéralement `K_ana→K_min` quand `Φ` est haut — en
contradiction avec le texte qui l'accompagne dans le même document
(« Phase de cristallisation... `K_ana` augmente »). Incohérence interne
présente dès la source, reproduite sans le remarquer. Corrigée pour la
suite.

**Second point relevé, indépendant** : `Tr(ρ²)` (pureté) est **toujours
égal à 1** sur une trajectoire pure individuelle (`|ψ(t)⟩` reste pur
sous évolution unitaire + collapse de Born) — elle ne prend un sens que
moyennée sur de nombreuses trajectoires (reconstitue `ρ`). Un
régulateur qui agit **par trajectoire** (comme le nôtre) ne peut donc
pas utiliser la pureté comme signal ; l'entropie de participation
`S_part(ψ)`, elle, reste calculable sur un état pur, mais reste une
opération globale sur toute la base `{e_k}` — pas strictement locale.

**Mécanisme proposé, plus naturel : taux de saut asservi au
chevauchement maximal.** Sur la trajectoire courante, `p_max(t) =
max_k|⟨e_k|ψ(t)⟩|²` — tant qu'aucun bassin ne domine (`p_max≈1/8`), le
taux de mesure reste quasi nul (exploration libre sous le régime
unitaire) ; dès qu'un bassin franchit un seuil critique, le taux de
mesure augmente spontanément et déclenche l'effondrement — pas de dé
lancé de l'extérieur à taux constant, le taux **dépend de l'état de la
trajectoire elle-même** :

```
λ_saut(t) = K₀ · (p_max(t))^γ     (γ ≥ 2)
```

**Piste retenue pour l'implémentation immédiate (« Phase 1 » de la
proposition)** : remplacer le taux de Poisson constant `K_ana` du
protocole confirmatoire par `λ_saut(t)` ci-dessus — teste si le
mécanisme d'auto-sélection émerge effectivement sous la dynamique
unitaire déjà caractérisée (le réseau déclenche-t-il lui-même son
propre effondrement dès qu'un attracteur émerge, sans qu'on lui impose
de taux constant ?).

**Piste notée pour plus tard, plus profonde, non implémentée** : rendre
la non-linéarité elle-même conservative (terme de rétroaction
hamiltonienne à la Gross-Pitaevskii/Kerr, `H_eff(ψ)=H₀-χΣ_k|e_k⟩⟨e_k||
⟨e_k|ψ⟩|²⟨e_k|`) — l'effondrement émergerait d'une bifurcation
dynamique dans une évolution toujours unitaire, sans opérateur de
mesure externe à invoquer du tout. Piste physiquement la plus profonde,
pas encore explorée.

#### Résultat de la « Phase 1 » — auto-sélection confirmée, mais métrique à raffiner (2026-09-20)

**`scripts/run_n_basin_endogenous_kana.py`, résultat archivé dans
`docs/results/n_basin_endogenous_kana_2026-09-20.json`** : `λ_saut(t) =
K0·p_max(t)²`, fenêtre longue (`Δt_total=20`, `200` sous-pas), `20`
trajectoires par `K0` :

```
K0     <S_final>   % trajectoires effondrées   <pas du 1er saut>/200
 0,0      1,69              0%                    —
 1,0      1,68            100%                  67,7
10,0      1,61            100%                   6,7
50,0      1,70            100%                   0,6
```

**Le mécanisme déclenche bien son propre effondrement** : 100% des
trajectoires connaissent au moins un saut dès `K0>0`, de plus en plus
tôt quand `K0` croît — confirmation directe que le taux de mesure
asservi à `p_max(t)` produit l'auto-sélection recherchée, sans taux
imposé de l'extérieur.

**Mais l'entropie finale ne baisse pas** (reste `~1,6-1,7`, quel que
soit `K0`) — **pas un échec du mécanisme, un défaut de la métrique**.
Après un saut, l'état effondré continue d'évoluer **unitairement**
jusqu'à la fin de la fenêtre longue ; on a déjà établi (section
précédente) qu'un état localisé remonte vers le plateau de superposition
en quelques unités de `Δt` sous évolution unitaire pure. Le système ne
« décide » pas une fois pour toutes : il s'effondre puis se re-disperse
sous `Y` — le cycle cristallisation→relâchement→ré-intrication déjà
décrit par ailleurs (contribution Gémini, analogie méditative).
**Confirmation numérique non planifiée de ce cadre cyclique**, mais qui
signale que la mesure retenue (entropie en fin de fenêtre longue) ne
teste pas la bonne question — il faudrait suivre l'entropie **juste
après** le premier saut, pas au bout d'une longue fenêtre unitaire
ultérieure.

**Reste à faire** : raffiner la métrique (entropie immédiatement après
le premier événement de collapse, pas en fin de fenêtre) avant de tirer
une conclusion quantitative sur l'effet de `K0`/`γ` ; explorer si la
« respiration » observée (durée du régime effondré avant re-dispersion)
dépend elle-même de `K0` — question distincte, potentiellement plus
intéressante que l'entropie finale.

#### Distinction cristallisation spontanée vs sélection forcée (2026-09-20)

**Remarque de Bertrand, décisive** : un attracteur peut émerger
**spontanément** sous l'effet de `Y` seul (sans aucune mesure) — mais si
aucun « choix » ne se dessine naturellement, augmenter `K_ana` force
quand même le système à sélectionner un bassin, arbitrairement. Ce sont
deux régimes différents, à ne pas confondre dans une seule courbe.

**Vérifié directement.** Sous `Y` seul (`K0=0`, même trajectoire, pas de
mesure) : `p_max(t)` (le poids du bassin dominant à cet instant) varie
naturellement entre `0,179` et `0,838` (moyenne `0,420`) — bien au-dessus
du niveau dispersé (`1/8=0,125`). **La cristallisation spontanée sous
`Y` seul est confirmée** : l'interférence constructive fait émerger de
vrais vainqueurs temporaires, sans qu'aucune mesure n'intervienne.

**Mais avec `λ_saut(t)=K0·p_max(t)^γ` et `γ=2` (valeur initiale), le
saut se produit systématiquement autour de `p_max≈0,46-0,53`** — proche
de la *moyenne* de fluctuation, pas des pics extrêmes — **quel que soit
`K0`** (testé de `0,1` à `50`). Diagnostic : `K0` ne fait que
ré-échelonner le temps du processus de Poisson, il ne change jamais le
niveau de `p_max` préférentiellement sélectionné — c'est l'exposant `γ`
qui contrôle cette sélectivité (le rapport de probabilité de saut entre
deux niveaux de `p_max` est `(p_a/p_b)^γ`, indépendant de `K0`).

**Confirmé par balayage de `γ`** (`K0∈{0,1;1;10}`, `γ∈{2;6;12;20}`) :

```
gamma   K0      % effondrées   <p_max au saut>
  2.0    1.00      100%            0.531
  6.0    1.00       30%            0.673
 12.0    1.00       10%            0.834
 20.0   10.00        5%            0.838
```

`p_max` au moment du saut monte de `0,53` (`γ=2`) à `0,83` (`γ≥12`) —
se rapprochant du pic naturel maximal observé sous `Y` seul (`0,838`).
**`γ` contrôle la sélectivité** (le système attend un vainqueur net
avant de trancher) ; **`K0` contrôle seulement l'urgence** (la vitesse à
laquelle, un niveau de dominance donné étant atteint, la décision se
prend) — deux rôles bien distincts, pas un seul cadran. À `γ` élevé et
`K0` modéré, le mécanisme approche la « cristallisation spontanée
guidée » que Bertrand décrit : le réseau attend un vrai vainqueur avant
de laisser `K_ana` agir, plutôt que de forcer un choix sur une
dominance à peine supérieure à la moyenne.

#### Protocole confirmatoire — cristallisation spontanée et sélectivité de γ (pré-enregistré, 2026-09-20)

**Écrit avant tout nouveau run.** Deux affirmations distinctes,
chacune avec un critère fixé à l'avance — la leçon des protocoles
précédents de ce fil.

**Échantillon** : 3 paysages **fraîchement tirés** (seeds `401, 402,
403` — namespace disjoint de tout ce qui a déjà été utilisé), même
construction que précédemment (8 bassins par paysage).

**Test E — la cristallisation spontanée sous `Y` seul généralise**
(calcul exact, déterministe, pas de Monte-Carlo) :
- `K0=0`, `Δt_total=20`, `200` sous-pas, état initial localisé dans le
  bassin 0.
- **Seuil de succès, fixé à l'avance** : `max_t p_max(t) > 0,5` sur les
  **3 paysages** (bien au-dessus du niveau dispersé `1/8=0,125` —
  seuil significatif, pas ajusté après coup).

**Test C — `γ` contrôle la sélectivité, `K0` non** :
- Deux valeurs de `γ` seulement, les extrêmes déjà explorés :
  `γ=2` et `γ=20`, à `K0=10` fixe (choisi pour garantir suffisamment
  d'événements de collapse même à `γ=20`, où le taux de collapse est
  faible).
- **`M=500` trajectoires** par paysage et par valeur de `γ` (contre 20
  dans l'exploration).
- Métrique : `p_max` au moment du premier saut, moyenné sur les
  trajectoires ayant effectivement collapsé, avec erreur-type.
- **Garde-fou de puissance, fixé à l'avance** : si moins de 20
  trajectoires collapsent dans une condition, le test est déclaré
  **non concluant** pour ce paysage plutôt que de forcer une lecture
  sur un échantillon trop petit — pas un ajustement a posteriori, une
  règle décidée avant de voir les résultats.
- **Critère de succès, fixé à l'avance** : `z = (⟨p_max⟩_{γ=20} −
  ⟨p_max⟩_{γ=2}) / √(σ₂₀²/M₂₀ + σ₂²/M₂) ≥ 5` (même standard 5σ que le
  reste du projet), sur les **3 paysages**.

**Décision de citation** : si Test E et Test C réussissent tous les
deux sur les 3 paysages (et qu'aucun n'est déclaré non concluant par le
garde-fou de puissance), le résultat (cristallisation spontanée
généralisée + `γ` comme paramètre de sélectivité, indépendant de
l'urgence contrôlée par `K0`) pourra être proposé pour
`Simulations_API.md`.

#### Résultat du protocole confirmatoire — les deux tests réussissent (2026-09-20)

**`scripts/run_n_basin_gamma_confirmatory.py`, résultat archivé dans
`docs/results/n_basin_gamma_confirmatory_2026-09-20.json`, 3 paysages
frais (seeds `401, 402, 403`) :**

```
seed=401 : Test E max_p_max=0,9151 OUI | Test C <p_max>(γ=2)=0,484±0,008 (n=500) <p_max>(γ=20)=0,883±0,008 (n=82)  z=35,27 OUI
seed=402 : Test E max_p_max=0,8287 OUI | Test C <p_max>(γ=2)=0,471±0,007 (n=500) <p_max>(γ=20)=0,788±0,009 (n=27)  z=27,49 OUI
seed=403 : Test E max_p_max=0,8946 OUI | Test C <p_max>(γ=2)=0,601±0,004 (n=500) <p_max>(γ=20)=0,841±0,003 (n=268) z=47,04 OUI
```

**Test E et Test C réussissent sur les 3 paysages**, avec une marge
très large (`z` entre `27,5` et `47,0`, largement au-dessus du seuil
`5σ`). Le garde-fou de puissance tient (`n≥27` collapses partout, au-
dessus du minimum `20` fixé à l'avance — le paysage `402` est le plus
proche de la limite, mais reste valide selon la règle pré-enregistrée).

**Décision (Producteur) : condition de citation remplie.** Protocole
pré-enregistré avant le run, seeds fraîches, seuils et garde-fou de
puissance fixés à l'avance. **Reste à valider avec Bertrand avant le
commit de citation dans `Simulations_API.md`** — probablement à fondre
avec l'entrée déjà proposée sur la superposition/collapse (même
famille de résultats, mécanisme affiné).

### Recherche — Vers un signal de collapse réellement interne (2026-09-20)

**Origine** : remarque de Bertrand — `p_max(t)` (recouvrement avec les 8
concepts nommés) demande une information de type « vue de l'extérieur »
(la liste des concepts, construite par nous, pas calculable depuis
l'intérieur du réseau sans qu'on la lui fournisse). Objection identique,
généralisée, à celle déjà soulevée par Gémini sur `Tr(ρ²)`. Il faut un
signal fondé uniquement sur `ψ` et `W`, tous deux déjà internes au
réseau.

**Faux départ — `ΔE²(ψ)=⟨ψ|W²|ψ⟩−⟨ψ|W|ψ⟩²` (le « capteur B » de la
contribution Gémini d'origine).** Résout bien le problème d'étiquetage
externe (ne dépend que de `ψ` et `W`), mais **structurellement
inutilisable** : `⟨W⟩` et `⟨W²⟩` sont des quantités **conservées
exactement** sous une évolution unitaire générée par `W` lui-même
(`W` commute avec `exp(-iWt)`, donc avec `W²`) — `ΔE²(ψ(t))` est figé
dès l'état initial, incapable par construction de détecter une
résonance qui émerge dans le temps. Vérifié : sous `Y` seul, `ΔE²(t)`
varie de `6606` à `6623` (`0,25%` de fluctuation relative, du bruit
numérique de `matrix_exp`, pas un signal).

**Signal retenu — entropie de participation sur la base de coordonnées
brutes du réseau** (les `80` dimensions natives — littéralement ses
propres unités, pas une liste de concepts fournie de l'extérieur).
`c(t) = 1 − S_brut(t)/S_max` (`0`=dispersé, `1`=localisé). Cette base ne
commute pas avec `W` en général, donc `c(t)` **évolue réellement** :
vérifié sous `Y` seul, `c(t)` varie de `0,0708` à `0,1451` — une
fluctuation de plusieurs points de pourcentage, pas du bruit numérique.

**Revalidation de la cristallisation/sélectivité** (`scripts/explore_raw_participation_crystallization.py`,
même paysage `seed=14`, `λ_saut(t)=K0·c_norm(t)^γ`, `c_norm` normalisé
sur sa plage propre observée sous `Y` seul — nécessaire car la plage
naturelle de `c(t)` est bien plus étroite que celle de `p_max(t)`,
`K0` calibré pour l'ancien signal ne transposait pas directement) :

```
gamma   % effondrées   <pas du 1er saut>   <c au saut>
  1.0        100%              2.8              0.1011
  3.0        100%             11.6              0.1142
  6.0        100%             20.5              0.1304
 12.0        100%             73.6              0.1365
```

**Même comportement qualitatif que `p_max`, cette fois sur un signal
authentiquement interne** : `c` au moment du saut monte de `0,101` à
`0,137` quand `γ` croît, se rapprochant du maximum naturel (`0,145`).
`γ` contrôle toujours la sélectivité, `K0` (une fois recalibré à
l'échelle du nouveau signal) toujours l'urgence.

**Statut : exploratoire.** Le protocole confirmatoire déjà validé pour
`p_max` (Test C/E) reste à refaire avec ce signal avant toute citation
— pas fait à ce stade. Reste ouvert : est-ce que cette entropie « sur
les neurones bruts » correspond à quelque chose de psychologiquement
interprétable (un ressenti), ou est-ce un simple proxy technique — non
tranché, à discuter séparément.

## Historique des phases complétées

<!-- Déplacer ici les phases terminées avec date de complétion -->
