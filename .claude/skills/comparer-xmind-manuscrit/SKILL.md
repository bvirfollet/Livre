---
name: comparer-xmind-manuscrit
description: Compare le contenu de la carte mentale xmind (methodologie/RadioHumaine — Disruptifs & Équations.xmind) à l'état actuel du manuscrit (Livre/manuscrit_draft_§N-§M.md) et des notes méthodologiques déjà arbitrées (elements_disruptifs_gemini_a_integrer.md, formules_candidates_par_chapitre.md, formalisation_effondrement_dimensionnel.md), puis met à jour la todo list de rédaction methodologie/todo_xmind_vs_manuscrit.md. Utiliser quand Bertrand a modifié le xmind et veut resynchroniser la liste des tâches de rédaction, ou demande "qu'est-ce qui a changé dans le xmind par rapport au texte".
---

# Comparer le xmind au manuscrit et mettre à jour la todo list

Le xmind (`methodologie/RadioHumaine — Disruptifs & Équations.xmind`) est
l'outil de planification arbitrée de Bertrand — contrairement aux
contributions brutes de Gémini, les entrées qui s'y trouvent portent déjà
des décisions ("confirmé par Bertrand", "à exclure", "candidat fort ★★★").
Rappel de CLAUDE.md : le xmind sert à *organiser*, jamais à *rédiger* — ce
skill ne doit donc jamais copier une formulation du xmind directement dans
le manuscrit ; il produit une liste de tâches qui sera traitée section par
section, dans un échange dédié, après validation de la cohérence avec
Bertrand.

## Quand l'utiliser

- Bertrand vient de modifier le xmind et veut savoir ce que ça change pour
  la suite de la rédaction.
- Avant de reprendre la rédaction d'une section, pour vérifier qu'aucune
  décision prise dans le xmind n'est restée sans suite dans le texte ou les
  notes méthodologiques.

## Étapes

### 1. Localiser le xmind actif

Il peut exister plusieurs fichiers `.xmind` dans `methodologie/`. Le fichier
de référence pour ce skill est celui dont le nom contient
« Disruptifs & Équations » (format XMind Zen : zip contenant `content.json`).
Si un autre `.xmind` existe (ex. `RadioHumaine_synthese.xmind`, format XMind
legacy avec seulement `content.xml`) et que son contenu diverge
significativement de celui du fichier de référence, le signaler à Bertrand
en fin de rapport plutôt que de trancher — les deux fichiers ne doivent pas
dériver silencieusement l'un de l'autre.

Vérifier avec `git status` / dates de modification lequel a été touché le
plus récemment ; c'est celui-là qui reflète les dernières décisions de
Bertrand.

### 2. Extraire l'arbre du xmind

Un `.xmind` Zen est un zip. Extraire l'arbre complet (titres + notes) avec
un script Python inline, par exemple :

```python
import zipfile, json
z = zipfile.ZipFile("methodologie/RadioHumaine — Disruptifs & Équations.xmind")
j = json.loads(z.read("content.json").decode("utf-8"))
def walk(topic, depth=0):
    print("  "*depth + f"- {topic.get('title','')}")
    notes = (topic.get("notes") or {}).get("plain", {}).get("content")
    if notes:
        print("  "*depth + f"  [note] {notes}")
    for ch in (topic.get("children") or {}).values():
        for c in ch:
            walk(c, depth+1)
for sheet in j:
    walk(sheet["rootTopic"])
```

Pour un `.xmind` legacy (seulement `content.xml`), parser le XML
(`xmlns:...:content:2.0`, éléments `<topic><title>...</title>`) avec le
même principe récursif.

Ne pas déléguer cette extraction à un agent : c'est un script déterministe,
pas une tâche de jugement.

### 3. Situer l'état actuel du manuscrit et des notes déjà arbitrées

Lire (directement, pas via agent — ce sont des fichiers de référence à
recouper précisément) :
- `Livre/manuscrit_draft_§N-§M.md` (dernier fichier de ce nom) : ce qui est
  déjà rédigé, section par section.
- `methodologie/elements_disruptifs_gemini_a_integrer.md` : ce qui est déjà
  indexé comme en attente d'intégration depuis les contributions brutes.
- `methodologie/formules_candidates_par_chapitre.md` : formules déjà
  inventoriées et leur recommandation.
- `methodologie/formalisation_effondrement_dimensionnel.md` (ou tout autre
  document de consolidation thématique existant) : concepts transversaux
  déjà consolidés.
- `CLAUDE.md` : sections validées, corrections en attente, éléments
  réservés à des chapitres futurs.

### 4. Classer chaque nœud du xmind

Pour chaque feuille de branche « Équations », « Éléments disruptifs »,
« Vision fractale », « TODO / prochaines étapes », etc., déterminer un
statut parmi :

- **Déjà rédigé** — le concept ou la formule est visible dans le
  manuscrit, avec repère (numéro de ligne ou citation courte).
- **Déjà noté, pas encore rédigé** — présent dans une des notes
  méthodologiques mais absent du texte. Indiquer où (fichier + section).
- **Nouveau** — absent du manuscrit ET des notes méthodologiques. C'est ce
  qui justifie une entrée dans la todo list.
- **Marqué à exclure dans le xmind** (ex. « ⚠️ À EXCLURE », « non retenu ») —
  reporter tel quel comme décision actée, ne pas le classer comme tâche.
- **Contradiction** — le xmind indique un statut (« déjà validé dans le
  texte ») qui ne correspond pas à ce qui est réellement rédigé, ou une note
  méthodologique et le xmind se contredisent sur la strate ou la
  recommandation. Signaler explicitement, c'est le type d'écart le plus
  important à faire remonter à Bertrand.

### 5. Mettre à jour `methodologie/todo_xmind_vs_manuscrit.md`

Ne pas régénérer le fichier entier à l'aveugle s'il existe déjà : reprendre
sa structure, mettre à jour les entrées dont le statut a changé (ex. un
"nouveau" d'hier devenu "déjà rédigé"), ajouter les nouvelles, et retirer
(ou marquer "traité — voir §X") les entrées intégrées entre-temps.

Structure attendue, par chapitre (dans l'ordre du manuscrit puis chapitres
non encore rédigés) :

```markdown
## §N — <titre>

- [ ] <intitulé court> — Strate <1/2/3> — <nouveau|déjà noté dans X|contradiction>
  - Source xmind : <chemin de branche>
  - Détail : <une ou deux phrases>
```

Terminer par une section « Décisions actées à ne pas rouvrir » (les
« à exclure ») et une section « Contradictions à trancher avec Bertrand »
si le point 4 en a produit.

### 6. Rapporter à Bertrand, sans trancher

Résumer en quelques lignes : nombre de nouvelles tâches par chapitre,
nombre de contradictions repérées, et rappeler explicitement que la
todo list attend une validation de cohérence avant tout traitement
séquentiel — ne jamais enchaîner sur la rédaction dans la foulée de ce
skill.

## Garde-fous

- Ne jamais copier une formulation du xmind telle quelle dans le
  manuscrit — seule la todo list méthodologique est mise à jour ici.
- Ne jamais supprimer une entrée de la todo list sans justification
  traçable (rédigée dans le texte, ou décision explicite de Bertrand) —
  en cas de doute, la déplacer en "points de vigilance" plutôt que de
  l'effacer.
- Si le xmind actif a changé de nom de fichier depuis la dernière
  exécution du skill, le signaler — ne pas continuer à comparer contre un
  fichier obsolète silencieusement.
