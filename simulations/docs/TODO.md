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
- [ ] **Régime `K_ana` faible — transfert unitaire entre bassins, défaut
  de construction identifié (2026-09-20)** (cf. `docs/DevPlan.md` pour
  le détail complet). Run exploratoire puis protocole confirmatoire
  pré-enregistré (`scripts/run_basin_tunneling_unitary.py`,
  `run_basin_tunneling_confirmatory.py`, réutilisation de
  `src/superposition/`, pas de calcul WKB — abandonné après correction
  du glissement `ħ_eff`→`Y`, cf. contribution Gémini
  `implications_théorème_Stone`). **Résultat : `P_B_max=1` exactement
  pour 80/80 paires testées, y compris à recouvrement quasi nul — fait
  mathématique exact (double puits symétrique, nos états de bassin ont
  tous la même norme via `RMSNorm`), pas une confirmation.** La
  construction hebbienne à poids égaux (`build_two_pattern_weights`)
  efface l'écart d'énergie classique réel entre bassins ; corrélation
  gap classique / période de Rabi mesurée : `r=-0,058` (nulle) contre
  `r=-0,688` pour recouvrement/période — la vitesse de transfert ne
  dépend que de la géométrie des vecteurs, pas de la barrière classique.
  **Aucune citation possible en l'état** (le run exploratoire précédent
  non plus).

  **Piste 2 (tight-binding) explorée (2026-09-20), mise en pause,
  inconclusive.** `scripts/run_basin_tight_binding.py` : chemin
  interpolé + renormalisé, énergie réelle `E(x_n)` sur chaque site —
  corrige bien le défaut ci-dessus (le vrai relief entre à présent dans
  le calcul, états localisés retrouvés en régime de faible couplage).
  Premier test (3 paires, `N` fixe) : relation barrière/séparation
  inversée par rapport à l'intuition WKB — confondant identifié (`N`
  fixe alors que la distance réelle entre bassins varie). Corrigé (`N`
  proportionnel à la distance, pas physique constant) et réétendu à 53
  paires/3 paysages : l'inversion nette disparaît, mais **aucune
  corrélation nette du signe attendu n'émerge** (`r≈+0,29`, faible,
  toujours du mauvais signe). **Fil mis en pause** — ni confirmé ni
  infirmé, poursuivre demanderait de contrôler des facteurs
  supplémentaires (forme du profil, hétérogénéité inter-paysages)
  non isolés à ce stade.

  Piste indépendante toujours ouverte : tester un `K_ana` intermédiaire
  (canal dissipatif GKSL explicite), pas seulement les deux extrêmes
  déjà testés séparément.

- [ ] **Recadrage (2026-09-20) — superposition simultanée + intrication
  réseau/entrée** (cf. `docs/DevPlan.md`, remplace le fil « tunnel »
  ci-dessus, jugé conceptuellement mal posé — le tunnel décrit un
  système déjà localisé qui s'échappe, pas la coexistence cohérente de
  plusieurs bassins avant effondrement). Renvoie à l'Objectif 2 du plan
  d'origine (`contributions/claude/plan_dev_simulation_superposition_intrication.md`,
  jamais commencé), reformulé : le second système couplé est le
  vecteur d'entrée, pas un second réseau.
  **Premier test fait, exploratoire** : `N=8` bassins réels (paysage
  seed=14, croisable avec le fil précédent), `build_n_pattern_weights`
  (généralisation à N motifs, testée), entropie de participation sur
  les 8 bassins plutôt que `K(nS)` (binaire, ne généralise pas à N=8
  sans variante ad hoc). Résultat : sous évolution unitaire pure,
  l'entropie monte au-delà du recouvrement géométrique de fond et se
  stabilise sur un plateau élevé (`N_eff≈5,5-6/8`), sans jamais
  redescendre — signature directe de superposition simultanée, pas de
  bascule entre deux bassins. Pas encore pré-enregistré/confirmatoire.
  **Contraste dissipatif fait (2026-09-20)** : deux faux départs
  (déphasage aléatoire sans collapse, base brute puis base de concepts
  — biais de Jensen identifié, l'entropie de la moyenne d'ensemble
  n'est pas la moyenne des entropies), puis correctif (vrai collapse
  projectif répété, règle de Born, effet Zénon, entropie moyennée par
  trajectoire) — tendance nette à la baisse avec `K_ana` (`1,72→1,33`,
  **pas strictement monotone sur la grille exploratoire**, correction
  actée après relecture de Bertrand).

  **Protocole confirmatoire réussi (2026-09-20)**
  (`scripts/run_n_basin_confirmatory.py`, résultat archivé dans
  `docs/results/n_basin_confirmatory_2026-09-20.json`) : 3 paysages
  frais (seeds `301,302,303`), Test A (superposition maintenue, seuil
  `S>1,0`) et Test B (collapse `K_ana=0` vs `10`, `M=1000` trajectoires,
  seuil `z≥5σ`) **réussissent sur les 3 paysages**, marge large
  (`z` entre `19,7` et `35,9`). **Condition de citation remplie** —
  reste à valider la formulation exacte avec Bertrand avant de commit
  dans `Simulations_API.md`.

  **K_ana endogène — Phase 1 testée (2026-09-20)** : second avis (via
  Gémini) a corrigé une inversion sémantique (K_ana doit croître avec
  la cristallisation, pas la dispersion — erreur tracée à une
  incohérence interne du document source) et proposé un mécanisme
  d'auto-sélection, `λ_saut(t)=K0·p_max(t)²` (taux asservi à l'état
  propre de la trajectoire, pas un taux externe constant). Testé
  (`scripts/run_n_basin_endogenous_kana.py`) : le mécanisme déclenche
  bien l'auto-effondrement (100% des trajectoires dès `K0>0`, de plus
  en plus vite avec `K0`), mais la métrique (entropie en fin de fenêtre
  longue) ne le montre pas — l'état effondré se re-disperse sous
  évolution unitaire après le saut (cycle cristallisation/relâchement,
  pas une décision permanente).

  **Distinction cristallisation spontanée / sélection forcée établie
  (2026-09-20)** : `γ` contrôle la sélectivité (le niveau de dominance
  requis avant de trancher), `K0` contrôle seulement l'urgence (la
  vitesse) — vérifié par balayage (`p_max` au saut monte de `0,53` à
  `0,83` quand `γ` passe de 2 à 20, indépendant de `K0`).

  **Protocole confirmatoire réussi (2026-09-20)**
  (`scripts/run_n_basin_gamma_confirmatory.py`, résultat archivé dans
  `docs/results/n_basin_gamma_confirmatory_2026-09-20.json`) : Test E
  (cristallisation spontanée généralisée, `max p_max>0,5`) et Test C
  (`γ` contrôle la sélectivité, comparaison `γ=2` vs `γ=20`, `z≥5σ`)
  **réussissent sur les 3 paysages frais** (seeds `401,402,403`), marge
  large (`z` entre `27,5` et `47,0`). **Condition de citation
  remplie** — reste à valider la formulation avec Bertrand.

  **Signal réellement interne trouvé (2026-09-20)** : `p_max`
  demandait une liste de concepts nommés (externe) ; `ΔE²(ψ)` proposé
  en remplacement s'est révélé structurellement figé (quantité
  conservée sous l'évolution qu'il générait lui-même — pas un signal).
  Retenu : entropie de participation sur les **coordonnées natives du
  réseau** (`c(t)=1-S_brut/S_max`, aucun étiquetage externe, évolue
  réellement sous `Y` seul). Cristallisation/sélectivité revalidées
  avec ce signal (`scripts/explore_raw_participation_crystallization.py`)
  — même comportement qualitatif que `p_max` (`γ` contrôle la
  sélectivité).

  **Protocole confirmatoire lancé, bug trouvé et corrigé (2026-09-20)**
  (`scripts/run_c_signal_confirmatory.py`, résultat archivé dans
  `docs/results/c_signal_confirmatory_2026-09-20.json`) : normalisation
  par `ln(80)` retirée (constante architecturale globale, irréaliste ;
  de toute façon annulée par la normalisation empirique en aval) —
  mais ce changement a révélé que le critère du Test E' n'était pas
  bien posé sous le nouveau signe (vacuoirement toujours vrai).
  Corrigé. **Résultat après correction : Test C' (sélectivité de `γ`)
  réussit toujours sur les 3 paysages (`z` entre `13,2` et `77,1`) ;
  Test E' (cristallisation) échoue net** (baisse d'entropie réelle
  `6,6-9,3%`, sous le seuil `20%` pré-enregistré). **Condition de
  citation NON remplie** pour ce signal — le mécanisme de
  cristallisation reste établi sur `p_max` (entrée déjà validée,
  inchangée), mais le signal purement interne le dilue trop pour le
  détecter au seuil fixé.

  **Signal Kuramoto `R(t)` trouvé, prometteur (2026-09-22)** (seconde
  contribution Gémini, cf. `docs/DevPlan.md`) : `R(ψ)=|Σψⱼ|/Σ|ψⱼ|`,
  zéro dépendance à `W`, invariant de jauge, corrige les deux défauts
  d'`S_brut` (dépendance de jauge, dilution spatiale). Exploratoire :
  plage naturelle large (`0,006-0,286`), sélectivité de `γ` reproduite
  nettement (`R` au saut : `0,146→0,248`). **Protocole confirmatoire pas
  encore fait.**

  **Limite de `R(t)` identifiée (2026-09-22)** : ne référence jamais
  `W` (les poids/la mémoire), seulement `ψ` — ne peut pas distinguer
  une cohérence incidente d'une vraie convergence vers un attracteur
  appris. Même limite pour la piste `ρ_liens` (Gram inter-tokens),
  jamais testée, qui ne référence que `X` (l'état), pas `W` non plus.

  **`a_rel(t)` testé (2026-09-22)** : `(1/Y)⟨ψ|i[W_ffn,W_att]|ψ⟩`,
  reconnecté à l'architecture réelle (`W_att` depuis `K` de l'attention
  liée, `W_ffn` depuis `W₁` du FFN lié) — utilise `W`, pas seulement
  `ψ`. Confirmé non trivial (`a_rel(t)` varie réellement,
  `‖[W_att,W_ffn]‖=104,5≠0`), mais **la sélectivité de `γ` ne se
  reproduit pas** (`|a_rel|` au saut reste `~1,4` quel que soit `γ`,
  pas monotone) — comportement qualitativement différent des signaux
  précédents, pas encore compris (hypothèse : oscillation trop rapide).
  Exploratoire, résultat mitigé, pas de protocole confirmatoire
  envisagé pour l'instant.

  **Reste à faire** : protocole confirmatoire pour `R(t)` ; tester
  l'entropie de liens ; raffiner la métrique d'entropie post-saut (le
  mécanisme de « respiration » — durée du régime effondré avant
  re-dispersion) ; volet plasticité interprétative (`W_imag`, `M=R+iI`,
  cf. `docs/DevPlan.md`, discussion du 2026-09-20 sur la reconsolidation
  mnésique) ; volet intrication réseau/entrée, pas commencé ; piste
  théorique de la transformée de Hilbert pour l'entrée (notée à part,
  `docs/DevPlan.md`).

- [ ] **Requalifier tous les signaux endogènes (`p_max`, `S_brut`, `R(t)`,
  `a_rel`) sur un réseau réellement entraîné** (posé par Bertrand,
  2026-09-22) : tous les tests de ce fil (superposition simultanée,
  collapse, sélectivité de `γ`) ont été faits sur des constructions
  **non entraînées** — `K`/`W₁` tirés au hasard indépendamment (jamais
  co-adaptés), motifs stockés par construction hebbienne plutôt
  qu'appris. Le comportement collectif « normalement attendu » d'un
  couplage attention/FFN (par exemple la nature et la vitesse de
  l'oscillation `a_rel`, cf. discussion du 2026-09-22 sur le manque
  d'apprentissage entre les deux couches) ne peut probablement pas être
  correctement capté sur un réseau jamais entraîné. Nécessite de
  reprendre ces mêmes signaux sur un réseau ayant véritablement appris
  (fine-tuning réel sur une tâche, ou au minimum un entraînement
  auto-supervisé même simple) avant de tirer des conclusions générales
  sur ces comportements collectifs. Dépend indirectement de la Phase 3
  (harnais GLUE), jamais commencée.

- [ ] **`K_ana` local par nœud — plasticité synaptique différenciée**
  (posé par Bertrand, 2026-09-25, traité à part du premier entraînement
  pour ne pas cumuler les inconnues) : au lieu d'un `K_ana` global,
  chaque nœud/dimension porterait sa propre capacité de plasticité
  apprise `κᵢ`, entrant dans la loi de saut comme facteur local
  (`λ_saut⁽ⁱ⁾(t)=K0·κᵢ·signal(t)^γ`) — l'analogue réseau de la
  plasticité synaptique différenciée en biologie. Cohérent avec la
  distinction phase d'entraînement (mode 1, tout s'apprend ensemble) vs
  exploitation (mode 2, dynamique `K_ana`) actée le 2026-09-22/25.
  Non commencé, à reprendre après un premier entraînement de base
  fonctionnel.

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
