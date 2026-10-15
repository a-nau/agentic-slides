#!/usr/bin/env bash
#
# One-time setup, safe to re-run.
#   Usage: scripts/setup.sh
#
#   .venv/                    deck server (:8093) + comments/export API (:8094):
#                             comments, edit mode, HTML/PPTX/PDF downloads
#   quarto/.dist, quarto/vendor/   Quarto (checksum-verified release) + local MathJax and fonts (quarto/scripts/setup.sh)
#   .git/hooks/pre-commit     rebuilds generated slides.qmd on commit
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> python venv (.venv)"
[ -x .venv/bin/python ] || python3 -m venv .venv
.venv/bin/pip install -q --require-hashes -r scripts/pptx_export/requirements.lock   # exact versions + hashes, as CI

echo "==> Quarto toolchain (quarto/)"
quarto/scripts/setup.sh

echo "==> git hooks"
scripts/install-hooks.sh

echo ""
echo "Done. Start the server with:  scripts/start.sh"
