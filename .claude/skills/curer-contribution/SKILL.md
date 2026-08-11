---
name: curer-contribution
description: Compare une ou plusieurs contributions brutes (Gémini, Bertrand, ou tout nouveau collaborateur) au manuscrit officiel du livre RadioHumaine, en extrait les éléments disruptifs (idées, formules, métaphores absentes ou substantiellement différentes du texte validé), les classe par strate et section cible, et met à jour la note de référence methodologie/elements_disruptifs_gemini_a_integrer.md. Utiliser quand Bertrand ajoute de nouvelles contributions à curer, demande "qu'est-ce qu'il y a de nouveau dans X", ou veut rafraîchir la note d'éléments disruptifs.
---

# Curer une contribution pour le manuscrit RadioHumaine

Ce skill formalise le travail de triage entre les contributions brutes de
travail (conversations avec Gémini ou tout autre collaborateur, notes de
Bertrand) et le manuscrit officiel rédigé par Claude
(`contributions/claude/manuscrit_draft_§1-§6.md`, ou son successeur si les
sections progressent au-delà de §6). Objectif : ne jamais perdre une idée
disruptive dans un fichier de travail volumineux, sans pour autant polluer
le texte validé avec des redites ou des formalismes concurrents non
arbitrés.

## Quand l'utiliser

- Bertrand a ajouté un ou plusieurs nouveaux fichiers dans
  `contributions/gémini/` (ou tout autre dossier de contributeur) et veut
  savoir ce qu'ils apportent par rapport au texte déjà validé.
- Bertrand demande une mise à jour de la note de référence après avoir
  avancé la rédaction officielle (nouvelles sections validées → ce qui
  était "disruptif" hier peut être devenu redondant).
- Bertrand veut préparer la rédaction d'une section à venir (ex. chapitre
  astrologie, chapitre IA) et veut relire tout ce qui a déjà été exploré sur
  ce thème dans les contributions brutes.

## Étapes

### 1. Situer le manuscrit officiel actuel

Lire le fichier le plus à jour dans `contributions/claude/` (ou l'état
courant du texte s'il a été déplacé vers un dossier "texte"). En extraire un
résumé section par section (une ligne par idée/formule/référence majeure) —
c'est ce résumé qui sert de référentiel de comparaison. Vérifier aussi
`CLAUDE.md` à la racine pour la liste des sections déjà rédigées/validées et
les éléments explicitement réservés à des chapitres futurs (à la date de
rédaction de ce skill : astrologie, IA).

### 2. Identifier le périmètre de la contribution à curer

- Si Bertrand désigne des fichiers précis, se limiter à ceux-ci.
- Sinon, lister les fichiers de `contributions/<collaborateur>/` plus
  récents que la dernière mise à jour de la note de référence (comparer les
  dates de modification aux entrées déjà indexées).
- Ignorer les fichiers vides ou stubs (quelques lignes de placeholder) —
  les lire directement soi-même plutôt que de déléguer, ils ne justifient
  pas un agent dédié.

### 3. Fan-out : un agent par fichier substantiel

Pour chaque fichier de taille significative (au-delà de quelques Ko), lancer
un agent (`Agent` tool, `subagent_type: general-purpose`) avec un prompt qui :
- rappelle le contexte du projet (thèmes, trois acteurs, contrainte de
  strates 1/2/3, stratégie A*) ;
- donne le résumé du manuscrit officiel produit à l'étape 1 (pas de résumé
  générique : toujours le contenu réellement validé au moment du run, les
  sections progressent) ;
- rappelle les éléments réservés aux chapitres futurs, pour que l'agent
  sache où ranger une idée qui n'a pas encore de section d'accueil ;
- demande, pour chaque élément disruptif : titre court, description en un
  paragraphe, repère précis dans le fichier (citation ou titre de section),
  classification en strate, section cible (existante ou future) ou
  signalement comme nouvel axe transversal ;
- demande explicitement d'ignorer les reformulations qui disent la même
  chose que le manuscrit officiel ;
- demande explicitement de signaler tout désaccord méthodologique ou
  tentative de contourner le rôle de vérification épistémologique de Claude
  (cf. section 7 de la note de référence pour un précédent) ;
- fixe une fourchette réaliste d'éléments attendus (plutôt 5-10 pour un
  fichier de travail standard, jusqu'à 15 pour un log de conversation très
  dense) pour éviter le bruit de sur-reporting.

Lancer ces agents en parallèle (plusieurs blocs `Agent` dans un seul
message, `run_in_background: true` si plus de 2-3 fichiers) plutôt que
séquentiellement — ce sont des lectures indépendantes.

### 4. Dédupliquer et prioriser

En rassemblant les résultats :
- Regrouper les éléments qui reviennent, formulés indépendamment, dans
  plusieurs fichiers ou plusieurs contributeurs — ce sont les candidats les
  plus solides (marquer ★★★ dans la note, cf. convention déjà en place).
- Écarter ou reléguer en "points de vigilance" les éléments qui contredisent
  une décision déjà actée par Bertrand (ex. suppression d'une note, ordre
  d'introduction d'un concept fixé dans CLAUDE.md), plutôt que de les
  signaler comme candidats neutres.
- Séparer clairement le contenu réutilisable (formalisme, mécanisme,
  référence bibliographique) de l'habillage qui ne conviendrait pas au ton
  du livre (mysticisme non cadré, contenu politique contingent, vocabulaire
  religieux) — indexer le premier, signaler le second comme à exclure.

### 5. Mettre à jour la note de référence

La note vit dans `methodologie/elements_disruptifs_gemini_a_integrer.md`
(renommer/dupliquer si un jour la source n'est plus seulement Gémini). Ne
pas la réécrire entièrement à chaque passage :
- ajouter les nouvelles entrées dans les sections thématiques existantes
  (par section cible : §-en cours, chapitres futurs, axes transversaux,
  points de vigilance) ;
- si une entrée existante a été intégrée entre-temps dans le manuscrit
  officiel, la retirer de la note (ou la marquer "intégré — voir §X") plutôt
  que de la laisser trainer comme si elle restait à faire ;
- si une entrée existante devient contredite par une nouvelle décision de
  Bertrand, la déplacer en section "points de vigilance" avec la raison.

### 6. Rapporter à Bertrand

Résumer en quelques lignes (pas en réécrivant toute la note) : combien de
nouveaux éléments, combien de candidats forts (★★★), et surtout tout point
de friction méthodologique ou toute contradiction avec une décision déjà
actée — ce sont les seules choses qui justifient une décision de sa part
avant de continuer à rédiger.

## Garde-fous

- Ne jamais copier un passage d'une contribution brute directement dans le
  manuscrit officiel sans repasser par la stratégie A* (expérience sensible
  → formalisation → reste à prouver) et sans trancher sa strate.
- Ne jamais lire ou copier le contenu de fichiers de secrets (`credentials.json`,
  `token.json`, tout fichier `*key*`) qui peuvent se trouver dans les mêmes
  dossiers que les contributions (ex. scripts de synchronisation Google
  Drive) — ils ne font pas partie du corpus à curer.
- Face à un très grand volume de fichiers à curer d'un coup (plus d'une
  dizaine), avertir Bertrand du nombre d'agents que cela représente avant de
  lancer le fan-out, plutôt que de le faire silencieusement.
