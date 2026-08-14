Exécute la procédure de release complète : vérification de reproductibilité, changelog, tag git, archivage TODO.

## Utilisation

`/release [version]`

Exemple : `/release 0.2.0`

Si la version n'est pas fournie, détermine la prochaine version en lisant la dernière dans RELEASES.md et en demandant confirmation (patch / minor / major).

## Étapes à suivre

1. **Vérifie l'état du dépôt** :
   ```bash
   git status
   git log --oneline -10
   ```
   - Aucun fichier non commité (sinon demander confirmation)
   - Branche courante cohérente avec une release (pas une branche explore/)

2. **Détermine la version** :
   - Lit la dernière version dans `RELEASES.md`
   - Si argument fourni : utilise cet argument
   - Sinon : propose patch/minor/major selon les commits depuis la dernière release

3. **Vérifie la reproductibilité des résultats cités** dans cette version :
   - Tout commit `experiment(...)` depuis la dernière release référence-t-il bien une config et une seed archivées ?
   - Si un résultat déjà cité dans `docs/Simulations_API.md` a changé, `contract_version` a-t-il été bumpé et une entrée `[PENDING: RadioHumaine]` ajoutée dans `docs/Simulations_API_CHANGELOG.md`, dans le même commit ?

4. **Met à jour `RELEASES.md`** :
   - Ajoute une section `## vX.Y.Z — [date du jour]`
   - Liste les commits depuis la dernière release, groupés par type :
     ```bash
     git log [last_tag]..HEAD --oneline --pretty=format:"- %s"
     ```
   - Format : Nouvelles fonctionnalités / Correctifs / Améliorations / Résultats (expériences) / Breaking changes

5. **Archive les items résolus dans `docs/TODO.md`** :
   - Déplace les items `- [x]` vers la section "Historique" avec la date du jour

6. **Commit de release** :
   ```bash
   git add RELEASES.md docs/TODO.md docs/Simulations_API.md docs/Simulations_API_CHANGELOG.md
   git commit -m "release: v[version]"
   ```
   Rappel : pas de Co-Authored-By, pas de mention d'IA.

7. **Crée le tag git** :
   ```bash
   git tag v[version]
   ```
   Affiche la commande de push à exécuter manuellement :
   ```bash
   git push origin v[version]
   ```
   Ne pas pousser automatiquement — demander confirmation.

8. **Résumé final** : version, tag, fichiers modifiés, changelog de la release.
