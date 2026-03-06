# DeepOrbit /do:init — Copy plugin DeepOrbitPrompt.md to work dir and inject into .gemini/settings.json.
# Windows PowerShell. No Python required.

param([string]$Dest = (Get-Location).Path)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
$ExtensionDir = Join-Path $env:USERPROFILE ".gemini\extensions\deeporbit"

# 1. Find source: plugin's DeepOrbitPrompt.md
$Source = $null
if (Test-Path (Join-Path $RepoRoot "DeepOrbitPrompt.md")) { $Source = Join-Path $RepoRoot "DeepOrbitPrompt.md" }
if (-not $Source -and (Test-Path (Join-Path $ExtensionDir "DeepOrbitPrompt.md"))) { $Source = Join-Path $ExtensionDir "DeepOrbitPrompt.md" }

if (-not $Source) {
  Write-Error "DeepOrbitPrompt.md not found in:`n  - $RepoRoot`n  - $ExtensionDir"
  exit 1
}

# 2. Copy to work dir as DeepOrbitPrompt.md
$DestDir = [System.IO.Path]::GetFullPath($Dest)
if (-not (Test-Path $DestDir)) { New-Item -ItemType Directory -Path $DestDir -Force | Out-Null }
$DestFile = Join-Path $DestDir "DeepOrbitPrompt.md"
Copy-Item -Path $Source -Destination $DestFile -Force
Write-Host "Copied prompt to: $DestFile"

# 3. Create folder structure per DeepOrbitPrompt.md "Structure" section
$vaultDirs = @("00_收件箱", "10_日记", "20_项目", "30_研究", "40_知识库", "50_资源", "60_笔记", "90_计划", "99_系统")
foreach ($d in $vaultDirs) { New-Item -ItemType Directory -Path (Join-Path $DestDir $d) -Force | Out-Null }
@("50_资源\Newsletters", "50_资源\产品发布", "99_系统\模板", "99_系统\提示词", "99_系统\归档") | ForEach-Object {
  New-Item -ItemType Directory -Path (Join-Path $DestDir $_) -Force | Out-Null
}
Write-Host "Created vault folders: 00_收件箱 .. 99_系统, 50_资源/Newsletters, 50_资源/产品发布, 99_系统/模板, 99_系统/提示词, 99_系统/归档"

# 4. Inject DEST\.gemini\settings.json (project-level); create dir if needed
$GeminiDir = Join-Path $DestDir ".gemini"
$SettingsPath = Join-Path $GeminiDir "settings.json"
if (-not (Test-Path $GeminiDir)) { New-Item -ItemType Directory -Path $GeminiDir -Force | Out-Null }

$fileNameList = [System.Collections.ArrayList]@("DeepOrbitPrompt.md")
if (Test-Path $SettingsPath) {
  $json = Get-Content -Path $SettingsPath -Raw -Encoding UTF8
  $obj = $json | ConvertFrom-Json
  if ($obj.context -and $obj.context.fileName) {
    $arr = @($obj.context.fileName)
    foreach ($n in $arr) { if ($n -ne "DeepOrbitPrompt.md") { $fileNameList.Add($n) | Out-Null } }
  }
  if (-not $obj.context) {
    $obj | Add-Member -NotePropertyName context -Value ([PSCustomObject]@{ fileName = @($fileNameList) }) -Force
  } else {
    $obj.context | Add-Member -NotePropertyName fileName -Value @($fileNameList) -Force
  }
} else {
  $obj = [PSCustomObject]@{ context = [PSCustomObject]@{ fileName = @($fileNameList) } }
}

$jsonOut = $obj | ConvertTo-Json -Depth 10
Set-Content -Path $SettingsPath -Value $jsonOut -Encoding UTF8 -NoNewline
Write-Host "Updated context.fileName in $SettingsPath"

Write-Host 'Done. Run "/memory refresh" in Gemini CLI to load DeepOrbitPrompt.md.'
