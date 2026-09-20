# simulations — Contrat de résultats (fichier d'échange inter-projet)

<!--
  CE FICHIER EST LE CONTRAT INTER-PROJET.
  Règles absolues :
  - Ne documenter ici que ce qui est STABLE ET CITABLE dans le manuscrit
    RadioHumaine : définitions de métriques, figures, seuils de
    significativité, tables de résultats validées par leur plan de test.
  - Ne jamais y décrire l'implémentation (voir SW_Design.md pour ça).
  - Bumper contract_version + ajouter une entrée [PENDING] dans
    Simulations_API_CHANGELOG.md à chaque modification d'un résultat déjà
    cité, dans le même commit.
  - Ce fichier n'existe que parce que ce projet est de rôle "Producteur"
    (voir CLAUDE.md).
-->

---

contract_version: 2026-09-18-v2
date: 2026-09-18
consumers:
  - RadioHumaine

---

## 1. Résultats disponibles

### Violation de Leggett-Garg dans un réseau hermitien à deux motifs (régime unitaire cohérent)

**Affirmation testée :** un réseau de nœuds hermitiens (représentation
phasor, `W` construit par stockage hebbien de deux motifs concurrents)
viole une inégalité de Leggett-Garg généralisée à `nS=3` temps de mesure,
de façon statistiquement incompatible avec un taux de violation nul —
pour des tailles de réseau `nN=3` et `nN=10`.

**Méthode :** `docs/test_plan.md` (U-05 à U-07, I-04, protocole
confirmatoire pré-enregistré `docs/DevPlan.md`),
`scripts/run_superposition_confirmatory.py`.

**Seuil de significativité fixé a priori :** succès par tirage = 5σ (`M`
dimensionné sur la marge exacte, plafonné à `M≤200000`) ; décision globale
= `p_value` du test binomial `< p_null≈2,87×10⁻⁷` (30 tirages frais par
`nN`).

**Résultat :** `nN=3` : 17/30 succès, `p=7,13×10⁻¹⁰⁴`. `nN=10` : 24/30
succès, `p=5,63×10⁻¹⁵²`. Rejet net de l'hypothèse nulle pour les deux
tailles.

**Figure/table :** `docs/results/confirmatory_run_2026-09-18.json`.

**Strate proposée pour le livre : Strate 1**, avec une réserve explicite
à reporter dans le texte : le résultat est établi pour ce modèle
spécifique (phasor scalaire, deux motifs, régime unitaire cohérent,
mesure projective avec collapse) — pas une démonstration générale de
superposition dans tout réseau hermitien, et sa valeur principale est
méthodologique (falsifiabilité du protocole) plutôt qu'une découverte
physique nouvelle.

---

## 2. Définitions de métriques stables

<!-- À compléter au fur et à mesure : ex. définition exacte du score de
     cohérence spectrale C(X) si retenu, définition du seuil de tolérance
     du test de portage de poids. -->

---

## 3. Contraintes d'intégration pour le manuscrit

| Contrainte | Détail |
|---|---|
| Strate | Un résultat de ce fichier ne peut être cité en Strate 1 par RadioHumaine que s'il est listé ici avec un test associé vert — jamais un résultat encore en Phase de développement |
| Reproductibilité | Toute figure citée doit être régénérable depuis un commit taggé de ce projet |
