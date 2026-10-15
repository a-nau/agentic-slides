#!/usr/bin/env bash
#
# Export every deck as a single self-contained HTML file, plus an index.html
# grouped by category in the same order as the decks/ overview page.
#   Usage: .agents/skills/export-all-html/export_all_html.sh [output_dir]
#
#   output_dir — where the files land (default: exports/). Layout:
#                <output_dir>/<category>/<deck>.html + <output_dir>/index.html
#
# Each deck is exported via scripts/export.sh <deck> html (Quarto
# embed-resources), which always writes exports/<deck>.html; for a custom
# output_dir the file is copied there afterwards. Decks that fail to export
# are skipped, listed at the end, and left out of the index.
set -euo pipefail
cd "$(dirname "$0")/../../.."   # skill asset → repo root

OUT_DIR="${1:-exports}"
OUT_DIR="${OUT_DIR%/}"

# Same categories and order as scripts/gen_index.sh ("<dir>|<label>"),
# with MR decks before templates like on the main landing page.
CATEGORIES=(
  "tools|Tools"
  "repos|Repos"
  "reading-groups|Reading Groups"
  "paper-reviews|Paper Reviews"
  "investigations|Investigations"
  "mrs|MR decks"
  "templates|Templates"
)

# --- title / description extraction (same rules as gen_index.sh) -------------
pretty() { echo "$1" | sed 's/-/ /g; s/\b\(.\)/\u\1/g'; }
strip_md() { sed 's/\*\*//g; s/&nbsp;/ /g; s#<br */*># #g'; }

deck_title() {
    local slides="$1" d src title
    d=$(dirname "$slides")
    src="$d/slides.tpl.md"; [ -f "$src" ] || src="$slides"
    title=$(grep -m1 '^# ' "$src" | sed 's/^#\+ *//' | strip_md)
    [ -n "$title" ] || title=$(pretty "$(basename "$d")")
    printf '%s' "$title"
}

deck_desc() {
    local slides="$1" d src desc
    d=$(dirname "$slides")
    src="$d/slides.tpl.md"; [ -f "$src" ] || src="$slides"
    desc=$(awk '
        NR==1 && /^---[ \t]*$/ { fm=1; next }
        fm && /^---[ \t]*$/ { exit }
        fm && /^description:[ \t]*/ {
            sub(/^description:[ \t]*/, "")
            gsub(/^["'\'']|["'\'']$/, "")
            print; exit
        }' "$src")
    if [ -z "$desc" ]; then
        desc=$(awk '
            /^---[ \t]*$/ { dash++; next }
            dash == 2 && /^## / { sub(/^## +/, ""); print; exit }
            dash >= 3 { exit }' "$src")
    fi
    printf '%s' "$desc" | strip_md
}

day_of() { date -d "@$(stat -c %Y "$1")" +%Y-%m-%d 2>/dev/null || echo ""; }

# --- export every deck, newest-first within each category --------------------
FAILED=()
SECTIONS=""

for entry in "${CATEGORIES[@]}"; do
    dir="${entry%%|*}"; label="${entry#*|}"
    [ -d "decks/$dir" ] || continue

    rows=""
    while IFS= read -r slides; do
        [ -n "$slides" ] || continue
        deck="${slides#decks/}"; deck="${deck%/slides.qmd}"
        echo "=== ${deck}"
        if ! scripts/export.sh "$deck" html; then
            echo "  ✗ export failed, skipping" >&2
            FAILED+=("$deck")
            continue
        fi
        if [ "$OUT_DIR" != "exports" ]; then
            mkdir -p "$OUT_DIR/$(dirname "$deck")"
            cp "exports/${deck}.html" "$OUT_DIR/${deck}.html"
        fi
        rows="${rows}<a class=\"item\" href=\"${deck}.html\"><div class=\"item-top\"><span class=\"item-name\">$(deck_title "$slides")</span><span class=\"item-date\">$(day_of "$slides")</span></div><p class=\"item-desc\">$(deck_desc "$slides")</p></a>"
    done < <(find "decks/$dir" -name slides.qmd -type f -printf '%T@\t%p\n' | sort -rn | cut -f2-)

    [ -n "$rows" ] || continue
    SECTIONS="${SECTIONS}<section class=\"cat\"><h2>${label}</h2><div class=\"list\">${rows}</div></section>"
done

# --- index.html: categories in overview order, decks newest-first ------------
mkdir -p "$OUT_DIR"
cat > "$OUT_DIR/index.html" <<ENDHTML
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Slide Decks · HTML exports</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Inter', system-ui, sans-serif;
    background: radial-gradient(1200px 600px at 50% -200px, #0b1a33 0%, #0a0a0a 60%) no-repeat, #0a0a0a;
    color: #f0f0f0; min-height: 100vh;
    display: flex; flex-direction: column; align-items: center;
    padding: 4rem 1.5rem 5rem;
  }
  h1 { font-size: 2.4rem; font-weight: 700; margin-bottom: 0.5rem; color: #3b82f6; letter-spacing: -0.01em; }
  .subtitle { color: #a0a0a0; margin-bottom: 3rem; font-size: 1.05rem; text-align: center; }
  .wrap { width: 100%; max-width: 820px; display: flex; flex-direction: column; gap: 1.5rem; }
  .cat { background: #141414; border: 1px solid #242424; border-radius: 0.9rem; padding: 0.4rem 0.55rem 0.6rem; }
  .cat h2 { font-size: 1.2rem; font-weight: 700; color: #3b82f6; padding: 0.7rem 0.85rem 0.75rem; border-bottom: 1px solid #232323; margin-bottom: 0.35rem; }
  .list { display: flex; flex-direction: column; width: 100%; }
  .item { display: block; padding: 0.9rem 1rem; border-radius: 0.6rem; text-decoration: none; color: #f0f0f0; transition: background 0.12s ease; }
  .item + .item { box-shadow: 0 -1px 0 #232323; }
  .item:hover { background: #1d1d1d; }
  .item-top { display: flex; align-items: baseline; justify-content: space-between; gap: 1rem; }
  .item-name { font-weight: 600; font-size: 1.03rem; line-height: 1.3; }
  .item-date { color: #707070; font-size: 0.78rem; white-space: nowrap; font-family: ui-monospace, 'JetBrains Mono', monospace; }
  .item-desc { color: #9a9a9a; font-size: 0.87rem; line-height: 1.45; margin-top: 0.25rem; max-width: 62ch; }
</style>
</head>
<body>
  <h1>Slide Decks</h1>
  <p class="subtitle">Self-contained HTML exports — grouped by category, newest first</p>
  <div class="wrap">${SECTIONS}</div>
</body>
</html>
ENDHTML
echo "Wrote ${OUT_DIR}/index.html"

if [ ${#FAILED[@]} -gt 0 ]; then
    echo "Failed decks:" >&2
    printf '  %s\n' "${FAILED[@]}" >&2
    exit 1
fi
echo "Done."
