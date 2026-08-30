# Wrapper so Windows PowerShell can run graphify without a global install on PATH.
# From the repo root:
#   .\scripts\graphify.ps1 query "How does analyze work?"
#   .\scripts\graphify.ps1 update .
# macOS/Linux: ./scripts/graphify.sh

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

$exe = Join-Path $Root ".venv\Scripts\graphify.exe"
if (-not (Test-Path $exe)) {
  Write-Host "graphify not found at $exe"
  Write-Host "Create the venv and install graphify first:"
  Write-Host "  python -m venv .venv"
  Write-Host "  .\.venv\Scripts\Activate.ps1"
  Write-Host "  pip install graphifyy"
  exit 1
}

& $exe @args
exit $LASTEXITCODE
