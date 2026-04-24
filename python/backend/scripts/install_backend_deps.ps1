# CREDA backend — clean install into the ACTIVE venv (e.g. .\.venv\Scripts\Activate.ps1).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "Removing pdfplumber if present (conflicts with casparser pdfminer.six==20240706)..." -ForegroundColor Cyan
pip uninstall -y pdfplumber 2>$null | Out-Null

Write-Host "Installing requirements.txt..." -ForegroundColor Cyan
pip install -r (Join-Path $Root "requirements.txt")

Write-Host "pip check:" -ForegroundColor Cyan
pip check 2>&1
Write-Host "Done. If pip check reports conflicts, use a venv that only holds CREDA + this file." -ForegroundColor Green
