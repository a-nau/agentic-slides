#!/usr/bin/env bash
# Export a Quarto deck (only on explicit request) — thin wrapper around the
# slides repo's scripts/export.sh (the same backend as the deck server's
# download buttons).
#   Usage: export.sh <deck-dir> [html|pptx|pdf]
#   html — one self-contained file (images, CSS, MathJax inlined) + comments layer
#   pptx — editable PowerPoint (native text boxes, SVG-picture figures)
#   pdf  — reveal's print view, printed by Chromium
set -euo pipefail
DECK="$(cd "${1:?Usage: $0 <deck-dir> [html|pptx|pdf]}" && pwd)"
FMT="${2:-html}"
ROOT="$DECK"; while [ ! -f "$ROOT/_quarto.yml" ]; do ROOT="$(dirname "$ROOT")"; [ "$ROOT" = / ] && { echo "not inside the slides repo" >&2; exit 1; }; done
REL="${DECK#$ROOT/decks/}"
exec bash "$ROOT/scripts/export.sh" "$REL" "$FMT"
