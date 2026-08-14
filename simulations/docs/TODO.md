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

- [ ] Arbitrer avec Bertrand le rattachement (ou non) du plan Monte-Carlo
  superposition/intrication à ce projet (cf. CLAUDE.md, P1)
- [ ] **Conception non prévue** : `SW_Design.md` ne couvre que `ComplexLinear`,
  `HermitianSelfAttention`, l'équivalence Hopfield et `WeightProjector` —
  rien n'est encore conçu pour le FFN complexe, les `LayerNorm` complexes,
  les embeddings, ni l'empilement multi-couches d'un `HermitianBertModel`
  complet. Repéré le 2026-08-14 en scopant le test I-01 (portage de poids) :
  décidé avec Bertrand de limiter I-01 au bloc d'attention seul pour
  l'instant (cf. `docs/DevPlan.md`, Phase 2) — mais la question de
  l'architecture complète reste ouverte et devra être tranchée avant toute
  comparaison GLUE bout-en-bout (Phase 3).

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

<!-- Format : - [x] YYYY-MM-DD — description (commit: abc1234) -->
