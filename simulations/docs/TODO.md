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
- [ ] **Régime `K_ana` faible — tunnel quantique sur le paysage d'énergie**
  (posé par Bertrand, 2026-09-20, cf. `docs/DevPlan.md` pour l'explicatif
  complet) : sous-projet neuf, non démarré — distinct du régime `K_ana`
  fort (bruit classique, déjà quantifié). Nécessite (1) réduire le
  paysage à un profil 1D entre deux bassins voisins déjà identifiés,
  (2) définir une masse/`ħ_eff` effectifs (Strate 2/3, interprétatifs),
  (3) calculer l'amplitude WKB sur ce profil, (4) comparer au taux de
  Kramers classique déjà mesuré. Relié au fait que le BERT hermitien vise
  aussi à simuler des comportements quantiques (cf. le test de
  superposition Leggett-Garg déjà cité, régime unitaire cohérent
  distinct de celui étudié ici) — pont naturel entre les deux tracks,
  mais formalisme entièrement à construire. Q&R à faire avant tout code
  si priorisé.
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
- [x] **Équivalence Hopfield / tying `V=K` et `W₂=W₁†` — clos (2026-09-20)**,
  branche `dev/hopfield-energy-tying`, détail complet dans
  `docs/DevPlan.md`. Bilan final : deux sens d'« équivalence Hopfield »
  distingués (formule, inconditionnelle et quasi tautologique ; énergie,
  restreinte à `V=K`, jamais acquise pour BERT réel). Tying `V=K` et
  `W₂=W₁†` implémentés et testés (`src/hopfield/tied_dynamics.py`,
  `src/hermitian/tied_ffn.py`) — décroissance d'énergie confirmée à
  poids strictement fixes, mais rupture nette dès la moindre variabilité
  (aucune marge de tolérance), `Q≠K` casse la propriété indépendamment
  de `V≠K` (Jacobien non symétrique dès `W_Q≠I`), et l'empilement complet
  n'est pas automatiquement monotone par composition de deux composantes
  pourtant monotones séparément. Approfondissement : les violations
  observées sont un dépassement transitoire intra-bassin (dynamique non
  normale), pas un franchissement de barrière ; un même paysage produit
  bien une structure multi-bassins réelle (17 bassins/60 tirages, écarts
  0,5-3 unités), et un bruit d'entrée de 5-10% du signal suffit à
  produire un étalement du même ordre — confirme quantitativement le
  régime `K_ana` fort. Régime `K_ana` faible/tunnel explicitement hors
  de portée du système classique actuel, noté en piste séparée
  ci-dessus. Conséquence pour le manuscrit : toute affirmation Strate 1
  citant « Hopfield » pour BERT réel doit se limiter à l'équivalence de
  formule, jamais à la dynamique d'attracteur.

<!-- Format : - [x] YYYY-MM-DD — description (commit: abc1234) -->
