#!/usr/bin/env bash
# Full rebuild of every deck (a few minutes), safe while quarto/scripts/serve.py
# runs: both take .quarto/render.lock, so the watcher never renders a deck whose
# output the full build is moving into place.
set -euo pipefail
cd "$(dirname "$0")/../.."
mkdir -p .quarto
exec flock .quarto/render.lock quarto/bin/quarto render "$@"
