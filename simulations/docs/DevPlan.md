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

## Historique des phases complétées

<!-- Déplacer ici les phases terminées avec date de complétion -->
