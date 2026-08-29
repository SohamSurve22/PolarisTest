# Pulls local Ollama models used by PolarisLex (Windows, no Homebrew).
# Run from the repo root in PowerShell:
#   Set-ExecutionPolicy -Scope Process Bypass
#   .\scripts\setup-ollama.ps1

$ErrorActionPreference = "Stop"

$models = @(
  "nomic-embed-text",
  "qwen2.5:7b-instruct-q4_K_M"
)

function Test-Ollama {
  return [bool](Get-Command ollama -ErrorAction SilentlyContinue)
}

if (-not (Test-Ollama)) {
  Write-Host "Ollama is not on PATH. Installing with winget if available..."
  $winget = Get-Command winget -ErrorAction SilentlyContinue
  if ($winget) {
    winget install --id Ollama.Ollama -e --accept-package-agreements --accept-source-agreements
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
      [System.Environment]::GetEnvironmentVariable("Path", "User")
  }
  if (-not (Test-Ollama)) {
    Write-Host "Install Ollama from https://ollama.com/download/windows then re-run this script."
    Write-Host "Use the Windows installer (not WSL). Docker Desktop reaches it at host.docker.internal:11434."
    exit 1
  }
}

Write-Host "Using $(Get-Command ollama | Select-Object -ExpandProperty Source)"
foreach ($model in $models) {
  Write-Host "Pulling $model ..."
  ollama pull $model
}

Write-Host "Done. Keep the Ollama app running, then: docker compose up --build web api"
