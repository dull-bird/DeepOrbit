# Fetch content from URLs listed in a diary's "## News sources" section, or from args.
# Usage: .\fetch_news_sources.ps1 <path-to-diary.md> [output-dir]
#    OR  .\fetch_news_sources.ps1 <url1> [url2 ...]

param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$InputItems
)

$TimeoutSec = 30
$UserAgent = "Mozilla/5.0 (compatible; DeepOrbit/1.0; +https://github.com/dull-bird/DeepOrbit)"

function Get-UrlsFromDiary {
  param([string]$Path)
  $content = Get-Content -Path $Path -Raw -Encoding UTF8
  $inSection = $false
  $urls = [System.Collections.ArrayList]@()
  foreach ($line in ($content -split "`n")) {
    if ($line -match '^##\s+News\s+sources') { $inSection = $true; continue }
    if (-not $inSection) { continue }
    if ($line -match '^##\s') { break }
    if ([string]::IsNullOrWhiteSpace($line) -or $line -match '^\s*#') { continue }
    if ($line -match '\((https?://[^\)]+)\)') { $urls.Add($Matches[1]) | Out-Null }
    elseif ($line -match '(https?://\S+)') { $urls.Add($Matches[1]) | Out-Null }
  }
  $urls
}

function Fetch-One {
  param([string]$Url, [string]$OutDir)

  if ([string]::IsNullOrWhiteSpace($OutDir) -or -not (Test-Path -LiteralPath $OutDir)) {
    Write-Host "=== $Url ==="
    try {
      $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSec -MaximumRedirection 5 `
        -UserAgent $UserAgent -Headers @{ "Accept" = "text/html, application/xml, application/rss+xml, */*" }
      Write-Output $r.Content
    } catch {
      Write-Host "[fetch failed: $Url]"
    }
    Write-Host ""
    return
  }

  try {
    $uri = [System.Uri]$Url
    $domain = $uri.Host
  } catch {
    $domain = "unknown"
  }

  $safeName = $domain -replace '[^a-zA-Z0-9]', '_'
  $outFile = Join-Path $OutDir "$safeName.txt"
  $counter = 1
  while (Test-Path -LiteralPath $outFile) {
    $outFile = Join-Path $OutDir "${safeName}_${counter}.txt"
    $counter++
  }

  Write-Host "=== URL: $Url ==="
  Write-Host "Saving to: $outFile"

  try {
    $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSec -MaximumRedirection 5 `
      -UserAgent $UserAgent -Headers @{ "Accept" = "text/html, application/xml, application/rss+xml, */*" }
    Set-Content -Path $outFile -Value $r.Content -Encoding UTF8
  } catch {
    Set-Content -Path $outFile -Value "[fetch failed: $Url]" -Encoding UTF8
  }
  Write-Host "Status: Done"
  Write-Host ""
}

if (-not $InputItems -or $InputItems.Count -eq 0) {
  Write-Error "Usage: .\fetch_news_sources.ps1 <diary.md> [output-dir] OR .\fetch_news_sources.ps1 <url1> [url2 ...]"
  exit 1
}

if (Test-Path -LiteralPath $InputItems[0] -PathType Leaf) {
  $urls = Get-UrlsFromDiary -Path $InputItems[0]
  $outDir = ""
  if ($InputItems.Count -gt 1 -and (Test-Path -LiteralPath $InputItems[1] -PathType Container)) {
    $outDir = $InputItems[1]
  }
  foreach ($u in $urls) { Fetch-One -Url $u -OutDir $outDir }
} else {
  foreach ($u in $InputItems) { Fetch-One -Url $u -OutDir "" }
}
