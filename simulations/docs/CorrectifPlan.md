# Plan correctif — simulations

Historique des bugs identifiés et des correctifs appliqués.

---

## Template d'entrée

```
### BUG-XXX — [Titre court]

**Sévérité :** critique / majeur / mineur
**Découvert :** YYYY-MM-DD
**Corrigé :** YYYY-MM-DD (commit: abc1234)

**Symptôme :**
Description observable du bug.

**Cause racine :**
Explication technique précise.

**Correctif appliqué :**
Ce qui a été changé et pourquoi.

**Impact potentiel :**
Autres composants susceptibles d'être affectés (en particulier : un résultat
déjà cité dans `Simulations_API.md` est-il affecté ? Si oui, bumper le
contrat dans le même commit).

**Test de non-régression :**
Comment vérifier que le bug ne revient pas.
```

---

## Bugs ouverts

<!-- Bugs identifiés non encore corrigés -->

## Bugs résolus

### BUG-001 — Fuite de biais réel dans la partie imaginaire de ComplexLinear

**Sévérité :** critique
**Découvert :** 2026-08-14 (en concevant le test I-01, avant tout run)
**Corrigé :** 2026-08-14

**Symptôme :**
Avec la partie imaginaire d'entrée nulle et les poids/biais imaginaires mis
à zéro (cas exact du test I-01), `ComplexLinear` produisait une sortie
imaginaire non nulle au lieu de 0.

**Cause racine :**
`ComplexLinear` réutilisait le biais des deux `nn.Linear` internes
(`fc_real`, `fc_imag`) dans les deux équations de sortie :
`out_imag = fc_real(x_imag) + fc_imag(x_real)` incluait `bias_real` (biais
de `fc_real`) même quand `x_imag = 0`, alors que la formule correcte
`Y_imag = X_real·W_imag + X_imag·W_real + B_imag` ne doit jamais faire
apparaître `B_real`.

**Correctif appliqué :**
`fc_real`/`fc_imag` construits avec `bias=False` ; deux `nn.Parameter`
dédiés `bias_real`/`bias_imag` ajoutés et appliqués une seule fois, chacun
dans sa propre équation.

**Impact potentiel :**
Aucun résultat déjà cité dans `Simulations_API.md` (contrat encore vide à
cette date). Tests Phase 1 (U-01 à U-04) mis à jour (`bias_real`/`bias_imag`
au lieu de `fc_real.bias`/`fc_imag.bias`) — tous restés verts, le bug
n'affectait aucune de leurs assertions (aucune ne comparait à une référence
externe à biais non nul).

**Test de non-régression :**
`tests/test_weights.py::test_i01_weight_portage_imag_zero_matches_classic_bert`
— vérifie explicitement `out_imag ≈ 0` avec biais HuggingFace réels
(non nuls) injectés dans la partie réelle.

---

### BUG-002 — Softmax appliqué sur S symétrisé au lieu de S brut

**Sévérité :** critique
**Découvert :** 2026-08-14 (test I-01, premier run réel avec bert-tiny)
**Corrigé :** 2026-08-14

**Symptôme :**
Portage de poids réel (`prajjwal1/bert-tiny`, partie imaginaire à 0) :
écart maximal de 0.93 entre `HermitianSelfAttention` et
`BertAttention` HuggingFace — bien au-delà du bruit flottant attendu
(~1e-6).

**Cause racine :**
`HermitianSelfAttention.forward` appliquait le softmax sur `H = (S+S†)/2`
(symétrisé) au lieu de `S` brut. `docs/SW_Design.md` prescrivait déjà la
bonne règle (« symétrisée... avant toute exploitation *spectrale* »,
softmax sur Re(S)) mais l'implémentation de la Phase 1 avait conflé les
deux usages. Sans dépendance externe à biais/poids réels, les tests U-01 à
U-04 ne pouvaient pas détecter l'écart : la symétrisation est un no-op
exact quand Q = K (cas testé en Phase 1, `test_u03_equivalence_auto_associative`),
et BERT apprend justement des projections Q ≠ K indépendantes.

**Correctif appliqué :**
Le softmax porte désormais sur `s_real` (brut, non symétrisé) ; `h_real`/
`h_imag` (symétrisés) restent calculés et retournés, mais uniquement pour
l'inspection/l'exploitation spectrale en aval (`eigh`), jamais réinjectés
dans le softmax. Conséquence positive : l'équivalence Hopfield 1-pas ≡
attention hermitienne (`src/hopfield/equivalence.py`) devient
inconditionnelle (Q, K, V quelconques) au lieu d'être restreinte au cas
auto-associatif Q = K — cf. nouveau test
`test_u03_equivalence_general_qkv`.

**Impact potentiel :**
Aucun résultat déjà cité dans `Simulations_API.md`. Documentation mise à
jour en conséquence : `SW_Design.md`, docstrings de `attention.py` et
`equivalence.py`.

**Test de non-régression :**
`tests/test_weights.py::test_i01_weight_portage_imag_zero_matches_classic_bert`
(régression bout-en-bout sur poids réels) + `tests/test_hopfield.py::test_u03_equivalence_general_qkv`
(régression ciblée : Q ≠ K, vérifie explicitement que `h_real ≠ s_real`
tout en confirmant que le softmax utilisé correspond à `s_real`).

---

### BUG-003 — Gate du FFN basé sur le module, ne se réduit pas à GELU réel

**Sévérité :** critique
**Découvert :** 2026-09-18 (en préparant le portage de poids du FFN)
**Corrigé :** 2026-09-18

**Symptôme :**
`phase_preserving_gate` (`g(z)=GELU(|z|)·z/|z|`) donnait, à `Im=0`, des
valeurs très éloignées de `GELU` réel classique pour les entrées
négatives — ex. `Re=-2` : `GELU(-2)≈-0.045` (réel) contre `≈-1.95` (notre
gate). N'aurait été détecté qu'au moment du test de portage du FFN
(pas encore écrit), pas par les tests existants (aucun ne comparait à une
référence `GELU` réelle asymétrique).

**Cause racine :**
`GELU` n'est pas une fonction impaire (`GELU(-x) ≠ -GELU(x)`) — c'est même
tout l'intérêt de `GELU` par rapport à une fonction symétrique comme
`ReLU` centré. En faisant porter le gate sur `|z|` (une quantité toujours
positive, symétrique par construction), l'asymétrie réel/négatif de
`GELU` était effacée dès que `Im=0`.

**Correctif appliqué :**
`g(z) = z · Φ(Re(z))`, `Φ` = fonction de répartition normale standard
(`GELU(x)=x·Φ(x)` est la définition exacte de GELU). `Φ(Re(z))` est
toujours réel positif (`∈(0,1)`), donc `g` préserve la phase exactement
(comme avant), mais se réduit maintenant à `GELU(Re)` exactement quand
`Im=0` — sans division ni `ε` (plus simple et plus stable que la version
précédente).

**Impact potentiel :**
Aucun résultat déjà cité dans `Simulations_API.md`. `HermitianFFN` n'était
pas encore utilisé dans un test de portage de poids réel — impact limité
aux tests unitaires du gate/FFN, tous mis à jour.

**Test de non-régression :**
`tests/test_hermitian_ffn_norm.py::test_phase_preserving_gate_reduces_to_real_gelu_when_im_zero`
et `test_hermitian_ffn_reduces_to_real_ffn_when_im_zero` (bout-en-bout,
FFN complet comparé à `Linear→GELU→Linear` réel).
