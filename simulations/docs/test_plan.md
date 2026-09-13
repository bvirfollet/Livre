# Plan de test — simulations

## Niveau applicable

- [x] Unitaire — maths déterministes, sans dépendance externe
- [x] Intégration — comparaison empirique (poids HF, GLUE, Perceval)
- [ ] Matériel réel — QPU Quandela (Phase 5 uniquement, coûteux, non systématique)

## Condition de succès

Chaque affirmation citée dans `Simulations_API.md` est accompagnée d'un test
reproductible (config + seed archivés) et d'un seuil fixé *avant* le run.

## Principe de séparation strict (à ne jamais violer)

Un test de **portage de poids** (le modèle hermitien avec partie imaginaire
≈ 0 reproduit-il le BERT classique ?) et un test d'**effet architectural**
(l'architecture hermitienne change-t-elle le comportement au-delà du bruit
de mesure ?) répondent à deux questions différentes. Ne jamais lancer
seulement le second sans avoir d'abord fait passer le premier : un bug de
portage et un effet réel de l'architecture sont sinon indiscernables.

## Tests unitaires (Phase 1)

**Correction du 2026-08-14 :** la mention initiale « cas N=2 et N=3 vérifiés
à la main dans `BERT_hermitien_PoC` » était inexacte — ce fichier ne
contient aucun exemple numérique explicite pour l'attention hermitienne ou
l'équivalence Hopfield (vérifié par grep exhaustif sur le document source).
Les cas N=2 ci-dessous sont calculés à la main directement dans les fichiers
de test (`tests/test_hermitian.py`, `tests/test_hopfield.py`), avec le
détail du calcul en docstring.

**Tolérances fixées a priori (falsifiabilité avant calcul) :** `atol=1e-5`,
`rtol=1e-4`, arithmétique FP32 — cf. `tests/conftest.py::ATOL/RTOL`. Choisies
larges par rapport au bruit d'arrondi FP32 attendu (~1e-7) : un dépassement
signale un vrai bug, pas du bruit numérique.

| ID | Ce qui est testé | Entrée | Résultat attendu |
|---|---|---|---|
| U-01 | Hermiticité de `H = (S+S†)/2` après symétrisation | Q, K aléatoires + cas N=2 calculé à la main | `H_real` symétrique, `H_imag` antisymétrique (diagonale nulle), à `atol=1e-5`/`rtol=1e-4` |
| U-02 | Réalité du spectre | cas N=2 hermitien calculé à la main (valeurs propres analytiques) + invariant `Tr(H) = Σλ` sur cas aléatoire | `torch.linalg.eigh` (cast FP32 local) reproduit les valeurs propres attendues à `atol=1e-5`/`rtol=1e-4` |
| U-03 | Équivalence Hopfield 1-pas ≡ attention hermitienne | cas auto-associatif Q=K=V + cas général Q,K,V indépendants + cas N=2 calculé à la main | sorties identiques à `atol=1e-5`/`rtol=1e-4` — équivalence **inconditionnelle** depuis la correction BUG-002 du 2026-08-14 (`CorrectifPlan.md`) : le softmax de `HermitianSelfAttention` porte sur S brut, jamais sur le H symétrisé |
| U-04 | Overflow FP16 sur le produit hermitien | valeurs de grande magnitude (300), dtype FP16 vs BF16 | reproduit l'overflow documenté en FP16 (test de régression négatif) ; absence d'overflow en BF16 sur les mêmes valeurs |

## Tests d'intégration — portage de poids (Phase 2)

**Portée réduite actée avec Bertrand le 2026-08-14 :** bloc d'attention
seul (`BertAttention` HuggingFace = self-attention + `output.dense`), pas
un `BertModel` complet — embeddings/FFN/LayerNorm/empilement multi-couches
non conçus (point ouvert, `docs/TODO.md`).

| ID | Précondition | Action | Résultat attendu | Résultat obtenu |
|---|---|---|---|---|
| I-01 | `HermitianSelfAttention` instancié, poids projetés via `WeightProjector` depuis un `BertAttention` HuggingFace, partie imaginaire forcée à 0 (`imag_std=0.0`) | Forward sur un batch aléatoire, comparé à `hf_attention.output.dense(hf_attention.self(x)[0])` (bypass LayerNorm/résiduelle, absentes du module) | Sortie réelle ≈ sortie HuggingFace à `atol=1e-5`/`rtol=1e-4` ; sortie imaginaire exactement nulle | **Vert** (`prajjwal1/bert-tiny`, `tests/test_weights.py`) — diff max observée ~1e-6 |

## Tests d'intégration — effet architectural GLUE (Phase 3)

| ID | Précondition | Action | Résultat attendu | Résultat obtenu |
|---|---|---|---|---|
| I-02 | I-01 vert | Éval GLUE, BERT classique vs BERT hermitien, seeds fixées | Score comparé à un seuil de significativité fixé avant le run | |

## Tests d'intégration — Perceval (Phase 4)

| ID | Composant tiers | Stimulus | Comportement attendu | Observé |
|---|---|---|---|---|
| I-03 | Circuit Perceval reconstruit depuis la décomposition de Givens | `compute_unitary()` | `U @ U.conj().T ≈ I` | |

## Tests unitaires — Superposition Leggett-Garg (nouveau sous-track, cf. docs/DevPlan.md)

Régime unitaire cohérent (`γ=0`), distinct de la dynamique dissipative
testée par U-01 à U-04. Détail complet du protocole (`nN`, `nS`, `M`,
seuils) dans `docs/DevPlan.md`, section « Recherche — Superposition
quantique ».

| ID | Ce qui est testé | Entrée | Résultat attendu |
|---|---|---|---|
| U-05 | Hermiticité de `W` construit à partir de deux motifs | motifs `ξ¹`, `ξ²` (cas `nN=2` calculé à la main) | `W == W.conj().T` à `atol=1e-5`/`rtol=1e-4` |
| U-06 | Unitarité de l'évolution `U=e^{-iWΔt}` | `W` hermitien (cast FP32 pour `matrix_exp`) | `U U† ≈ I` à `atol=1e-5`/`rtol=1e-4` ; norme `|z|` conservée après application de `U` |
| U-07 | Cas `nN=2` vérifié à la main | `W`, `z(0)` explicites, calcul analytique de `z(t)` pour `nS=3` pas | sortie du code ≈ calcul analytique à `atol=1e-5`/`rtol=1e-4` |

## Tests d'intégration — Superposition Leggett-Garg (harnais Monte-Carlo)

| ID | Précondition | Action | Résultat attendu | Résultat obtenu |
|---|---|---|---|---|
| I-04 | U-05 à U-07 verts | Régression : calcul de `K(3)` en mesure idéale (sans bruit d'échantillonnage, cas non stochastique) sur le système à 2 niveaux de référence (Saha, Mal, Panigrahi & Home, arXiv:1409.1132) | `K(3) = 3/2` (violation maximale théorique) reproduite à `atol=1e-5` | |
| I-05 | I-04 vert | Run complet : 10 tests (`Q_global` × 5 `nN`, `Q_i` agrégé × 5 `nN`), `M=300` par corrélation, seeds archivées | Violation ≥5σ (par test), correction de Bonferroni sur la famille de 10 | |

## Tests — Recherche compression hermitienne (non planifiée, cf. docs/DevPlan.md)

**Non chiffrable en IDs de test tant que `d` cible et métrique de succès
ne sont pas arbitrés avec Bertrand** — consigné ici pour mémoire du
protocole convenu le 2026-08-14, à formaliser en tests concrets
(`R-01`, `R-02`, ...) une fois ces points tranchés.

Question falsifiable : à budget de réels strictement égal (`d²` pour les
deux côtés), `HermitianBottleneck` (`R^768 → Herm(d)` plein rang, `d² ≪ 768`)
préserve-t-il plus d'information sémantique utile que `RealBottleneck`
(`R^768 → R^{d²}` non contraint) ?

Trois métriques candidates, à ne pas mélanger dans un même run (chacune
répond à une question différente, cf. principe de séparation stricte
ci-dessus) :
- Fidélité de reconstruction (distance Hilbert-Schmidt / MSE) — teste la
  compression pure, sans tâche linguistique.
- Perplexité après distillation — teste la préservation de la capacité
  générative.
- Score GLUE après fine-tuning — teste la préservation de la capacité
  discriminative en aval.

Piège de protocole à ne pas reproduire (déjà identifié, cf.
`docs/DevPlan.md`) : un encodeur `Herm(d)` construit via un produit
extérieur (`φ(x)φ(x)†`, rang 1) handicape artificiellement le côté
hermitien — n'utiliser que des encodeurs plein rang des deux côtés.

## Cas limites à couvrir systématiquement

- [ ] Comportement si le nombre de modes Perceval demandé dépasse la limite
  matérielle actuelle (~6-12 modes en Cloud)
- [ ] Idempotence (rejouer le même run avec la même seed donne le même résultat)
- [ ] Comportement en précision réduite (BF16) sur le gap spectral — doit
  être documenté comme dégradé, pas silencieusement ignoré

## Critères de non-régression

- [ ] U-01 à U-04 doivent rester verts à chaque modification des modules hermitiens
- [ ] I-01 doit rester vert avant tout nouveau run GLUE cité dans `Simulations_API.md`
