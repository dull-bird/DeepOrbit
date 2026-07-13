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

# 2. Copy defaults without overwriting user customizations
mkdir -p "$DEST"
if [[ ! -f "$DEST/DeepOrbitPrompt.md" ]]; then
  cp "$SOURCE" "$DEST/DeepOrbitPrompt.md"
  echo "Copied prompt to: $DEST/DeepOrbitPrompt.md"
else
  echo "Preserved existing prompt: $DEST/DeepOrbitPrompt.md"
fi

# 2.5 Copy deeporbit.json context file
CONFIG_SOURCE=""
[[ -f "$REPO_ROOT/deeporbit.json" ]] && CONFIG_SOURCE="$REPO_ROOT/deeporbit.json"
[[ -z "$CONFIG_SOURCE" && -f "$EXTENSION_DIR/deeporbit.json" ]] && CONFIG_SOURCE="$EXTENSION_DIR/deeporbit.json"

if [[ -n "$CONFIG_SOURCE" && ! -f "$DEST/deeporbit.json" ]]; then
  cp "$CONFIG_SOURCE" "$DEST/deeporbit.json"
  echo "Copied configuration to: $DEST/deeporbit.json"
fi

# 3. Create folder structure
DIR_INBOX="00_Inbox"
DIR_DIARY="10_Diary"
DIR_WRITINGS="15_Writings"
DIR_PROJECTS="20_Projects"
DIR_RESEARCH="30_Research"
DIR_WIKI="40_Wiki"
DIR_RESOURCES="50_Resources"
DIR_NOTES="60_Notes"
DIR_PLANS="90_Plans"
DIR_SYSTEM="99_System"

VAULT_DIRS="$DIR_INBOX $DIR_DIARY $DIR_WRITINGS $DIR_PROJECTS $DIR_RESEARCH $DIR_WIKI $DIR_RESOURCES $DIR_NOTES $DIR_PLANS $DIR_SYSTEM"
for d in $VAULT_DIRS; do mkdir -p "$DEST/$d"; done

mkdir -p "$DEST/$DIR_RESOURCES/Newsletters" "$DEST/$DIR_RESOURCES/Product_Launches" "$DEST/$DIR_RESOURCES/News"
mkdir -p "$DEST/$DIR_SYSTEM/Templates" "$DEST/$DIR_SYSTEM/Prompts" "$DEST/$DIR_SYSTEM/Archive" "$DEST/$DIR_SYSTEM/Bases" "$DEST/$DIR_SYSTEM/Calendar"
echo "Created vault folders based on configuration."

# Use the v2 core for conflict-aware localized-folder migration and config upgrades.
if [[ -d "$REPO_ROOT/src/deeporbit" ]]; then
  PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}" python3 -m deeporbit --vault "$DEST" init || {
    echo "Warning: DeepOrbit core reported migration conflicts; review the JSON above." >&2
  }
fi

# 4. Copy plugin system contents into DEST/$DIR_SYSTEM (even if it already exists — overlay)
PLUGIN_ROOT="$(dirname "$SOURCE")"

PLUGIN_SYS_NAME="99_System"

if [[ -d "$PLUGIN_ROOT/$PLUGIN_SYS_NAME" ]]; then
  mkdir -p "$DEST/$DIR_SYSTEM"
  cp -rn "$PLUGIN_ROOT/$PLUGIN_SYS_NAME/"* "$DEST/$DIR_SYSTEM/" 2>/dev/null || true
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

# 6. Ensure gemini-obsidian extension dependencies are installed
OBSIDIAN_EXT_DIR="$HOME/.gemini/extensions/gemini-obsidian"
if [[ -d "$OBSIDIAN_EXT_DIR" && -f "$OBSIDIAN_EXT_DIR/package.json" ]]; then
  LANCEDB_MOD="$OBSIDIAN_EXT_DIR/node_modules/@lancedb/lancedb"
  if [[ ! -d "$LANCEDB_MOD" ]]; then
    echo "Installing gemini-obsidian extension dependencies (missing @lancedb/lancedb)..."
    (cd "$OBSIDIAN_EXT_DIR" && npm install --silent)
    echo "gemini-obsidian dependencies installed."
  else
    echo "gemini-obsidian extension dependencies OK."
  fi
fi

echo "Done. Run \"/memory refresh\" in Gemini CLI to load DeepOrbitPrompt.md."
