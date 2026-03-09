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

# 2.5 Copy deeporbit.json
CONFIG_SOURCE=""
[[ -f "$REPO_ROOT/deeporbit.json" ]] && CONFIG_SOURCE="$REPO_ROOT/deeporbit.json"
[[ -z "$CONFIG_SOURCE" && -f "$EXTENSION_DIR/deeporbit.json" ]] && CONFIG_SOURCE="$EXTENSION_DIR/deeporbit.json"

if [[ -n "$CONFIG_SOURCE" ]]; then
  cp "$CONFIG_SOURCE" "$DEST/deeporbit.json"
  echo "Copied configuration to: $DEST/deeporbit.json"
else
  echo "Warning: deeporbit.json not found. Using fallback defaults."
  echo '{"folder_mapping":{"inbox":"00_收件箱","diary":"10_日记","projects":"20_项目","research":"30_研究","wiki":"40_知识库","resources":"50_资源","notes":"60_笔记","plans":"90_计划","system":"99_系统"}}' > "$DEST/deeporbit.json"
fi

# 3. Create folder structure per deeporbit.json
if command -v jq &>/dev/null; then
  DIR_INBOX=$(jq -r '.folder_mapping.inbox' "$DEST/deeporbit.json")
  DIR_DIARY=$(jq -r '.folder_mapping.diary' "$DEST/deeporbit.json")
  DIR_PROJECTS=$(jq -r '.folder_mapping.projects' "$DEST/deeporbit.json")
  DIR_RESEARCH=$(jq -r '.folder_mapping.research' "$DEST/deeporbit.json")
  DIR_WIKI=$(jq -r '.folder_mapping.wiki' "$DEST/deeporbit.json")
  DIR_RESOURCES=$(jq -r '.folder_mapping.resources' "$DEST/deeporbit.json")
  DIR_NOTES=$(jq -r '.folder_mapping.notes' "$DEST/deeporbit.json")
  DIR_PLANS=$(jq -r '.folder_mapping.plans' "$DEST/deeporbit.json")
  DIR_SYSTEM=$(jq -r '.folder_mapping.system' "$DEST/deeporbit.json")
else
  # Hardcoded fallback if jq is missing
  DIR_INBOX="00_收件箱"
  DIR_DIARY="10_日记"
  DIR_PROJECTS="20_项目"
  DIR_RESEARCH="30_研究"
  DIR_WIKI="40_知识库"
  DIR_RESOURCES="50_资源"
  DIR_NOTES="60_笔记"
  DIR_PLANS="90_计划"
  DIR_SYSTEM="99_系统"
fi

VAULT_DIRS="$DIR_INBOX $DIR_DIARY $DIR_PROJECTS $DIR_RESEARCH $DIR_WIKI $DIR_RESOURCES $DIR_NOTES $DIR_PLANS $DIR_SYSTEM"
for d in $VAULT_DIRS; do mkdir -p "$DEST/$d"; done
mkdir -p "$DEST/$DIR_RESOURCES/Newsletters" "$DEST/$DIR_RESOURCES/产品发布" "$DEST/$DIR_RESOURCES/新闻"
mkdir -p "$DEST/$DIR_SYSTEM/模板" "$DEST/$DIR_SYSTEM/提示词" "$DEST/$DIR_SYSTEM/归档"
echo "Created vault folders based on configuration."

# 4. Copy plugin 99_系统 contents into DEST/$DIR_SYSTEM (even if it already exists — overlay)
PLUGIN_ROOT="$(dirname "$SOURCE")"
if [[ -d "$PLUGIN_ROOT/99_系统" ]]; then
  mkdir -p "$DEST/$DIR_SYSTEM"
  cp -r "$PLUGIN_ROOT/99_系统/"* "$DEST/$DIR_SYSTEM/" 2>/dev/null || true
  echo "Copied 99_系统 contents (templates, etc.) from plugin into $DEST/$DIR_SYSTEM"
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
