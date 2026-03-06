#!/usr/bin/env bash
# DeepOrbit /do:init — Copy plugin DeepOrbitPrompt.md to work dir and inject into .gemini/settings.json.
# macOS / Linux. No Python required; uses jq for JSON when available.
set -e

DEST="${1:-$PWD}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
EXTENSION_DIR="${HOME}/.gemini/extensions/deeporbit"

# 1. Find source: plugin's DeepOrbitPrompt.md
SOURCE=""
[[ -f "$REPO_ROOT/DeepOrbitPrompt.md" ]] && SOURCE="$REPO_ROOT/DeepOrbitPrompt.md"
[[ -z "$SOURCE" && -f "$EXTENSION_DIR/DeepOrbitPrompt.md" ]] && SOURCE="$EXTENSION_DIR/DeepOrbitPrompt.md"

if [[ -z "$SOURCE" ]]; then
  echo "Error: DeepOrbitPrompt.md not found in:" >&2
  echo "  - $REPO_ROOT" >&2
  echo "  - $EXTENSION_DIR" >&2
  exit 1
fi

# 2. Copy to work dir as DeepOrbitPrompt.md
mkdir -p "$DEST"
cp "$SOURCE" "$DEST/DeepOrbitPrompt.md"
echo "Copied prompt to: $DEST/DeepOrbitPrompt.md"

# 3. Inject DEST/.gemini/settings.json (project-level); create dir if needed
GEMINI_DIR="$DEST/.gemini"
GEMINI_SETTINGS="$GEMINI_DIR/settings.json"
mkdir -p "$GEMINI_DIR"

if command -v jq &>/dev/null; then
  if [[ -f "$GEMINI_SETTINGS" ]]; then
    tmp=$(mktemp)
    jq '
      .context = (.context // {}) |
      .context.fileName = (["DeepOrbitPrompt.md"] + (
        .context.fileName // [] |
        if type == "string" then [.] else . end |
        map(select(. != "DeepOrbitPrompt.md"))
      ))
    ' "$GEMINI_SETTINGS" > "$tmp" && mv "$tmp" "$GEMINI_SETTINGS"
  else
    echo '{"context":{"fileName":["DeepOrbitPrompt.md"]}}' > "$GEMINI_SETTINGS"
  fi
  echo "Updated context.fileName in $GEMINI_SETTINGS"
else
  if [[ ! -f "$GEMINI_SETTINGS" ]]; then
    echo '{"context":{"fileName":["DeepOrbitPrompt.md"]}}' > "$GEMINI_SETTINGS"
    echo "Created $GEMINI_SETTINGS with DeepOrbitPrompt.md"
  else
    echo "Note: install 'jq' to auto-update existing settings. Ensure context.fileName in $GEMINI_SETTINGS includes \"DeepOrbitPrompt.md\"."
  fi
fi

echo 'Done. Run "/memory refresh" in Gemini CLI to load DeepOrbitPrompt.md.'
