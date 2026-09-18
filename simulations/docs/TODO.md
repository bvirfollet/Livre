# TODO — simulations

> Backlog actif uniquement. Les items résolus sont archivés en bas de page
> (section Historique). Mettre à jour après chaque commit de feature ou
> correctif.

---

## Priorité haute

- [x] Mettre en place l'environnement Python (venv, dépendances figées) — Phase 0 (`.venv`, torch 2.13, pytest 9.1.1)
- [ ] Phase 3 : harnais d'évaluation GLUE (dépend de trancher le point
  d'architecture ci-dessous en priorité normale)

## Priorité normale

- [ ] **Superposition Leggett-Garg — pistes restantes** (protocole
  confirmatoire fait et cité, cf. Historique) : cas `Wᵢᵢ≠0` (self-couplage,
  hors modèle Hopfield standard) pour discriminer non-classicité locale vs
  relationnelle ; étendre le protocole confirmatoire à `Q_i` agrégé (fait
  uniquement sur `Q_global` cette fois) et/ou à d'autres `nN` si jugé utile.
- [ ] **Conception non prévue (échelle native)** : `SW_Design.md` ne
  couvre que `ComplexLinear`, `HermitianSelfAttention`, l'équivalence
  Hopfield et `WeightProjector` — rien n'est encore conçu pour le FFN
  complexe, les `LayerNorm` complexes, les embeddings, ni l'empilement
  multi-couches d'un `HermitianBertModel` complet, **à l'échelle native
  `d_model`** (portage direct de poids, pipeline Phase 3/4/5). Repéré le
  2026-08-14 en scopant le test I-01 : décidé avec Bertrand de limiter
  I-01 au bloc d'attention seul pour l'instant — la question de
  l'architecture complète reste ouverte et devra être tranchée avant toute
  comparaison GLUE bout-en-bout (Phase 3).

  **Correction du 2026-09-18 (avant tout codage) :** la piste FFN notée
  précédemment ici — résonance directe `H' = φ(W₂(W₁HW₁†)W₂†)`, issue de
  `contributions/gémini/Evolution_BERT_suite` — **ne s'applique pas à
  notre architecture**. Cette formule suppose que chaque token soit
  représenté par une **matrice** hermitienne `H` (le nœud « 32×32 » de
  Gémini, l'architecture à compression qu'on a explicitement écartée du
  pipeline natif, cf. section « Recherche — Compression hermitienne »
  ci-dessous). Notre `HermitianSelfAttention` représente chaque token par
  un **vecteur** `z ∈ C^{d_model}` — `W₁HW₁†` n'a pas de sens pour un
  vecteur. Même problème pour la normalisation de trace (`N(H)=H/Tr(H)+ε`),
  également définie pour une matrice.

  **FFN natif retenu (validé avec Bertrand, 2026-09-18)** — proposition
  cohérente avec l'architecture vectorielle et avec le principe déjà
  établi ailleurs dans le projet (la phase porte le déphasage, ne pas la
  triturer arbitrairement — cf. softmax sur `Re(S)` seul dans
  `HermitianSelfAttention`) :
  ```
  FFN(z) = ComplexLinear₂( g(ComplexLinear₁(z)) )
  g(z) = GELU(|z|) · z/|z|     # gate réel sur le module, phase préservée exactement
  ```
  Analogue direct du "modReLU" de la littérature sur les réseaux de
  neurones complexes (Arjovsky et al. 2016, Trabelsi et al. 2018) — pas
  une construction inventée pour l'occasion. L'alternative naïve (GELU
  séparé sur Re et Im) tournerait la phase de façon incontrôlée à chaque
  couche, ce qui contredirait le principe déjà établi. **Implémenté et
  testé (2026-09-18)** : `src/hermitian/gating.py`, `src/hermitian/ffn.py`,
  `tests/test_hermitian_ffn_norm.py` — préservation de phase vérifiée à la
  main (cas N=2) et sur cas aléatoires.

  **`LayerNorm` natif : deux variantes gardées en parallèle (2026-09-18)**
  — `HermitianRMSNorm` (préserve la phase, pas de portage exact possible)
  et `HermitianLayerNorm` (centrage complet, portage-compatible, ne
  préserve pas la phase). Question de Bertrand sur le rôle du centrage
  pour la discrimination tranchée empiriquement
  (`scripts/compare_normalizations.py`) : le centrage n'est pas une perte
  générale de discernement, il annule spécifiquement la sensibilité à un
  décalage uniforme partagé par toutes les dimensions, sans affecter la
  discrimination sur les autres directions (cf. `docs/SW_Design.md` pour
  la table de résultats). Reste non tranché : effet réel du centrage sur
  l'attention avec poids pré-entraînés (biais partagé gonflant `Q·K`) —
  hypothèse plausible, pas encore testée. `src/hermitian/norm.py`, testé
  (préservation/non-préservation de phase, portage exact à `Im=0`, cas
  N=2, invariant de discrimination).

  **Reste à faire pour clore ce point d'architecture** : empilement
  multi-couches (`HermitianBertLayer`/`HermitianBertModel` — choisir entre
  RMSNorm et LayerNorm, ou garder les deux comme option), embeddings
  (même schéma que `WeightProjector` — Re=table HF, Im=bruit —, pas de
  nouvelle conception requise), extension du test I-01 à la couche
  complète puis au modèle empilé.
- [ ] **Recherche séparée — compression hermitienne pour portage mobile**
  (cf. `docs/DevPlan.md`, section dédiée) : objectif et protocole posés
  avec Bertrand le 2026-08-14 (`d² ≪ 768`, comparaison à budget de réels
  égal contre un bottleneck réel non contraint). Point ouvert avant tout
  codage : arbitrer la ou les valeurs de `d` cible et la métrique de
  succès (fidélité de reconstruction / perplexité / score GLUE — ne pas
  mélanger).

## Améliorations / Nice-to-have

- [ ] Évaluation spectrale parcimonieuse (dernière couche seulement) si le
  coût de `torch.linalg.eigh` devient un goulet d'étranglement mesuré

---

## Historique (items résolus)

- [x] Phase 1 — `ComplexLinear`, `HermitianSelfAttention`, module d'équivalence
  Hopfield 1-pas (`src/hermitian/`, `src/hopfield/`), tests U-01 à U-04 verts
  (`tests/`). 2026-08-14.
- [x] Spike weights — correspondance state_dict BERT ↔ `ComplexLinear`
  confirmée (`docs/spike-weights-state-dict-mapping.md`). 2026-08-14.
- [x] Phase 2 (bloc d'attention) — `WeightProjector`
  (`src/weights/projector.py`), test I-01 vert (`tests/test_weights.py`).
  Deux bugs Phase 1 corrigés au passage (BUG-001 fuite de biais, BUG-002
  softmax sur S symétrisé — cf. `docs/CorrectifPlan.md`).
  `requirements.txt` créé (torch, pytest, transformers + dépendances
  figées aux versions installées). 2026-08-14.
- [x] Superposition Leggett-Garg — P1 résolu, protocole complet fixé
  (`nN`, `nS=3`, `M=300`, seuils 5σ/Bonferroni), primitives
  (`src/superposition/`) et TU U-05 à U-07 verts
  (`tests/test_superposition.py`). Point de vigilance noté sur la dérive
  numérique de `matrix_exp` composé (`SW_Design.md`). 2026-09-13.
- [x] Superposition Leggett-Garg — harnais Monte-Carlo
  (`src/superposition/harness.py` : `two_time_correlation`,
  `leggett_garg_k3`, `aggregated_local_k3`, version exacte sans bruit),
  TI I-04 vert (`tests/test_superposition_harness.py`) — écart au plan
  initial noté (`K(3)=3/2` non reproduit exactement, régression bâtie sur
  deux faits plus modestes mais vérifiés, cf. `docs/test_plan.md`).
  2026-09-13.
- [x] Superposition Leggett-Garg — run I-05 complet, deux passes
  (`M=300` fixe : PARTIEL, 2/10 à 5σ ; `M` recalculé par `nN` via
  `required_m_for_significance` : 9/10 à 5σ), script CLI relançable
  (`scripts/run_superposition_i05.py`), résultats archivés
  (`docs/results/i05_run_2026-09-13.json`). Exploration multi-tirages sur
  `nN=3`/`nN=10` (50 tirages chacun, `run_multi_realization_exact`) :
  l'anomalie `nN=3` du premier tirage ne tenait pas (82 % de violation
  locale en moyenne, comparable à `nN=10`). Hypothèse « solides de Platon
  hermitiens » (référence `Hopfield_Géométrie_Sacrée_atome_Mémoire`)
  explorée et écartée (prémisse disparue + absence de pont mathématique
  avec la construction actuelle de `W`). 2026-09-13.
- [x] Superposition Leggett-Garg — **protocole confirmatoire
  pré-enregistré et lancé** (`run_confirmatory_binomial_test`,
  `scripts/run_superposition_confirmatory.py`, plafond `M≤200000` ajouté
  après un hang constaté sur des tirages à marge quasi nulle) : `nN=3`
  (17/30 succès, `p=7,13×10⁻¹⁰⁴`) et `nN=10` (24/30, `p=5,63×10⁻¹⁵²`), tous
  deux très en-dessous du seuil pré-enregistré. Résultat archivé
  (`docs/results/confirmatory_run_2026-09-18.json`) et **cité dans
  `docs/Simulations_API.md`** (`contract_version: 2026-09-18-v2`, entrée
  `[PENDING: RadioHumaine]` dans `Simulations_API_CHANGELOG.md`) — premier
  résultat citable de ce projet. 2026-09-18.

<!-- Format : - [x] YYYY-MM-DD — description (commit: abc1234) -->
