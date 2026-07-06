$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$ThirdParty = Join-Path $Root "third_party"
$RepoZip = Join-Path $ThirdParty "Dolphin-master.zip"
$RepoDir = Join-Path $ThirdParty "Dolphin-master"
$ModelDir = Join-Path $Root "models\dolphin-v2"

New-Item -ItemType Directory -Force -Path $ThirdParty, $ModelDir | Out-Null

if (-not (Test-Path $RepoZip)) {
  Invoke-WebRequest `
    -Uri "https://github.com/bytedance/Dolphin/archive/refs/heads/master.zip" `
    -OutFile $RepoZip `
    -TimeoutSec 120
}

if (-not (Test-Path $RepoDir)) {
  Expand-Archive -LiteralPath $RepoZip -DestinationPath $ThirdParty -Force
}

python -m pip install qwen-vl-utils
hf download ByteDance/Dolphin-v2 `
  --local-dir $ModelDir `
  --include "*.json" "*.txt" "*.md" "*.safetensors"

Write-Host "Dolphin repository: $RepoDir"
Write-Host "Dolphin model:      $ModelDir"
Write-Host "Set DOLPHIN_REPO_DIR / DOLPHIN_MODEL_DIR only if you move these folders."
