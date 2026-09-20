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

- [ ] **Équivalence Hopfield non vérifiée pour la couche complète
  (FFN+Norm)** (soulevé par Bertrand, 2026-09-18) — **point important,
  priorité haute logique même si classé ici pour l'instant**. Le fil
  conducteur du projet est que BERT, malgré la complexité apparente de
  ses couches (LayerNorm, FFN...), se ramène in fine à un réseau de
  Hopfield (Ramsauer et al. 2020) — un Hopfield qu'on plonge ensuite dans
  l'espace hermitien. Ce qu'on a réellement démontré :
  - Phase 1 (`test_u03_equivalence_general_qkv`) : le **bloc d'attention
    seul** (`HermitianSelfAttention`) est exactement un pas de Hopfield
    (`hopfield_step`), pour `Q`, `K`, `V` quelconques.
  - 2026-09-18 : la **couche complète** (attention+FFN+2 Norm+résiduelles,
    `HermitianBertLayer`) reproduit BERT classique à `Im=0` — un test de
    *portage*, pas un test d'*équivalence Hopfield*.
  Ces deux résultats ne se recouvrent pas : `HermitianFFN` et
  `HermitianRMSNorm`/`HermitianLayerNorm` ont été conçus sur d'autres
  critères (préservation de phase, compatibilité de portage), **jamais
  vérifiés vis-à-vis du cadre Hopfield**. Rien ne garantit que la couche
  complète — résiduelle + norme + FFN autour du pas de Hopfield — reste
  elle-même interprétable comme une dynamique de Hopfield (simple ou
  généralisée) plutôt que comme un objet mathématique différent. Note :
  Ramsauer et al. 2020 établissent l'équivalence pour l'**attention
  seule**, pas pour un bloc transformeur complet avec FFN — donc il n'est
  même pas évident que la littérature de référence promette cette
  équivalence au niveau couche complète. À trancher avant de présenter le
  travail natif comme « un Hopfield hermitien », y compris pour la Phase 3
  (GLUE) et pour toute citation dans `Simulations_API.md` :
  1. **Fait (2026-09-18)** : le sous-bloc attention, *isolé* à l'intérieur
     de `HermitianBertLayer` assemblé et chargé avec de **vrais poids
     pré-entraînés** (bruit imaginaire non nul, régime complexe réel — pas
     seulement `Im=0`), reste exactement un pas de Hopfield —
     `tests/test_weights.py::test_layer_attention_subblock_still_hopfield_equivalent_after_assembly`,
     vert du premier coup. Ceci confirme que l'assemblage et le portage
     n'ont pas silencieusement altéré le sous-bloc attention lui-même.
  2. **Dérivation théorique faite (2026-09-20)** — cf. `docs/DevPlan.md`,
     section dédiée, pour le détail complet. Résumé : **deux sens
     distincts d'« équivalence Hopfield » ont été confondus jusqu'ici.**
     (a) Équivalence de *formule* (Phase 1, `test_u03_equivalence_general_qkv`)
     — vraie pour `Q,K,V` quelconques, quasi tautologique (l'attention et
     `hopfield_step` calculent littéralement la même expression). (b)
     Équivalence *dynamique/énergétique* (garantie de convergence vers un
     attracteur, la propriété physiquement significative) — prouvée par
     Ramsauer et al. 2020 **uniquement pour le cas auto-associatif**
     (`V=K`, vérifié sur la source : leur passage à l'attention `Q,K,V`
     séparés, éq. 10, est une observation formelle, pas une preuve
     d'énergie). Or **BERT réel apprend `W_K` et `W_V` indépendamment**
     (`V≠K` systématiquement) — donc le sens (b) n'a jamais été acquis,
     même pour le bloc d'attention seul avec de vrais poids. Le trou est
     plus profond qu'initialement repéré : il ne vient pas du FFN/de la
     norme, il existe déjà à la racine de l'attention hermitienne dès
     qu'on utilise des poids réels.

     Dérivation propre complémentaire (cas `V=K`) : `Attention(x)=X·softmax(βX^Tx)
     = ∇_x lse(β,X^Tx)` exactement. `x + Attention(x)` est donc un pas
     d'Euler de **montée** de gradient sur `lse` seul (non borné), et
     `RMSNorm` (qui force `‖sortie‖=γ√d` constant, cf.
     `test_rmsnorm_output_rms_is_gamma`) agit comme une **rétraction sur
     la sphère** — la technique standard de montée de gradient contrainte
     à une variété. `Attention+résiduelle+RMSNorm` correspond donc
     exactement à un pas de montée de gradient projetée sur `lse(β,K^Tx)`
     sur une sphère, **mais seulement si `V=K`**. `LayerNorm` (qui centre)
     projetterait sur une variété différente (sphère ∩ hyperplan
     orthogonal à `𝟙`), pas la sphère simple — **second argument
     théorique indépendant**, en plus de la préservation de phase, pour
     préférer `RMSNorm` dans ce cadre.

     **(i) FFN sans dérivation d'énergie — exploré le 2026-09-20**
     (Krotov, *Hierarchical Associative Memory*, arXiv:2107.06446,
     cf. `docs/DevPlan.md`) : le formalisme couvre bien toute fonction
     d'activation, mais confirme et généralise la même contrainte
     (`W₂=W₁ᵀ`) — ne résout pas le problème, en donne le vocabulaire
     exact. **Protocole de tying `V=K` implémenté et testé (2026-09-20,
     `docs/DevPlan.md`, section « Hopfield hermitien à poids liés »)** :
     décroissance d'énergie confirmée sans exception à `K` strictement
     fixe (étape 1), mais **rupture nette dès la moindre perturbation de
     `K`** (étape 2 — fraction de pas monotones chute de 100% à ~60% dès
     `σ=0,01`, aucune dégradation progressive) et **aucune monotonie
     locale une fois `K` recalculé à chaque pas** (étape 3, exploratoire —
     seulement 2/20 graines strictement monotones, malgré une tendance
     globale décroissante sur 20/20). Conséquence directe : une
     régularisation souple (rapprocher `V` de `K` sans les égaler) n'offre
     vraisemblablement **aucune** garantie d'énergie, même approximative
     — seul un tying strict serait porteur de la propriété, et encore
     uniquement dans le cas `K` fixe (jamais vérifié pour l'empilement
     réel). Tying FFN (`W₂=W₁ᵀ`) toujours hors scope (Lagrangienne du
     gate `g(z)=z·Φ(Re(z))` non dérivée).
     (ii) même en `V=K`, vérifier si `Q≠K` (qui, lui, ne casse pas l'égalité
     formule=Hopfield-step déjà prouvée) affecte la dérivation d'énergie
     ci-dessus — toujours ouvert, non traité par le protocole ci-dessus
     (qui pose `Q=ξ` par construction). (iii) conséquence pour le
     portage : BERT pré-entraîné a `V≠K` par construction, donc porter
     ses poids garantit la formule mais jamais la dynamique d'attracteur
     — renforcé par les résultats ci-dessus (même une proximité
     approximative ne suffirait pas) — à formuler explicitement avant
     toute affirmation Strate 1 sur ce point dans le manuscrit.
- [ ] **Piste Chladni-Hopfield sur BERT hermitien** (discussion du
  2026-09-18, cf. `contributions/claude/annexe_chladni_hopfield_v3.md`
  et `contributions/claude/Revue_Claude_Analogie_Fig_Chaldni`) : hypothèse
  de Bertrand — l'ajout d'une partie complexe à un réseau de Hopfield
  produit génériquement des transitions topologiques de type Chladni
  (croisements/dégénérescences de valeurs propres), et le même phénomène
  devrait apparaître dans le paysage d'attention du BERT hermitien
  (dynamique des figures probablement différente, physique sous-jacente
  la même). Plausible mathématiquement (généralisable en principe à toute
  famille paramétrée de formes quadratiques avec dégénérescence), mais
  **non testé empiriquement sur l'architecture réelle de `simulations/`**
  — le script `chladni_hopfield_anim_v2.py` porte sur un Hopfield-jouet
  `N=4` à matrice complexe *symétrique* (pas hermitienne), pas sur
  `HermitianSelfAttention`. Reste à formuler un protocole de test (quel
  paramètre jouer le rôle de `λ`/`α` dans l'attention hermitienne ? quelle
  observable jouerait le rôle des lignes nodales ?) avant de pouvoir
  trancher. Non prioritaire, à reprendre plus tard.

- [ ] **Superposition Leggett-Garg — pistes restantes** (protocole
  confirmatoire fait et cité, cf. Historique) : cas `Wᵢᵢ≠0` (self-couplage,
  hors modèle Hopfield standard) pour discriminer non-classicité locale vs
  relationnelle ; étendre le protocole confirmatoire à `Q_i` agrégé (fait
  uniquement sur `Q_global` cette fois) et/ou à d'autres `nN` si jugé utile.
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

- [x] **Architecture native (échelle `d_model`) — portage complet BERT↔Hermitien**
  (2026-09-18) : `HermitianFFN`/`gating.py` (gate `g(z)=z·Φ(Re(z))`,
  corrigé en BUG-003 — la première version sur `|z|` ne se réduisait pas
  à `GELU` réel), `HermitianRMSNorm`/`HermitianLayerNorm` (deux variantes,
  `RMSNorm` par défaut — préservation de phase —, `LayerNorm` réservée à
  la vérification de portage), `HermitianBertLayer`/`HermitianBertModel`
  (empilement Post-LN), `HermitianEmbeddings`. `WeightProjector` étendu à
  l'ensemble (`project_bert_ffn/_layer_norm/_layer/_model/_embeddings`).
  I-01 étendu vert à toutes les échelles (couche, empilement, modèle
  complet embeddings+encodeur) — `Im=0` reproduit `BertModel` HuggingFace
  exactement, du premier coup à chaque niveau. **Réserve importante
  soulevée par Bertrand (2026-09-18), non résolue** : voir le nouveau
  point ouvert ci-dessus sur l'équivalence Hopfield de la couche complète
  (FFN+Norm non vérifiés vis-à-vis du cadre Hopfield, seule l'attention
  seule l'a été en Phase 1).
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
