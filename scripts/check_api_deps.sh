#!/bin/bash
# check_api_deps.sh — Vérifie les mises à jour de contrats producteurs en attente.
# Déclenché par le hook UserPromptSubmit de Claude Code (racine RadioHumaine,
# rôle Consommateur du contrat exposé par simulations/).
# Sortie non vide = Claude interrompt et signale les mises à jour avant de traiter la requête.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPS_FILE="$SCRIPT_DIR/../docs/api_deps.yaml"
[ -f "$DEPS_FILE" ] || exit 0

# Strip guillemets simples et doubles
strip_q() { local v="$1"; v="${v//\"/}"; v="${v//\'/}"; echo "$v"; }

# Résoudre ~ vers $HOME
resolve_p() { echo "${1/#\~/$HOME}"; }

PROJECT_NAME=$(strip_q "$(grep '^project:' "$DEPS_FILE" | sed 's/project:[[:space:]]*//')")

PENDING_OUTPUT=""

current_name=""
changelog_path=""
acked=""

process_producer() {
    [ -z "$current_name" ] || [ -z "$changelog_path" ] || [ -z "$acked" ] && return
    [ -f "$changelog_path" ] || return

    local latest
    latest=$(grep -m1 '^## ' "$changelog_path" | awk '{print $2}')
    [ -z "$latest" ] && return
    [ "$latest" = "$acked" ] && return

    # Extraire les blocs non acquittés contenant [PENDING]
    local block_lines
    block_lines=$(python3 - "$changelog_path" "$acked" "$PROJECT_NAME" <<'PYEOF'
import sys, re

changelog_file = sys.argv[1]
acked_ver      = sys.argv[2]
consumer       = sys.argv[3]

with open(changelog_file) as f:
    content = f.read()

# Découper par blocs "## VERSION ..."
blocks = re.split(r'\n(?=## )', content)

output = []
for block in blocks:
    lines = block.strip().splitlines()
    if not lines:
        continue
    header = lines[0]
    m = re.match(r'^## (\S+)', header)
    if not m:
        continue
    ver = m.group(1)
    if ver == acked_ver:
        break
    if '[PENDING' in header:
        output.append(f"  {header}")
        for l in lines[1:]:
            if l.startswith('- '):
                output.append(f"    {l}")

print('\n'.join(output))
PYEOF
)

    if [ -n "$block_lines" ]; then
        PENDING_OUTPUT+="━━━ ${current_name} : courante=${latest} | acquittée=${acked}\n"
        PENDING_OUTPUT+="${block_lines}\n\n"
    fi
}

while IFS= read -r line || [ -n "$line" ]; do
    if [[ "$line" =~ ^[[:space:]]*-[[:space:]]*name:[[:space:]]*(.+) ]]; then
        process_producer
        current_name=$(strip_q "${BASH_REMATCH[1]}")
        changelog_path=""
        acked=""
    elif [[ "$line" =~ ^[[:space:]]*changelog:[[:space:]]*(.+) ]]; then
        changelog_path=$(resolve_p "$(strip_q "${BASH_REMATCH[1]}")")
    elif [[ "$line" =~ ^[[:space:]]*acked_version:[[:space:]]*(.+) ]]; then
        acked=$(strip_q "${BASH_REMATCH[1]}")
    fi
done < "$DEPS_FILE"
process_producer  # traiter le dernier bloc

if [ -n "$PENDING_OUTPUT" ]; then
    echo "⚠ [API-PENDING] Des mises à jour de contrats producteurs n'ont pas été acquittées :"
    echo ""
    echo -e "$PENDING_OUTPUT"
    echo "→ Traiter ces modifications EN PRIORITÉ avant la requête en cours."
    echo "  Acquittement : adapter le texte du manuscrit + bumper acked_version dans docs/api_deps.yaml"
    echo "  + marquer [ACKED: ${PROJECT_NAME} — $(date +%Y-%m-%d)] dans le CHANGELOG producteur."
fi

exit 0
