#!/usr/bin/env bash
# Builds dist/FGDP_SYSTEM.app (Apple Silicon, ad-hoc signed).
# Usage: ./build_app.sh
set -euo pipefail

cd "$(dirname "$0")"

# venv must exist with pyinstaller installed (see README setup).
if [[ ! -x ".venv/bin/python" ]]; then
  echo "ERR: .venv not found — run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && pip install pyinstaller"
  exit 1
fi

source .venv/bin/activate

echo "→ pyinstaller"
pyinstaller --noconfirm --clean FGDP_SYSTEM.spec

echo "→ deep ad-hoc re-sign (fixes Team-ID mismatch on Python framework)"
codesign --force --deep --sign - dist/FGDP_SYSTEM.app

echo "→ verify"
codesign --verify --verbose dist/FGDP_SYSTEM.app

echo
echo "OK: dist/FGDP_SYSTEM.app"
echo "Run with:  open dist/FGDP_SYSTEM.app"
echo "Or drag dist/FGDP_SYSTEM.app to /Applications."
