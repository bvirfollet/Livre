# Architecture logicielle — simulations

## Vue d'ensemble

```
[Modèle HuggingFace pré-entraîné]
  → [WeightProjector] (Re = poids HF, Im = bruit faible)
    → [HermitianSelfAttention / ComplexLinear] (BERT hermitien)
      → [Module d'équivalence Hopfield 1-pas] (validation croisée)
      → [Harnais d'évaluation GLUE] (comparaison vs BERT classique)
        → [Pont Perceval] (circuit photonique simulé)
          → [Pont QPU Quandela Cloud] (matériel réel)
```

## Composants principaux

### Décision d'architecture — représentation complexe (2026-08-14)

Contrairement au PoC Gémini source (`torch.complex64` matérialisé via
`torch.complex(real, imag)`), les modules ci-dessous manipulent des
**paires de tenseurs réels (`real`, `imag`)** de bout en bout, sans jamais
matérialiser de tenseur `complex64`. Raison : PyTorch ne définit pas de
dtype "complex-bf16" (seuls complex32/64/128, en composantes FP16/FP32/FP64,
sont supportés par `torch.complex()`) — matérialiser un tenseur complexe
figerait donc les composantes en FP16 ou FP32, ce qui contredirait
l'exigence de forward en BF16. En gardant réel/imag séparés, chaque
opération est un matmul réel ordinaire, nativement compatible avec
`torch.autocast(dtype=torch.bfloat16)`. Le passage à `torch.complex64` n'a
lieu qu'au point de sortie qui l'exige réellement : l'appel à
`torch.linalg.eigh` (avec cast FP32 local, cf. contrainte déjà actée).
Décision validée avec Bertrand le 2026-08-14.

### ComplexLinear

**Rôle :** couche linéaire complexe, décomposition explicite Re/Im
(`Y_r = X_r W_r − X_i W_i + B_r`, `Y_i = X_r W_i + X_i W_r + B_i`), deux
`nn.Linear` réels internes sans biais (`fc_real`, `fc_imag`) + deux
`nn.Parameter` de biais dédiés (`bias_real`, `bias_imag`).
**Fichier :** `src/hermitian/complex_linear.py`
**Interfaces :** `forward(x_real, x_imag) -> (y_real, y_imag)`.
**Correction du 2026-08-14 (BUG-001, `CorrectifPlan.md`) :** la première
version réutilisait le biais des deux `nn.Linear` internes dans les deux
équations de sortie, faisant fuiter `B_real` dans `Y_imag` (et
réciproquement) — indétectable par les tests Phase 1 (aucune référence
externe à biais non nul), détecté par le test I-01 de la Phase 2.

### HermitianSelfAttention

**Rôle :** attention `S = Q K† / √d_k`, softmax appliqué directement sur
`Re(S)` **brut** — pas sur le `H` symétrisé. `H = (S + S†)/2` (partie
réelle symétrisée + partie imaginaire antisymétrisée) est calculée et
retournée séparément, réservée à l'inspection/l'exploitation spectrale en
aval (ex. `eigh`) ; la partie imaginaire de `S` porte le déphasage.
**Fichier :** `src/hermitian/attention.py`
**Interfaces :** `forward(x_real, x_imag) -> (out_real, out_imag, (h_real, h_imag))`.
**Correction du 2026-08-14 (BUG-002, `CorrectifPlan.md`) :** la première
version appliquait le softmax sur `H` symétrisé, ce qui aurait rendu la
sortie invérifiable contre BERT classique dès que Q ≠ K (cas général,
puisque BERT apprend des projections indépendantes) — détecté par le test
I-01. Conséquence positive : l'équivalence Hopfield 1-pas ≡ attention
hermitienne (ci-dessous) est désormais inconditionnelle.

### Module d'équivalence Hopfield 1-pas

**Rôle :** `hopfield_step` calcule `softmax(β·Re(qK†))·K` (1 pas de mise à
jour de Hopfield continu complexe, Ramsauer et al. 2020) ; `hopfield_energy`
calcule la fonction de Liapounov associée. Depuis la correction BUG-002,
`Re(QK†)` (brut, non symétrisé) est exactement ce qu'utilise
`HermitianSelfAttention` pour son softmax — les deux chemins de calcul
coïncident pour Q, K, V quelconques (validé par U-03, cas auto-associatif
*et* cas général) — évite le goulet d'étranglement O(T³) de la
décomposition spectrale (`torch.linalg.eigh`) documenté dans
`BERT_hermitien_PoC` quand celle-ci n'est pas strictement nécessaire.
**Fichier :** `src/hopfield/equivalence.py`
**Interfaces :** `hopfield_step(q_real, q_imag, k_real, k_imag, v_real, v_imag, beta)`,
`hopfield_energy(s_real, z_real, z_imag, beta)`.

### HermitianFFN (échelle native, pas encore implémenté — cf. `docs/TODO.md`)

**Correction du 2026-09-18 (avant tout codage) :** la piste FFN
initialement notée (résonance matricielle `H' = φ(W₂(W₁HW₁†)W₂†)`, issue
de `contributions/gémini/Evolution_BERT_suite`) suppose un token
représenté par une **matrice** hermitienne — l'architecture à
compression écartée du pipeline natif (cf. section « Recherche —
Compression hermitienne »). Notre `HermitianSelfAttention` représente
chaque token par un **vecteur** `z ∈ C^{d_model}` ; `W₁HW₁†` n'a pas de
sens pour un vecteur. Piste corrigée, validée avec Bertrand.

**Rôle :** FFN position-wise pour l'architecture vectorielle native,
cohérent avec le principe déjà établi (la phase porte le déphasage, ne
pas la triturer arbitrairement — cf. softmax sur `Re(S)` seul dans
`HermitianSelfAttention`) :
```
FFN(z) = ComplexLinear₂( g(ComplexLinear₁(z)) )
g(z) = GELU(|z|) · z/|z|     # gate réel sur le module, phase préservée exactement
```
Analogue du "modReLU" (Arjovsky et al. 2016, Trabelsi et al. 2018) —
construction établie dans la littérature des réseaux complexes, pas
inventée pour l'occasion. L'alternative (GELU séparé sur Re et Im)
tournerait la phase de façon incontrôlée à chaque couche.
**Fichier :** `src/hermitian/ffn.py`, gate dans `src/hermitian/gating.py`.
**Statut :** implémenté et testé (2026-09-18).

### HermitianRMSNorm (échelle native)

**Rôle :** normalisation native, `L(z)=γ·z/(RMS(z)+ε)`,
`RMS(z)=√(mean(|z|²))`, `γ` réel par dimension appliqué identiquement à
Re et Im — préserve `arg(z)` exactement. Remplace la piste initialement
envisagée (normalisation de trace de Gémini, `N(H)=H/(Tr(H)+ε)`,
également définie pour une matrice, pas un vecteur — même correction que
pour `HermitianFFN` ci-dessus). Précédent empirique réel (RMSNorm,
LLaMA et consorts), contrairement à la normalisation de trace jamais
validée.
**Fichier :** `src/hermitian/norm.py`.
**Statut :** implémenté et testé (2026-09-18).

**Décision (2026-09-18) : `HermitianLayerNorm` gardée en parallèle**, pas
remplacée. Question de Bertrand : le centrage de `LayerNorm` joue-t-il un
rôle fonctionnel (discrimination des tokens dans l'attention par produit
scalaire sur des poids pré-entraînés) que `RMSNorm` perdrait en ne
centrant pas ? Vérifié empiriquement (`scripts/compare_normalizations.py`,
test de régression `test_layernorm_blind_to_dc_shift_but_not_rmsnorm`) :

| Perturbation | distance sous RMSNorm | distance sous LayerNorm |
|---|---|---|
| Décalage uniforme `ε·𝟙` | 0,099 | **0,000** |
| Orthogonale (moyenne nulle), même norme | 0,088 | 0,091 |

**Conclusion : pas de perte générale de discernement sous RMSNorm** —
LayerNorm est spécifiquement et exclusivement aveugle à la direction
« décalage uniforme partagé par toutes les dimensions » (le centrage
l'annule par construction), tout en restant aussi sensible que RMSNorm
aux perturbations dans les autres directions. RMSNorm est donc, si
quelque chose, *plus* discriminante sur cette direction précise, pas
moins. Ce qui reste vrai et motive de garder `LayerNorm` en parallèle :
les poids `Q`/`K` de BERT ont été appris avec des entrées centrées — un
biais partagé non centré peut gonfler artificiellement `Q·K` entre tokens
et dégrader l'attention lors du **portage de poids pré-entraînés**
spécifiquement (question distincte de la discrimination générale,
non encore testée empiriquement — à faire lors de l'extension du test de
portage à la couche complète).

### HermitianLayerNorm (échelle native, portage-compatible)

**Rôle :** centrage complexe complet, `LN(z)=γ·(z−mean(z))/std(z)+β`,
`mean`/`std` calculés sur `|z−mean(z)|²`. **Se réduit exactement à
`nn.LayerNorm` réelle quand `Im=0` et `bias_imag=0`** (même schéma de
portage que `ComplexLinear`/`WeightProjector`, testé). Ne préserve **pas**
la phase individuelle (soustraire une moyenne complexe partagée déplace
`arg(zᵢ)` différemment pour chaque composante) — compromis assumé, cf.
comparaison ci-dessus.
**Fichier :** `src/hermitian/norm.py`.
**Statut :** implémenté et testé (2026-09-18).

### HermitianBertLayer / HermitianBertModel (échelle native)

**Rôle :** empilement Post-LN identique à BERT classique :
```
x1 = Norm(x + Attention(x))
x2 = Norm(x1 + FFN(x1))
```
**Correction du 2026-09-18** : `HermitianRMSNorm` par défaut (`norm_cls`)
— préservation de la phase, principe directeur explicite de tout ce
travail (cf. `HermitianFFN`), confirmé par l'expérience de discrimination
ci-dessus (RMSNorm ne montre aucun désavantage face à LayerNorm, elle est
même plus discriminante sur l'axe DC). Une version précédente de ce
document faisait de `HermitianLayerNorm` le défaut au nom de la
compatibilité de portage — un raisonnement que Bertrand n'avait pas
validé (il avait accepté LayerNorm « en parallèle pour le temps de ces
tests », pas comme défaut définitif). `HermitianLayerNorm` reste
disponible via `norm_cls`, réservée à la vérification de portage de poids
(I-01 étendu), pas à l'architecture principale. `HermitianBertModel`
empile `num_layers` couches indépendantes (poids propres par couche,
comme BERT).
**Fichier :** `src/hermitian/layer.py`.
**Statut :** implémenté et testé structurellement (forme, finitude,
absence de fuite Re→Im quand rien n'en introduit) — **portage de poids
réel non testé à ce niveau** : `WeightProjector` ne couvre encore que le
bloc d'attention (I-01), pas le FFN. Extension nécessaire avant tout test
de portage à l'échelle couche/modèle complet (cf. `docs/TODO.md`).

### WeightProjector

**Rôle :** copie les poids d'un bloc `BertAttention` HuggingFace
(`self.{query,key,value}` + `output.dense`) dans la partie réelle d'un
`HermitianSelfAttention`, initialise la partie imaginaire par bruit
gaussien (`imag_std`, 0.0 pour le test de régression I-01).
**Portée actée avec Bertrand le 2026-08-14 :** bloc d'attention seul, pas
le modèle BERT complet (embeddings, FFN, LayerNorm, empilement multi-
couches non conçus — cf. `docs/TODO.md`, point ouvert).
**Fichier :** `src/weights/projector.py`
**Interfaces :** `project_bert_attention(hermitian_attn, hf_attention, imag_std=0.0)`.
**Charger le modèle source via `BertModel.from_pretrained` explicitement,
pas `AutoModel`** : certains checkpoints anciens (`prajjwal1/bert-tiny`)
ont un `config.json` sans `model_type`, incompatible avec `Auto*` sous
`transformers` récent (cf. `docs/spike-weights-state-dict-mapping.md`).
`bert-base-uncased` (cible Phase 2 pour un résultat citable) n'a pas ce
problème.

### SpectralCoherenceEvaluator (optionnel, si le calcul spectral est retenu)

**Rôle :** calcule pureté (`γ = Tr(ρ²)`), entropie de Von Neumann et gap
spectral à partir du spectre de `S` symétrisée. Réservé aux cas où
l'équivalence Hopfield ne suffit pas (cf. arbitrage Phase 1).
**Fichier :** `src/hermitian/spectral.py` (à créer si retenu)

### HermitianBottleneck / RealBottleneck (recherche, non planifié — cf. `docs/DevPlan.md`)

**Rôle :** composants du protocole de comparaison pour la piste de
recherche « compression hermitienne pour portage mobile » (posée par
Bertrand le 2026-08-14, distincte du pipeline Phase 3/4/5 qui reste à
l'échelle native `d_model`). Objectif : tester si `Herm(d)` (avec
`d² ≪ 768`, une vraie réduction — pas `d² ≈ 768` comme dans
`BERT_hermitien_PoC`) préserve plus d'information sémantique utile qu'un
vecteur réel non contraint au même budget de réels.

- **`RealBottleneck`** : encodeur/décodeur baseline `R^768 → R^{d²} → R^768`
  (ou vers la tâche avale), sans aucune contrainte hermitienne — sert de
  contrôle à budget de réels égal.
- **`HermitianBottleneck`** : encodeur `R^768 → Herm(d)` **plein rang**
  (sortie linéaire non contrainte de dimension `d²`, reshapée sous
  contrainte hermitienne — **pas** le projecteur `π(x)=φ(x)φ(x)†+diag(...)`
  de `BERT_hermitien_PoC`, qui est un produit extérieur de rang 1 et ne
  peuple que ~`3d` réels effectifs sur les `d²` disponibles, faussant toute
  comparaison en défaveur de l'hermitien). Décodeur symétrique.

**Fichiers :** `src/compression/real_bottleneck.py`, `src/compression/hermitian_bottleneck.py` (à créer — non planifiés, cf. `docs/DevPlan.md`).
**Point ouvert avant tout codage :** valeur(s) de `d` cible et métrique de
succès (fidélité de reconstruction, perplexité après distillation, ou
score GLUE — à ne pas mélanger, cf. `docs/test_plan.md`) à arbitrer avec
Bertrand.

### Superposition Leggett-Garg (sous-track de recherche, cf. `docs/DevPlan.md`)

**Rôle :** teste si un nœud/réseau hermitien exhibe une authentique
superposition (violation d'une inégalité de Leggett-Garg généralisée),
en régime **unitaire cohérent** (`γ=0`) — distinct de la dynamique
dissipative de `src/hermitian`/`src/hopfield`. Représentation en
`torch.complex64` natif (pas la paire réel/imag : aucune contrainte BF16
ici, ce module ne participe à aucune boucle d'entraînement).

- **`build_two_pattern_weights`** (`src/superposition/patterns.py`) :
  `W = ξ¹ξ¹† + ξ²ξ²†` (stockage hebbien à deux motifs), `Wᵢᵢ=0` par défaut
  (hypothèse Hopfield standard), option `zero_diagonal=False` pour la
  piste `Wᵢᵢ≠0` (cf. `docs/DevPlan.md`).
- **`evolution_operator`/`evolve`** (`src/superposition/dynamics.py`) :
  `U=exp(-iWΔt)` (cast FP32 local pour `matrix_exp`), trajectoire complète
  sur `nS` itérations.
- **`dichotomic_projectors`/`measure`** (`src/superposition/measurement.py`) :
  observable `Q=P₊−P₋` dichotomique (règle de Born, collapse), axe défini
  par les deux motifs concurrents.

- **`two_time_correlation`/`leggett_garg_k3`/`aggregated_local_k3`**
  (`src/superposition/harness.py`) : harnais Monte-Carlo, `K(3) =
  C₁₂+C₂₃−C₁₃`, un sous-ensemble frais de `M` tirages par paire de temps
  (mesurabilité non invasive). `exact_leggett_garg_k3` : version
  déterministe (probabilités de Born exactes, sans bruit d'échantillonnage)
  utilisée pour la régression I-04.

- **`generate_patterns`/`run_full_experiment`** (`src/superposition/experiment.py`) :
  motifs concrets (phases aléatoires par composante, normalisés
  `‖ξᵏ‖=1`), orchestration du run I-05 sur `nN∈{2,3,5,10,20}`.

**Pour relancer** (cf. `scripts/run_superposition_i05.py`) :
```bash
python scripts/run_superposition_i05.py --n-nodes 2 3 5 10 20 --dt 1.0 --m-samples 300
python scripts/run_superposition_i05.py --auto-m --sigma-target 5.0  # M recalculé par nN
```

**Fichiers :** `src/superposition/`, `scripts/run_superposition_i05.py`.
**Statut :** primitives, TU (U-05 à U-07), harnais + TI (I-04) et run
complet I-05 faits (deux passes, `docs/results/i05_run_2026-09-13.json`) :
`M=300` fixe → PARTIEL (2/10 à 5σ) ; `M` recalculé par `nN` (`required_m_for_significance`)
→ 9/10 à 5σ, avec une absence *significative* de violation locale à
`nN=3` (distincte de `Q_global`, qui viole pour ce même réseau). **Non
citable dans `Simulations_API.md`** : un seul tirage de motifs par `nN`,
robustesse de l'anomalie `nN=3` non établie — cf. `docs/DevPlan.md`.

## Flux de données

```
[Poids HF] → [WeightProjector] → [Modèle hermitien] → [Sortie complexe]
                                                          ↓
                                            [Comparaison GLUE vs baseline]
```

## Stockage

| Fichier | Type | Contenu |
|---|---|---|
| `checkpoints/*.pt` | Binaire PyTorch | Poids de modèles entraînés/fine-tunés (ignoré par git) |
| Config d'expérience | YAML/JSON | Seed, hyperparamètres, référencés dans les commits `experiment(...)` |

## Interfaces externes

| Service | Usage | Phase |
|---|---|---|
| HuggingFace Hub | Téléchargement de `prajjwal1/bert-tiny` (debug) et `bert-base-uncased` (citable) | Phase 2 |
| `datasets` (GLUE) | Données de benchmark | Phase 3 |
| Perceval (local) | Simulation de circuit photonique | Phase 4 |
| Quandela Cloud | Exécution QPU réelle | Phase 5 |

## Contraintes d'architecture

- BF16 pour le forward des couches complexes (mémoire/débit) ; cast FP32
  ciblé uniquement pour `torch.linalg.eigh` si le chemin spectral est
  utilisé (perte de résolution du gap spectral sinon).
- FP16 classique proscrit pour le produit hermitien QK† (risque d'overflow
  documenté — plage dynamique insuffisante).
- Le chemin « Hopfield 1-pas » est préféré au chemin spectral complet
  (`eigh`, O(T³)) chaque fois que la seule question posée est l'équivalence
  attention/Hopfield, pas la mesure fine de cohérence spectrale.

## Points de vigilance

- Le surcoût mémoire d'un passage à `complex64` est ×2 (poids et
  activations) ; le gradient checkpointing devient quasi obligatoire dès la
  Phase 3 (fine-tuning).
- Le calcul spectral, s'il est activé, coûte O(T³) par tête — à réserver à
  la dernière couche ou à un sous-échantillon d'itérations si le profilage
  le justifie (ne pas l'activer par défaut).
- Ne jamais évaluer l'effet architectural (Phase 3) avant d'avoir confirmé
  le test de régression du portage de poids (Phase 2) — cf.
  `docs/test_plan.md`.
- **Dérive numérique sur la composition répétée de `matrix_exp`** (constaté
  le 2026-09-13, `test_u07_hand_n2_evolution`) : appliquer `U=exp(-iWΔt)`
  `n` fois successivement (`evolve`) accumule une dérive d'arrondi FP32
  (~1e-4 observée sur `nS=3` pas) supérieure à un seul appel équivalent
  `exp(-iWnΔt)` — chaque appel à `matrix_exp` (Padé + scaling-squaring) a
  sa propre erreur d'approximation, qui se compose. Négligeable pour
  `nS=3` face aux effets recherchés (Δ(3)=0,5, cf. protocole Leggett-Garg),
  mais à surveiller si `nS` devait grandir significativement.
