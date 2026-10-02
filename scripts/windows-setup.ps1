<#
  One-shot, idempotent setup + start for PolarisLex on Windows 10/11.

  Usage (from anywhere):
    powershell -ExecutionPolicy Bypass -File scripts\windows-setup.ps1

  Safe to re-run: every step checks the current state and skips what is done.

  Optional environment variables (all have sensible defaults):
    POLARIS_CHAT_MODEL   chat model to use (default: picked from RAM, then remembered in .env)
    OLLAMA_MODELS        where Ollama stores models (e.g. D:\Ollama\models); honoured if set
    OLLAMA_EXE           full path to ollama.exe if it is not on PATH
    FORCE_REINDEX=1      re-run the Qdrant ingest even if data exists
#>
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$EmbedModel = "nomic-embed-text"
$Qdrant     = "http://localhost:6333"

function Log($m)  { Write-Host "`n==> $m" -ForegroundColor Cyan }
function Skip($m) { Write-Host "    (skip) $m" -ForegroundColor DarkGray }
function Die($m)  { Write-Host "ERROR: $m" -ForegroundColor Red; exit 1 }
function Has($c)  { [bool](Get-Command $c -ErrorAction SilentlyContinue) }
function Up($url) { $null = curl.exe -s -f -m 5 $url 2>$null; return ($LASTEXITCODE -eq 0) }
function DockerUp { $null = docker info 2>$null; return ($LASTEXITCODE -eq 0) }

# ---------- 1. Docker ----------
Log "Docker"
if (-not (Has docker)) {
  $dd = "C:\Program Files\Docker\Docker\resources\bin"
  if (Test-Path "$dd\docker.exe") { $env:Path = "$dd;$env:Path" }
}
if (-not (Has docker)) {
  Die "Docker Desktop not found. Install it: https://docs.docker.com/desktop/setup/install/windows-install/ (then re-run)."
}
if (-not (DockerUp)) {
  $exe = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
  if (-not (Test-Path $exe)) { Die "Docker is installed but not running, and Docker Desktop.exe was not found." }
  Write-Host "    Starting Docker Desktop..."
  Start-Process $exe
  $ok = $false
  for ($i = 0; $i -lt 60 -and -not $ok; $i++) { Start-Sleep 5; $ok = DockerUp }
  if (-not $ok) { Die "Docker did not become ready in 5 minutes." }
} else { Skip "docker running" }

# ---------- 2. Ollama ----------
Log "Ollama"
$ollama = $null
# Collect every candidate, then prefer a *complete* install (has lib\ollama with the inference
# engine). A half-installed copy (e.g. from a disk-full install) can sit earlier on PATH and
# makes every embedding/chat call return 500.
$cands = @()
if ($env:OLLAMA_EXE) { $cands += $env:OLLAMA_EXE }
$cands += @(Get-Command ollama -All -ErrorAction SilentlyContinue | ForEach-Object { $_.Source })
$cands += "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe", "$env:ProgramFiles\Ollama\ollama.exe"
$cands = @($cands | Where-Object { $_ -and (Test-Path $_) } | Select-Object -Unique)
foreach ($c in $cands) {
  $lib = Join-Path (Split-Path -Parent $c) "lib\ollama"
  if ((Test-Path $lib) -and @(Get-ChildItem $lib -ErrorAction SilentlyContinue).Count -gt 0) { $ollama = $c; break }
}
if (-not $ollama -and $cands.Count -gt 0) {
  $ollama = $cands[0]
  Write-Host "    WARNING: $ollama looks incomplete (no lib\ollama). Reinstall Ollama, or set OLLAMA_EXE to a working ollama.exe." -ForegroundColor Yellow
}
if (-not $ollama) {
  if (Has winget) {
    Write-Host "    Installing Ollama with winget..."
    winget install --id Ollama.Ollama -e --accept-package-agreements --accept-source-agreements
    $p = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
    if (Test-Path $p) { $ollama = $p }
  }
  if (-not $ollama) { Die "Ollama not found. Install the Windows build from https://ollama.com/download/windows (not WSL) and re-run." }
}
Write-Host "    using $ollama"
$ollamaDir = Split-Path -Parent $ollama
if (($env:Path -split ';') -notcontains $ollamaDir) { $env:Path = "$ollamaDir;$env:Path" }

if (-not (Up "http://localhost:11434/api/tags")) {
  # If OLLAMA_MODELS is set it is inherited by the process we start.
  $tray = Join-Path $ollamaDir "ollama app.exe"
  if (Test-Path $tray) { Start-Process $tray } else { Start-Process $ollama -ArgumentList "serve" -WindowStyle Hidden }
  $ok = $false
  for ($i = 0; $i -lt 30 -and -not $ok; $i++) { Start-Sleep 3; $ok = Up "http://localhost:11434/api/tags" }
  if (-not $ok) { Die "Ollama did not start. Check %LOCALAPPDATA%\Ollama\server.log" }
} else { Skip "ollama already serving" }

# ---------- 3. Chat model: explicit > .env > pick by RAM ----------
Log "Chat model"
$envFile = Join-Path $Root ".env"
$chat = $env:POLARIS_CHAT_MODEL
if (-not $chat -and (Test-Path $envFile)) {
  $line = Select-String -Path $envFile -Pattern '^POLARIS_CHAT_MODEL=(.+)$' | Select-Object -Last 1
  if ($line) { $chat = $line.Matches[0].Groups[1].Value.Trim() }
}
if (-not $chat) {
  $ramGb = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)
  # Docker + Ollama share RAM, so be conservative.
  if ($ramGb -ge 16) { $chat = "qwen2.5:7b-instruct-q4_K_M" } else { $chat = "qwen2.5:3b-instruct" }
  Write-Host "    RAM $ramGb GB -> $chat"
}
$current = $null
if (Test-Path $envFile) {
  $l = Select-String -Path $envFile -Pattern '^POLARIS_CHAT_MODEL=(.+)$' | Select-Object -Last 1
  if ($l) { $current = $l.Matches[0].Groups[1].Value.Trim() }
}
if ($current -ne $chat) {
  $keep = @()
  if (Test-Path $envFile) { $keep = @(Get-Content $envFile | Where-Object { $_ -notmatch '^POLARIS_CHAT_MODEL=' }) }
  Set-Content -Path $envFile -Value ($keep + "POLARIS_CHAT_MODEL=$chat") -Encoding ascii
} else { Skip ".env already has $chat" }

function Pull-IfMissing($m) {
  $want = $m; if ($m -notmatch ':') { $want = "${m}:latest" }
  $have = (& $ollama list | Select-Object -Skip 1 | ForEach-Object { ($_ -split '\s+')[0] })
  if ($have -contains $want) { Skip "$m already pulled" }
  else { & $ollama pull $m; if ($LASTEXITCODE -ne 0) { Die "ollama pull $m failed" } }
}
Pull-IfMissing $EmbedModel
Pull-IfMissing $chat

# ---------- 4. Containers ----------
Log "Containers (web, api, qdrant)"
docker compose up --build -d web api
if ($LASTEXITCODE -ne 0) {
  # Typical cause: a container stuck as an unkillable zombie. Restarting the Docker engine clears it.
  Write-Host "    compose failed; restarting the Docker engine once and retrying..." -ForegroundColor Yellow
  Get-Process "Docker Desktop", "com.docker.backend" -ErrorAction SilentlyContinue | Stop-Process -Force
  wsl --shutdown
  Start-Sleep 5
  Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
  $ok = $false
  for ($i = 0; $i -lt 60 -and -not $ok; $i++) { Start-Sleep 5; $ok = DockerUp }
  if (-not $ok) { Die "Docker did not come back after restart." }
  docker compose down 2>$null
  docker compose up --build -d web api
  if ($LASTEXITCODE -ne 0) { Die "docker compose failed again. See: docker compose logs" }
}
$ok = $false
for ($i = 0; $i -lt 60 -and -not $ok; $i++) {
  $ok = (Up "http://localhost:8000/health") -and (Up "$Qdrant/collections")
  if (-not $ok) { Start-Sleep 2 }
}
if (-not $ok) { Die "API not healthy. See: docker compose logs api" }

# ---------- 5. Python venv ----------
Log "Python venv"
$py = Join-Path $Root ".venv\Scripts\python.exe"
$venvOk = $false
if (Test-Path $py) {
  & $py -c "import vectorization, document_pipeline" 2>$null
  $venvOk = ($LASTEXITCODE -eq 0)
}
if ($venvOk) { Skip "venv OK" }
else {
  $launcher = $null
  if (Has py) { $launcher = @("py", "-3.12") } elseif (Has python) { $launcher = @("python") }
  if (-not $launcher) { Die "Python 3.12+ not found. Install from https://www.python.org/downloads/ and re-run." }
  if (Test-Path (Join-Path $Root ".venv")) { Remove-Item -Recurse -Force (Join-Path $Root ".venv") }
  if (Has py) { & py -3.12 -m venv (Join-Path $Root ".venv") } else { & python -m venv (Join-Path $Root ".venv") }
  if ($LASTEXITCODE -ne 0) { Die "venv creation failed (need Python 3.12; try: py -3.12 --version)" }
  & $py -m pip install -U pip
  & $py -m pip install -e (Join-Path $Root "vectorization") -e (Join-Path $Root "document_pipeline")
  if ($LASTEXITCODE -ne 0) { Die "pip install failed" }
}

# A stale SSL_CERT_FILE (e.g. from an uninstalled XAMPP) breaks httpx; fall back to certifi.
if ($env:SSL_CERT_FILE -and -not (Test-Path $env:SSL_CERT_FILE)) {
  $env:SSL_CERT_FILE = (& $py -c "import certifi;print(certifi.where())")
  Write-Host "    SSL_CERT_FILE pointed to a missing file; using certifi bundle for this run."
}

# ---------- 6. Law vectors (each source checked independently) ----------
function Count-Source($t) {
  $body = '{"exact":true,"filter":{"must":[{"key":"source_type","match":{"value":"' + $t + '"}}]}}'
  try {
    $r = Invoke-RestMethod -Method Post -Uri "$Qdrant/collections/document_clauses/points/count" -ContentType "application/json" -Body $body
    return [int]$r.result.count
  } catch { return 0 }
}
Log "Law vectors"
$vec = Join-Path $Root ".venv\Scripts\vectorization.exe"
$force = ($env:FORCE_REINDEX -eq "1")
$kg = Count-Source "kg_obligation"
$rag = Count-Source "rag_section"
Push-Location (Join-Path $Root "vectorization")
try {
  if ($force -or $kg -eq 0) { & $vec ingest-kg; if ($LASTEXITCODE -ne 0) { Die "ingest-kg failed" } }
  else { Skip "kg_obligation already indexed ($kg points)" }
  if ($force -or $rag -eq 0) {
    & $vec ingest-rag --path ../dataset/IT_ACT_POLARISLEX_MERGED.json
    if ($LASTEXITCODE -ne 0) { Die "ingest-rag failed" }
  } else { Skip "rag_section already indexed ($rag points)" }
} finally { Pop-Location }

# ---------- 7. Smoke test ----------
Log "Smoke test: /analyze on a sample policy"
$code = curl.exe -s -m 600 -o NUL -w "%{http_code}" -F "file=@$Root\test_policy\test.txt" http://localhost:8000/analyze
Write-Host "    /analyze -> HTTP $code (a 503 right after a chat request can be a one-off model swap on low RAM; just retry)"

Write-Host @"

==========================================================
 PolarisLex is running.
   UI:      http://localhost:8080
   API:     http://localhost:8000/health
   Qdrant:  http://localhost:6333/dashboard
   Chat model: $chat    Embeddings: $EmbedModel

 Re-run this script any time; it only does what's missing.
 Stop:  docker compose down      (from $Root)
==========================================================
"@
