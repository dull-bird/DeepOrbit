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

# 2.5 Copy deeporbit.json context file
$ConfigSource = $null
if (Test-Path (Join-Path $RepoRoot "deeporbit.json")) { $ConfigSource = Join-Path $RepoRoot "deeporbit.json" }
if (-not $ConfigSource -and (Test-Path (Join-Path $ExtensionDir "deeporbit.json"))) { $ConfigSource = Join-Path $ExtensionDir "deeporbit.json" }

if ($ConfigSource) {
  $DestConfig = Join-Path $DestDir "deeporbit.json"
  Copy-Item -Path $ConfigSource -Destination $DestConfig -Force
  Write-Host "Copied configuration to: $DestConfig"
} else {
  New-Item -ItemType File -Path (Join-Path $DestDir "deeporbit.json") -Force | Out-Null
}

# 3. Create folder structure
$DirInbox = "00_Inbox"
$DirDiary = "10_Diary"
$DirProjects = "20_Projects"
$DirResearch = "30_Research"
$DirWiki = "40_Wiki"
$DirResources = "50_Resources"
$DirNotes = "60_Notes"
$DirPlans = "90_Plans"
$DirSystem = "99_System"

$vaultDirs = @($DirInbox, $DirDiary, $DirProjects, $DirResearch, $DirWiki, $DirResources, $DirNotes, $DirPlans, $DirSystem)
foreach ($d in $vaultDirs) { New-Item -ItemType Directory -Path (Join-Path $DestDir $d) -Force | Out-Null }
@("$DirResources\Newsletters", "$DirResources\产品发布", "$DirResources\新闻", "$DirSystem\模板", "$DirSystem\提示词", "$DirSystem\归档") | ForEach-Object {
  New-Item -ItemType Directory -Path (Join-Path $DestDir $_) -Force | Out-Null
}
Write-Host "Created vault folders."

# 4. Copy plugin system contents into DEST\system_folder (even if it already exists — overlay)
$PluginRoot = Split-Path -Parent $Source
$PluginSysName = "99_System"

$SysSource = Join-Path $PluginRoot $PluginSysName
if (Test-Path $SysSource) {
  $SysDest = Join-Path $DestDir $DirSystem
  Get-ChildItem -Path $SysSource -Force | Copy-Item -Destination $SysDest -Recurse -Force
  Write-Host "Copied $SysSource contents (templates, etc.) from plugin into $SysDest"
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
