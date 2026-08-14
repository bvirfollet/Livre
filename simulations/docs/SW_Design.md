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

### ComplexLinear

**Rôle :** couche linéaire sur `torch.complex64`, décomposition explicite
Re/Im (`Y_r = X_r W_r − X_i W_i`, `Y_i = X_r W_i + X_i W_r`).
**Fichier :** `src/hermitian/complex_linear.py` (à créer, Phase 1)
**Interfaces :** entrée/sortie `torch.complex64`.

### HermitianSelfAttention

**Rôle :** attention `S = Q K† / √d_k`, symétrisée explicitement
(`H = (S + S†)/2`) avant toute exploitation spectrale. Softmax appliqué sur
`Re(S)` uniquement ; la partie imaginaire porte le déphasage.
**Fichier :** `src/hermitian/attention.py` (à créer, Phase 1)

### Module d'équivalence Hopfield 1-pas

**Rôle :** démontre que `softmax(β·Re(qK†))·K` (1 pas de mise à jour de
Hopfield continu complexe) reproduit le résultat de
`HermitianSelfAttention`, sans passer par une décomposition spectrale
(`torch.linalg.eigh`) — évite le goulet d'étranglement O(T³) documenté dans
`BERT_hermitien_PoC` quand celui-ci n'est pas strictement nécessaire.
**Fichier :** `src/hopfield/equivalence.py` (à créer, Phase 1)

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
