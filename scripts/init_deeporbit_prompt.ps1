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

# 2.5 Copy deeporbit.json
$ConfigSource = $null
if (Test-Path (Join-Path $RepoRoot "deeporbit.json")) { $ConfigSource = Join-Path $RepoRoot "deeporbit.json" }
if (-not $ConfigSource -and (Test-Path (Join-Path $ExtensionDir "deeporbit.json"))) { $ConfigSource = Join-Path $ExtensionDir "deeporbit.json" }

if ($ConfigSource) {
  $DestConfig = Join-Path $DestDir "deeporbit.json"
  Copy-Item -Path $ConfigSource -Destination $DestConfig -Force
  Write-Host "Copied configuration to: $DestConfig"
  $configJson = Get-Content -Path $DestConfig -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
  Write-Warning "deeporbit.json not found in $RepoRoot or $ExtensionDir. Using fallback defaults."
  $configJson = [PSCustomObject]@{
    folder_mapping = [PSCustomObject]@{
      inbox = "00_收件箱"
      diary = "10_日记"
      projects = "20_项目"
      research = "30_研究"
      wiki = "40_知识库"
      resources = "50_资源"
      notes = "60_笔记"
      plans = "90_计划"
      system = "99_系统"
    }
  }
}

# 3. Create folder structure per deeporbit.json "folder_mapping"
$m = $configJson.folder_mapping
$vaultDirs = @($m.inbox, $m.diary, $m.projects, $m.research, $m.wiki, $m.resources, $m.notes, $m.plans, $m.system)
foreach ($d in $vaultDirs) { New-Item -ItemType Directory -Path (Join-Path $DestDir $d) -Force | Out-Null }
@("$($m.resources)\Newsletters", "$($m.resources)\产品发布", "$($m.resources)\新闻", "$($m.system)\模板", "$($m.system)\提示词", "$($m.system)\归档") | ForEach-Object {
  New-Item -ItemType Directory -Path (Join-Path $DestDir $_) -Force | Out-Null
}
Write-Host "Created vault folders based on configuration."

# 4. Copy plugin 99_系统 contents into DEST\system_folder (even if it already exists — overlay)
$PluginRoot = Split-Path -Parent $Source
$Sys99Source = Join-Path $PluginRoot "99_系统"
if (Test-Path $Sys99Source) {
  $Sys99Dest = Join-Path $DestDir $m.system
  Get-ChildItem -Path $Sys99Source -Force | Copy-Item -Destination $Sys99Dest -Recurse -Force
  Write-Host "Copied $Sys99Source contents (templates, etc.) from plugin into $Sys99Dest"
}

# 5. Inject DEST\.gemini\settings.json (project-level); create dir if needed
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
