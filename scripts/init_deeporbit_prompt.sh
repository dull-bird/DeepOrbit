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

# 2.5 Copy deeporbit.json context file
CONFIG_SOURCE=""
[[ -f "$REPO_ROOT/deeporbit.json" ]] && CONFIG_SOURCE="$REPO_ROOT/deeporbit.json"
[[ -z "$CONFIG_SOURCE" && -f "$EXTENSION_DIR/deeporbit.json" ]] && CONFIG_SOURCE="$EXTENSION_DIR/deeporbit.json"

if [[ -n "$CONFIG_SOURCE" ]]; then
  cp "$CONFIG_SOURCE" "$DEST/deeporbit.json"
  echo "Copied configuration to: $DEST/deeporbit.json"
else
  echo "" > "$DEST/deeporbit.json"
fi

# 3. Create folder structure
DIR_INBOX="00_Inbox"
DIR_DIARY="10_Diary"
DIR_PROJECTS="20_Projects"
DIR_RESEARCH="30_Research"
DIR_WIKI="40_Wiki"
DIR_RESOURCES="50_Resources"
DIR_NOTES="60_Notes"
DIR_PLANS="90_Plans"
DIR_SYSTEM="99_System"

VAULT_DIRS="$DIR_INBOX $DIR_DIARY $DIR_PROJECTS $DIR_RESEARCH $DIR_WIKI $DIR_RESOURCES $DIR_NOTES $DIR_PLANS $DIR_SYSTEM"
for d in $VAULT_DIRS; do mkdir -p "$DEST/$d"; done
mkdir -p "$DEST/$DIR_RESOURCES/Newsletters" "$DEST/$DIR_RESOURCES/产品发布" "$DEST/$DIR_RESOURCES/新闻"
mkdir -p "$DEST/$DIR_SYSTEM/模板" "$DEST/$DIR_SYSTEM/提示词" "$DEST/$DIR_SYSTEM/归档"
echo "Created vault folders based on configuration."

# 4. Copy plugin system contents into DEST/$DIR_SYSTEM (even if it already exists — overlay)
PLUGIN_ROOT="$(dirname "$SOURCE")"

PLUGIN_SYS_NAME="99_System"

if [[ -d "$PLUGIN_ROOT/$PLUGIN_SYS_NAME" ]]; then
  mkdir -p "$DEST/$DIR_SYSTEM"
  cp -r "$PLUGIN_ROOT/$PLUGIN_SYS_NAME/"* "$DEST/$DIR_SYSTEM/" 2>/dev/null || true
  echo "Copied $PLUGIN_SYS_NAME contents (templates, etc.) from plugin into $DEST/$DIR_SYSTEM"
fi

# 5. Inject DEST/.gemini/settings.json (project-level); create dir if needed
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

echo "Done. Run \"/memory refresh\" in Gemini CLI to load DeepOrbitPrompt.md."
