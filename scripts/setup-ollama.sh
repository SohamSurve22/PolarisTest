# Pulls local Ollama models used by PolarisLex.
# Requires Ollama already installed and `ollama` on PATH.
#   macOS: brew install ollama   OR https://ollama.com/download
#   Windows: scripts/setup-ollama.ps1 (winget or the Windows installer)

set -euo pipefail

MODELS=(
  "nomic-embed-text"
  "qwen2.5:7b-instruct-q4_K_M"
)

if ! command -v ollama >/dev/null 2>&1; then
  echo "ollama is not on PATH. Install it first:"
  echo "  macOS:  brew install ollama"
  echo "  Linux:  https://ollama.com/download/linux"
  echo "  Windows: PowerShell  .\\scripts\\setup-ollama.ps1"
  exit 1
fi

echo "Using $(command -v ollama)"
for model in "${MODELS[@]}"; do
  echo "Pulling ${model} ..."
  ollama pull "${model}"
done

echo "Done. Keep Ollama running, then: docker compose up --build web api"
