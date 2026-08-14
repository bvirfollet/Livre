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

contract_version: 2026-08-14-v1
date: 2026-08-14
consumers:
  - RadioHumaine

---

## 1. Résultats disponibles

<!-- Aucun résultat validé à ce stade — initialisation du contrat.
     Ajouter une section par résultat citable, au format :

     ### [Nom du résultat]
     **Affirmation testée :** <!-- ex. l'extension hermitienne de BERT
       préserve le score GLUE à ±X% -->
     **Méthode :** <!-- renvoi à docs/test_plan.md, ID du test -->
     **Seuil de significativité fixé a priori :** <!-- valeur -->
     **Résultat :** <!-- OUI / NON / PARTIEL, chiffre -->
     **Figure/table :** <!-- chemin -->
     **Strate proposée pour le livre :** <!-- 1, 2 ou 3 -->
-->

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
