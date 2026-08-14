#!/usr/bin/env bash
# release.sh — Procédure de release pour le projet simulations (PyTorch/ML).
# Usage : ./scripts/release.sh <version>
# Exemple : ./scripts/release.sh 0.2.0

set -euo pipefail

VERSION="${1:-}"
DATE=$(date +%Y-%m-%d)

if [[ -z "$VERSION" ]]; then
  echo "Usage: $0 <version>"
  echo "Exemple: $0 0.2.0"
  exit 1
fi

echo "=== Release v${VERSION} — ${DATE} ==="

# 1. Vérifier état du dépôt
if [[ -n "$(git status --porcelain)" ]]; then
  echo "ERREUR : des fichiers non commités existent. Commit ou stash avant de releaser."
  git status --short
  exit 1
fi

# 2. Vérifier que le tag n'existe pas déjà
if git rev-parse "v${VERSION}" >/dev/null 2>&1; then
  echo "ERREUR : le tag v${VERSION} existe déjà."
  exit 1
fi

echo ""
echo "Rappels avant de continuer (non automatisés par ce script) :"
echo "  - Tous les runs cités dans cette version sont-ils reproductibles"
echo "    (config + seed + résultat archivés) ?"
echo "  - RELEASES.md a-t-il été mis à jour avec le changelog de la version ?"
echo "  - docs/TODO.md a-t-il été archivé (items résolus déplacés) ?"
echo "  - Si des résultats cités changent : Simulations_API.md et"
echo "    Simulations_API_CHANGELOG.md ont-ils été bumpés dans le même commit ?"
echo ""
read -rp "Confirmer que ces points sont traités (o/N) : " CONFIRM
if [[ "$CONFIRM" != "o" && "$CONFIRM" != "O" ]]; then
  echo "Release annulée."
  exit 1
fi

# 3. Commit de release
echo "Création du commit de release..."
git add -u
git commit -m "release: v${VERSION}"

# 4. Tag git
echo "Création du tag v${VERSION}..."
git tag "v${VERSION}"

echo ""
echo "=== Release v${VERSION} préparée ==="
echo "Tag créé : v${VERSION}"
echo ""
echo "Pour pousser (non automatique) :"
echo "  git push origin HEAD"
echo "  git push origin v${VERSION}"
