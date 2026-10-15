#!/usr/bin/env bash
#
# Export a deck (also the export server's backend for the deck download buttons).
#   Usage: scripts/export.sh <category/deck> [html|pptx|pdf|pdf,pptx,...]   (default: pdf)
#
#   html  → exports/<deck>.html — one self-contained file (images, CSS, MathJax
#           inlined) with the comments layer: comments post back to
#           COMMENTS_HOST:COMMENTS_PORT (default localhost and :8094 or
#           $SLIDES_EXPORT_PORT; empty COMMENTS_HOST: no layer).
#   pptx  → exports/<deck>.editable.pptx — native text boxes + SVG-picture
#           figures, via scripts/pptx_export on reveal's print view (alias: pptx-edit).
#   pdf   → exports/<deck>.pdf — reveal's print view, via Chromium.
set -euo pipefail
cd "$(dirname "$0")/.."   # repo root

DECK="${1:?Usage: $0 <category/deck> [html|pptx|pdf|pdf,pptx,...]}"
FORMATS="${2:-pdf}"
SRC="decks/${DECK}/slides.qmd"
[ -f quarto/shim/_client.html ] || python3 quarto/scripts/gen_client.py   # never overwrite: it carries the dev API port
if [ ! -f "$SRC" ] && [ -f "decks/${DECK}/slides.md" ]; then   # Marp-sourced deck not converted yet
    python3 quarto/scripts/marp2qmd.py --keep "decks/${DECK}" >/dev/null
fi
[ -f "$SRC" ] || { echo "Error: $SRC not found." >&2; exit 1; }
OUT="exports/${DECK}"
mkdir -p "$(dirname "$OUT")"
py="${PPTX_PYTHON:-.venv/bin/python}"

IFS=',' read -ra FMT_LIST <<< "$FORMATS"
for fmt in "${FMT_LIST[@]}"; do
  case "$(echo "$fmt" | tr '[:upper:]' '[:lower:]' | xargs)" in
  html)
    tmp="$(mktemp -d .export.XXXXXX)"
    trap 'rm -rf "$tmp"' EXIT
    quarto/bin/quarto render "$SRC" -M embed-resources:true --output-dir "$tmp" --quiet
    out="${OUT}.html"
    cp "$tmp/decks/${DECK}/slides.html" "$out"
    # reveal's math plugin loads MathJax at runtime from a relative URL, which
    # embed-resources cannot inline: put MathJax itself into the file.
    python3 - "$out" quarto/vendor/mathjax/tex-svg.js <<'PY'
import sys
path, mj = sys.argv[1:3]
html = open(path, encoding="utf-8").read()
js = open(mj, encoding="utf-8").read()
if "</script" in js:
    sys.exit("tex-svg.js contains a closing script tag; cannot inline")
html = html.replace("</head>", "<script>\n" + js + "\n</script>\n</head>", 1)
open(path, "w", encoding="utf-8").write(html)
PY
    # localhost: comments land when the file is opened on the machine running the
    # server. COMMENTS_HOST=<reachable host> collects them from other machines
    # (that name is embedded in the file).
    CM_HOST="${COMMENTS_HOST-localhost}"
    if [ -n "$CM_HOST" ]; then   # the client layers are in the file; tell them where home is
        python3 - "$out" "${DECK}" "http://${CM_HOST}:${COMMENTS_PORT:-${SLIDES_EXPORT_PORT:-8094}}" <<'PY'
import json, sys
path, deck, base = sys.argv[1:4]
cfg = json.dumps({"deck": deck, "base": base, "exported": True})
html = open(path, encoding="utf-8").read()
html = html.replace("<head>", f"<head>\n<script>window.CM_CONFIG={cfg};</script>", 1)
open(path, "w", encoding="utf-8").write(html)
PY
    fi ;;
  pptx|pptx-edit)
    quarto/bin/quarto render "$SRC" --quiet
    out="${OUT}.editable.pptx"
    [ -x "$py" ] || { echo "Error: ${py} not found (scripts/pptx_export/requirements.txt)." >&2; exit 1; }
    "$py" -m scripts.pptx_export "decks/${DECK}/slides.html" "$out" ;;
  pdf)
    quarto/bin/quarto render "$SRC" --quiet
    out="${OUT}.pdf"
    "$py" - "decks/${DECK}/slides.html" "$out" <<'PY'
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch(channel="chrome")
    p = b.new_page()
    # remote video streams would keep the network busy forever; the PDF gets a link instead
    p.route("**/*", lambda r: r.abort() if r.request.resource_type == "media" else r.continue_())
    p.goto(Path(sys.argv[1]).resolve().as_uri() + "?print-pdf", wait_until="networkidle")
    p.evaluate("() => document.querySelectorAll('video[src^=\"http\"]').forEach(v => {"
               " const a = document.createElement('a'); a.href = v.src; a.textContent = '▶ ' + v.src.split('/').pop();"
               " a.style.cssText = v.style.cssText + ';display:flex;align-items:center;justify-content:center;"
               "border:1px solid #333;border-radius:8px;color:#e5e5e5;margin:0 auto';"
               " v.replaceWith(a); })")
    p.wait_for_function("() => document.querySelectorAll('.reveal .pdf-page').length > 0")
    p.evaluate("() => window.MathJax && MathJax.startup ? MathJax.startup.promise : null")
    # relative links would print as file:///<this machine's path>: keep the text, drop the link
    p.evaluate("() => document.querySelectorAll('a[href]').forEach(a =>"
               " new URL(a.getAttribute('href'), document.baseURI).protocol === 'file:' && a.removeAttribute('href'))")
    p.pdf(path=sys.argv[2], width="1280px", height="720px", print_background=True)
    b.close()
PY
    ;;
  *) echo "Unknown format: $fmt (html, pptx or pdf)" >&2; exit 1 ;;
  esac
  echo "  ✓ ${out}"
done
