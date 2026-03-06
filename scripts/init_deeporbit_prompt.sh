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

# 3. Create folder structure per DeepOrbitPrompt.md "Structure" section
VAULT_DIRS="00_收件箱 10_日记 20_项目 30_研究 40_知识库 50_资源 60_笔记 90_计划 99_系统"
for d in $VAULT_DIRS; do mkdir -p "$DEST/$d"; done
mkdir -p "$DEST/50_资源/Newsletters" "$DEST/50_资源/产品发布"
mkdir -p "$DEST/99_系统/模板" "$DEST/99_系统/提示词" "$DEST/99_系统/归档"
echo "Created vault folders: $VAULT_DIRS, 50_资源/Newsletters, 50_资源/产品发布, 99_系统/模板, 99_系统/提示词, 99_系统/归档"

# 4. Inject DEST/.gemini/settings.json (project-level); create dir if needed
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
