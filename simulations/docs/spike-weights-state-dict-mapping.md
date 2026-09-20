# Spike — weights : le state_dict HuggingFace de BERT s'aligne-t-il sur nos modules ?

Branche : explore/weights-state-dict-mapping
Date : 2026-08-14

## Question

Le `state_dict` HuggingFace d'un modèle BERT standard (clés du type
`encoder.layer.N.attention.self.query.weight`, `...key.weight`,
`...value.weight`, `...output.dense.weight`, chacune de forme `(out, in)`
comme tout `nn.Linear`) s'aligne-t-il directement — sans table de
correspondance ni transformation de forme — sur ce qu'attend
`ComplexLinear.fc_real` (un `nn.Linear` par projection Q/K/V/out) ?

## Contraintes identifiées a priori

- `nn.Linear` stocke `weight` en forme `(out_features, in_features)` et
  calcule `y = x @ weight.T + bias` — l'injection doit copier directement
  (pas de transposition supplémentaire, sinon bug silencieux constaté
  pendant la Phase 1 sur `test_u01_hermiticity_hand_n2`, cf. `DevPlan.md`).
- `transformers` n'a jamais été utilisé dans ce projet (déclenche la règle
  spike du `CLAUDE.md`).
- Remarque de Bertrand (2026-08-14) : valider d'abord la logique de
  correspondance sur des coefficients fabriqués à la main en petite
  dimension, avant de dépendre du Hub HuggingFace / du réseau — isole la
  question "la logique de mapping est-elle correcte" de la question
  "le téléchargement fonctionne-t-il".

## Protocole de test minimal

- [ ] Vérification 1 (sans réseau, sans `transformers`) : construire à la
  main un `state_dict` synthétique en petite dimension (`in=4, out=4`)
  reproduisant exactement les noms de clés BERT réels
  (`query.weight`, `query.bias`, `key.weight`, `key.bias`,
  `value.weight`, `value.bias`, `output.dense.weight`,
  `output.dense.bias`), avec des valeurs choisies à la main. Écrire la
  fonction de correspondance (`WeightProjector` minimal) qui copie
  `query.weight` → `q_proj.fc_real.weight`, etc., et vérifier
  numériquement (`torch.equal` ou `allclose` à tolérance nulle) que les
  valeurs copiées sont identiques aux valeurs sources, sans transposition
  erronée (test explicite avec une matrice non symétrique pour détecter
  une inversion accidentelle).
- [ ] Vérification 2 (réseau, `transformers`, dans un environnement isolé
  du reste du projet) : charger réellement `prajjwal1/bert-tiny` via
  `AutoModel.from_pretrained`, lister les clés de `model.state_dict()`
  pour une couche d'attention, et confirmer qu'elles suivent exactement
  le même motif de noms que le `state_dict` synthétique de la
  Vérification 1 (mêmes suffixes, même convention de forme).
- [ ] Vérification 3 (si écart détecté) : si les noms/formes réels
  diffèrent du motif supposé, documenter l'écart exact et évaluer si une
  table de correspondance minimale suffit ou si c'est bloquant.

## Résultat

- Réponse : OUI, avec une contrainte d'implémentation.
- Vérification 1 (coefficients synthétiques, sans réseau) : verte. La
  correspondance directe nom-à-nom (`query.weight` → `q_proj.fc_real.weight`,
  etc., copie sans transposition) reproduit exactement les valeurs sources,
  y compris sur une matrice non symétrique (élimine le risque d'inversion
  accidentelle `weight` / `weight.T` déjà rencontré en Phase 1).
- Vérification 2 (réseau, `transformers==5.15.0` installé pour ce spike) :
  **`AutoModel.from_pretrained("prajjwal1/bert-tiny")` échoue** —
  `ValueError: Unrecognized model in prajjwal1/bert-tiny. Should have a
  model_type key in its config.json.` Le `config.json` de ce checkpoint
  (ancien, non maintenu depuis) ne définit pas `model_type`, requis par les
  versions récentes de `transformers` pour la résolution `Auto*`.
  Contournement testé et vert : `BertModel.from_pretrained(...)` explicite
  (bypass la résolution `Auto*`, charge directement l'architecture connue).
  Les clés obtenues (`encoder.layer.0.attention.self.{query,key,value}.weight/bias`,
  `encoder.layer.0.attention.output.dense.weight/bias`, formes `(128,128)`/`(128,)`)
  suivent exactement le motif supposé en Vérification 1 — pas de table de
  correspondance nécessaire.
  Vérifié séparément : `bert-base-uncased` (cible réelle Phase 2) a bien
  `model_type: "bert"` dans son `config.json` — `AutoModel.from_pretrained`
  fonctionnerait directement sur ce checkpoint sans ce contournement.
- Contrainte découverte : les checkpoints BERT anciens/tiers (ex.
  `prajjwal1/bert-tiny`) peuvent avoir un `config.json` incompatible avec
  `AutoModel` sous des versions récentes de `transformers` — pas un
  problème de mapping de poids, un problème de résolution de classe.
- Impact sur le design : `WeightProjector` doit instancier `BertModel`
  explicitement (pas `AutoModel`), pour rester robuste aux deux
  checkpoints (`bert-tiny` pour le debug rapide, `bert-base-uncased` pour
  la Phase 2 citable) sans branche de code conditionnelle.
- Condition de succès pour le feat : correspondance nom-à-nom directe,
  chargement via `BertModel.from_pretrained` (pas `AutoModel`).

## Décision

- [x] Le feat peut démarrer tel que spécifié, avec l'adaptation mineure
  ci-dessus (`BertModel` explicite plutôt que `AutoModel`).
- [ ] Le feat nécessite une adaptation plus large
- [ ] Bloquer — contrainte insurmontable dans le scope actuel

## Note d'environnement

`transformers` installé dans `.venv` pour ce spike : `transformers==5.15.0`
(+ dépendances : `huggingface-hub==1.27.0`, `tokenizers==0.22.2`,
`safetensors==0.8.0`). Non encore figé dans un fichier de lock — la Phase 0
(`docs/TODO.md`) reste à compléter sur ce point avant la Phase 2.
