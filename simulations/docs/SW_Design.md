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
(`Y_r = X_r W_r − X_i W_i`, `Y_i = X_r W_i + X_i W_r`), deux `nn.Linear`
réels internes (`fc_real`, `fc_imag`).
**Fichier :** `src/hermitian/complex_linear.py`
**Interfaces :** `forward(x_real, x_imag) -> (y_real, y_imag)`.

### HermitianSelfAttention

**Rôle :** attention `S = Q K† / √d_k`, symétrisée explicitement
(`H = (S + S†)/2`, soit partie réelle symétrisée + partie imaginaire
antisymétrisée) avant tout usage en aval. Softmax appliqué sur `Re(H)`
uniquement ; la partie imaginaire porte le déphasage.
**Fichier :** `src/hermitian/attention.py`
**Interfaces :** `forward(x_real, x_imag) -> (out_real, out_imag, (h_real, h_imag))`.

### Module d'équivalence Hopfield 1-pas

**Rôle :** `hopfield_step` calcule `softmax(β·Re(qK†))·K` (1 pas de mise à
jour de Hopfield continu complexe, Ramsauer et al. 2020) ; `hopfield_energy`
calcule la fonction de Liapounov associée. Dans le cas auto-associatif
(Q = K = V, projections partagées), `Re(QK†)` est automatiquement
symétrique, donc la symétrisation de `HermitianSelfAttention` devient un
no-op et les deux chemins de calcul coïncident exactement (validé par
U-03) — évite le goulet d'étranglement O(T³) de la décomposition spectrale
(`torch.linalg.eigh`) documenté dans `BERT_hermitien_PoC` quand celle-ci
n'est pas strictement nécessaire.
**Fichier :** `src/hopfield/equivalence.py`
**Interfaces :** `hopfield_step(q_real, q_imag, k_real, k_imag, v_real, v_imag, beta)`,
`hopfield_energy(s_real, z_real, z_imag, beta)`.

### WeightProjector

**Rôle :** charge un modèle HuggingFace (`bert-base-uncased`), copie ses
poids dans la partie réelle des couches hermitiennes, initialise la partie
imaginaire par bruit gaussien faible.
**Fichier :** `src/weights/projector.py` (à créer, Phase 2)
**Interfaces :** entrée = nom de modèle HF ; sortie = modèle hermitien
instancié avec poids injectés.

### SpectralCoherenceEvaluator (optionnel, si le calcul spectral est retenu)

**Rôle :** calcule pureté (`γ = Tr(ρ²)`), entropie de Von Neumann et gap
spectral à partir du spectre de `S` symétrisée. Réservé aux cas où
l'équivalence Hopfield ne suffit pas (cf. arbitrage Phase 1).
**Fichier :** `src/hermitian/spectral.py` (à créer si retenu)

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
| HuggingFace Hub | Téléchargement de `bert-base-uncased` | Phase 2 |
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
