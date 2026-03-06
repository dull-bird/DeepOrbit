#!/usr/bin/env bash
# Fetch content from URLs listed in a diary's "## News sources" section, or from args.
# Usage: fetch_news_sources.sh <path-to-diary.md>   OR   fetch_news_sources.sh <url1> [url2 ...]
# Output: for each URL, "=== <url> ===\n<raw body>\n"; stderr for skips/errors. Uses curl (timeout 30s, retry 2).
set -e

CURL_TIMEOUT=30
CURL_RETRY=2
UA="Mozilla/5.0 (compatible; DeepOrbit/1.0; +https://github.com/dull-bird/DeepOrbit)"

# Extract URLs from markdown: lines under "## News sources" until next ## or EOF; accept bare URL or [text](url)
extract_urls_from_diary() {
  local file="$1"
  local in_section=0
  while IFS= read -r line; do
    if [[ "$line" =~ ^##[[:space:]]+News[[:space:]]+sources ]]; then
      in_section=1
      continue
    fi
    [[ "$in_section" == 0 ]] && continue
    [[ "$line" =~ ^##[[:space:]] ]] && break
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
    # Bare URL or [text](url)
    if [[ "$line" =~ \(https?://[^\)]+\) ]]; then
      echo "$line" | sed -n 's/.*(\(https\?:\/\/[^)]*\)).*/\1/p'
    elif [[ "$line" =~ https?:// ]]; then
      echo "$line" | grep -oE 'https?://[^[:space:]]+' | head -1
    fi
  done < "$file"
}

fetch_one() {
  local url="$1"
  echo "=== $url ==="
  curl -sL -m "$CURL_TIMEOUT" --retry "$CURL_RETRY" --retry-delay 1 \
    -H "User-Agent: $UA" -H "Accept: text/html, application/xml, application/rss+xml, */*" \
    "$url" 2>/dev/null || echo "[fetch failed: $url]"
  echo ""
}

if [[ $# -eq 0 ]]; then
  echo "Usage: $0 <diary.md>  OR  $0 <url1> [url2 ...]" >&2
  exit 1
fi

if [[ -f "$1" ]]; then
  urls=()
  while IFS= read -r u; do [[ -n "$u" ]] && urls+=("$u"); done < <(extract_urls_from_diary "$1")
  for u in "${urls[@]}"; do fetch_one "$u"; done
else
  for u in "$@"; do fetch_one "$u"; done
fi
