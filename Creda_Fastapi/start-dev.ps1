# Start CREDA backend stack (3 separate terminals).
# Simpler: one terminal —  python run_stack.py   (starts finance + multilingual, then gateway)
# Prerequisite: conda env with deps (e.g. fastapi-cv) — same as your manual workflow.
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
if (-not $root) { $root = Get-Location }

# Use the active interpreter (run `conda activate fastapi-cv` in this shell first).
$pyExe = "python"
if (Get-Command python -ErrorAction SilentlyContinue) {
  $pyExe = (Get-Command python).Source
}
$pyQuoted = "`"$pyExe`""

function Start-CredaService {
  param([string]$Title, [string]$Script)
  $line = "title $Title && cd /d `"$root`" && $pyQuoted $Script"
  Start-Process cmd -ArgumentList @("/k", $line)
}

Write-Host "Opening 3 terminals: multilingual (:8010), finance (:8001), gateway (:8080)..." -ForegroundColor Cyan
Start-CredaService "CREDA multilingual" "fastapi1_multilingual.py"
Start-Sleep -Milliseconds 800
Start-CredaService "CREDA finance" "fastapi2_finance.py"
Start-Sleep -Milliseconds 800
Start-CredaService "CREDA gateway" "app.py"
Write-Host "Done. Wait for 'Application startup complete' on gateway, then open http://localhost:8080/health" -ForegroundColor Green
