#!/usr/bin/env bash
# CREDA backend — clean install (use a dedicated venv).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "Removing pdfplumber if present (conflicts with casparser pdfminer pin)..."
pip uninstall -y pdfplumber 2>/dev/null || true

echo "Installing requirements.txt..."
pip install -r requirements.txt

echo "pip check:"
pip check || true
echo "Done."
