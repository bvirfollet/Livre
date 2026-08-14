Crée un spike de faisabilité pour la question fournie en argument (ou demande-la si absente).

## Étapes à suivre

1. **Valide** que la question est précise et binaire (OUI/NON/PARTIEL). Si elle est trop large, propose de la découper.

2. **Crée la branche** explore/[scope]-[slug] depuis la branche courante :
   ```bash
   git checkout -b explore/[scope]-[slug]
   ```

3. **Génère le fichier spike** `docs/spike-[scope]-[slug].md` avec le template suivant rempli autant que possible :

```markdown
# Spike — [scope] : [question de faisabilité]

Branche : explore/[scope]-[slug]
Date : [date du jour]

## Question
[question précise et binaire]

## Contraintes identifiées a priori
- [ce qu'on sait déjà être hors de contrôle]

## Protocole de test minimal
- [ ] Vérification 1 : [vérification la plus simple possible]
- [ ] Vérification 2 :
- [ ] Vérification 3 (si nécessaire) :

## Résultat
- Réponse : [À REMPLIR : OUI / NON / PARTIEL]
- Contrainte découverte :
- Impact sur le design :
- Condition de succès pour le feat :

## Décision
- [ ] Le feat peut démarrer tel que spécifié
- [ ] Le feat nécessite une adaptation (décrire)
- [ ] Bloquer — contrainte insurmontable dans le scope actuel
```

4. **Rappelle les règles** :
   - Durée max : 2h
   - UN seul changement à la fois lors des tests
   - ≥ 3 tentatives sans convergence → STOP
   - Commit de conclusion obligatoire : `spike([scope]): [résultat en une ligne]`
   - Squash avant retour sur la branche principale
   - Supprimer la branche explore/ après merge

5. **Affiche le protocole de test minimal** suggéré en fonction de la question posée — pour ce projet, les cas typiques sont : prise en main de `perceval-quandela`, comportement numérique d'un algorithme en précision réduite, authentification/quota Quandela Cloud.
