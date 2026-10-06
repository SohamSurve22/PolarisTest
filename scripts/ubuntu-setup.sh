#!/usr/bin/env bash
# One-shot setup + start for PolarisLex on Ubuntu (22.04 / 24.04).
# Usage:  bash scripts/ubuntu-setup.sh
#
# Idempotent: re-running changes nothing that is already in the desired state
# (packages, Docker, Ollama config/service, models, .env, containers, venv,
# and each Qdrant collection are checked first; Qdrant point IDs are
# deterministic so even a forced re-ingest never duplicates data).
# Overrides:  POLARIS_CHAT_MODEL=<model> bash scripts/ubuntu-setup.sh
#             FORCE_REINDEX=1            bash scripts/ubuntu-setup.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

EMBED_MODEL="nomic-embed-text"
QDRANT="http://localhost:6333"
log()  { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
skip() { printf '    \033[0;90m(skip) %s\033[0m\n' "$*"; }

if [ "$(id -u)" -eq 0 ]; then SUDO=""; else SUDO="sudo"; fi

# ---------- 1. System packages (install only what's missing) ----------
log "System packages"
PKGS=(curl ca-certificates git python3 python3-venv python3-pip zstd)
MISSING=()
for p in "${PKGS[@]}"; do
  dpkg -s "$p" >/dev/null 2>&1 || MISSING+=("$p")
done
if [ "${#MISSING[@]}" -gt 0 ]; then
  $SUDO apt-get update -y
  $SUDO apt-get install -y "${MISSING[@]}"
else
  skip "all present"
fi

# ---------- 2. Docker ----------
log "Docker"
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | $SUDO sh
else
  skip "docker installed"
fi
$SUDO systemctl is-enabled --quiet docker || $SUDO systemctl enable docker
$SUDO systemctl is-active  --quiet docker || $SUDO systemctl start docker
if [ -n "$SUDO" ] && ! id -nG "$USER" | grep -qw docker; then
  $SUDO usermod -aG docker "$USER"
  echo "    Added $USER to the docker group (effective after next login; sudo is used meanwhile)."
fi
DOCKER="$SUDO docker"

# ---------- 3. Ollama (host service, reachable from containers) ----------
log "Ollama"
if ! command -v ollama >/dev/null 2>&1; then
  curl -fsSL https://ollama.com/install.sh | sh
else
  skip "ollama installed"
fi

# Containers reach Ollama via the docker bridge, so it must not bind to 127.0.0.1 only.
OVERRIDE_DIR=/etc/systemd/system/ollama.service.d
OVERRIDE_FILE=$OVERRIDE_DIR/polaris.conf
WANT=$'[Service]\nEnvironment="OLLAMA_HOST=0.0.0.0:11434"'
RESTART_OLLAMA=0
if [ "$(cat "$OVERRIDE_FILE" 2>/dev/null || true)" != "$WANT" ]; then
  $SUDO mkdir -p "$OVERRIDE_DIR"
  printf '%s\n' "$WANT" | $SUDO tee "$OVERRIDE_FILE" >/dev/null
  $SUDO systemctl daemon-reload
  RESTART_OLLAMA=1
else
  skip "service override already set"
fi
$SUDO systemctl is-enabled --quiet ollama || $SUDO systemctl enable ollama
if [ "$RESTART_OLLAMA" -eq 1 ]; then
  $SUDO systemctl restart ollama
else
  $SUDO systemctl is-active --quiet ollama || $SUDO systemctl start ollama
fi

for _ in $(seq 1 60); do
  curl -fs http://localhost:11434/api/tags >/dev/null 2>&1 && break
  sleep 2
done
curl -fs http://localhost:11434/api/tags >/dev/null || { echo "Ollama did not start"; exit 1; }

# ---------- 4. Chat model: keep existing choice, else pick by RAM ----------
log "Chat model"
CHAT_MODEL="${POLARIS_CHAT_MODEL:-}"
if [ -z "$CHAT_MODEL" ] && [ -f "$ROOT/.env" ]; then
  CHAT_MODEL="$(grep -E '^POLARIS_CHAT_MODEL=' "$ROOT/.env" | tail -n1 | cut -d= -f2- || true)"
fi
if [ -z "$CHAT_MODEL" ]; then
  RAM_GB=$(awk '/MemTotal/ {printf "%d", $2/1024/1024}' /proc/meminfo)
  if [ "$RAM_GB" -ge 12 ]; then CHAT_MODEL="qwen2.5:7b-instruct-q4_K_M"; else CHAT_MODEL="qwen2.5:3b-instruct"; fi
  echo "    RAM ${RAM_GB} GB -> $CHAT_MODEL"
fi
if [ "$(grep -E '^POLARIS_CHAT_MODEL=' "$ROOT/.env" 2>/dev/null | tail -n1 | cut -d= -f2- || true)" != "$CHAT_MODEL" ]; then
  # Only touch the one key; leave any other .env content alone.
  touch "$ROOT/.env"
  sed -i '/^POLARIS_CHAT_MODEL=/d' "$ROOT/.env"
  echo "POLARIS_CHAT_MODEL=$CHAT_MODEL" >> "$ROOT/.env"
else
  skip ".env already has $CHAT_MODEL"
fi

pull_if_missing() {
  local m="$1"
  # `ollama list` prints "name:tag"; accept bare names as ":latest".
  local want="$m"; [[ "$m" == *:* ]] || want="$m:latest"
  if ollama list | awk 'NR>1 {print $1}' | grep -qx "$want"; then
    skip "$m already pulled"
  else
    ollama pull "$m"
  fi
}
pull_if_missing "$EMBED_MODEL"
pull_if_missing "$CHAT_MODEL"

# ---------- 5. Containers (compose up is a no-op when nothing changed) ----------
log "Containers (web, api, qdrant)"
$DOCKER compose up --build -d web api

for _ in $(seq 1 90); do
  curl -fs http://localhost:8000/health >/dev/null 2>&1 && curl -fs "$QDRANT/collections" >/dev/null 2>&1 && break
  sleep 2
done
curl -fs http://localhost:8000/health >/dev/null || { echo "API not healthy; see: sudo docker compose logs api"; exit 1; }

# ---------- 6. Python venv ----------
log "Python venv"
if [ -x "$ROOT/.venv/bin/vectorization" ] && "$ROOT/.venv/bin/python" -c "import vectorization, document_pipeline" 2>/dev/null; then
  skip "venv OK"
else
  rm -rf "$ROOT/.venv"
  python3 -m venv "$ROOT/.venv"
  "$ROOT/.venv/bin/pip" install -U pip
  "$ROOT/.venv/bin/pip" install -e "$ROOT/vectorization" -e "$ROOT/document_pipeline"
fi

# ---------- 7. Index law vectors, each source checked independently ----------
count_source() {  # prints number of Qdrant points with the given source_type (0 if none/unavailable)
  curl -fs -X POST "$QDRANT/collections/document_clauses/points/count" \
    -H 'Content-Type: application/json' \
    -d "{\"exact\":true,\"filter\":{\"must\":[{\"key\":\"source_type\",\"match\":{\"value\":\"$1\"}}]}}" 2>/dev/null \
    | grep -o '"count":[0-9]*' | cut -d: -f2 || true
}

log "Law vectors"
KG="$(count_source kg_obligation)"; KG="${KG:-0}"
RAG="$(count_source rag_section)";  RAG="${RAG:-0}"
if [ "${FORCE_REINDEX:-0}" = "1" ] || [ "$KG" -eq 0 ]; then
  (cd "$ROOT/vectorization" && "$ROOT/.venv/bin/vectorization" ingest-kg)
else
  skip "kg_obligation already indexed ($KG points)"
fi
if [ "${FORCE_REINDEX:-0}" = "1" ] || [ "$RAG" -eq 0 ]; then
  (cd "$ROOT/vectorization" && "$ROOT/.venv/bin/vectorization" ingest-rag --path ../dataset/IT_ACT_POLARISLEX_MERGED.json)
else
  skip "rag_section already indexed ($RAG points)"
fi

# ---------- 8. Smoke test (read-only) ----------
log "Smoke test: /analyze on a sample policy"
curl -fs -m 600 -F "file=@$ROOT/test_policy/test.txt" http://localhost:8000/analyze | head -c 200 || echo "(analyze failed)"
echo

cat <<EOF

==========================================================
 PolarisLex is running.
   UI:      http://localhost:8080
   API:     http://localhost:8000/health
   Qdrant:  http://localhost:6333/dashboard
   Chat model: $CHAT_MODEL   Embeddings: $EMBED_MODEL

 Re-run this script any time; it only does what's missing.
 Stop:  sudo docker compose down
==========================================================
EOF
