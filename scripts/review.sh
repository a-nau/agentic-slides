#!/usr/bin/env bash
# Fact-check a deck against its source(s) and wire up in-deck review mode.
#   scripts/review.sh <category>/<deck>
# Loops over the deck's `sources:`, fetches+annotates each, ingests a multi-source
# review.json, installs the in-deck viewer, and adds the <script> include to the deck source.
set -euo pipefail
cd "$(dirname "$0")/.."

DECK="${1:?usage: review.sh <category>/<deck>}"
DECK_DIR="decks/${DECK}"
MD="${DECK_DIR}/slides.qmd"
[ -f "${DECK_DIR}/slides.md" ] && MD="${DECK_DIR}/slides.md"   # Marp-sourced deck
SLUG="$(basename "$DECK")"
SKILL=".agents/skills/slide-deck/scripts/annotate"
VENV="${ANNOTATE_PY:-$HOME/.venvs/annotate-source/bin/python}"
SCRATCH="${TMPDIR:-/tmp}/source-review/${SLUG}"
mkdir -p "$SCRATCH"

[ -f "$MD" ] || { echo "no deck source at $MD" >&2; exit 1; }
[ -f source-review/ingest.py ] || { echo "source-review/ missing" >&2; exit 1; }

# Parse every entry of the `sources:` front-matter list.
SRCS=()
while IFS= read -r l; do SRCS+=("$l"); done < <(awk '/^sources:/{f=1;next} f&&/^[^[:space:]-]/{exit} f&&/^[[:space:]]*-[[:space:]]/{gsub(/^[[:space:]]*-[[:space:]]*/,"");gsub(/["'"'"']/,"");print}' "$MD")
[ "${#SRCS[@]}" -gt 0 ] || { echo "no 'sources:' entries in $MD front-matter" >&2; exit 1; }
printf 'sources: %s\n' "${SRCS[*]}"

# Fetch each source once into $SCRATCH/<id>; build sources.json.
SOURCES_JSON="["
for i in "${!SRCS[@]}"; do
  id="s$i"; url="${SRCS[$i]}"; w="$SCRATCH/$id"; mkdir -p "$w"
  [ -f "$w/meta.json" ] || "$VENV" "$SKILL/fetch.py" "$url" --workdir "$w"
  typ="$("$VENV" -c "import json;print(json.load(open('$w/meta.json'))['type'])")"
  ttl="$("$VENV" -c "import json;print(json.load(open('$w/meta.json')).get('title') or '$id')")"
  [ "$i" -gt 0 ] && SOURCES_JSON+=","
  SOURCES_JSON+=$(SR_ID="$id" SR_URL="$url" SR_TTL="$ttl" SR_TYP="$typ" "$VENV" -c "import json,os;print(json.dumps({'id':os.environ['SR_ID'],'url':os.environ['SR_URL'],'title':os.environ['SR_TTL'],'type':os.environ['SR_TYP']}))")
done
SOURCES_JSON+="]"
printf '%s' "$SOURCES_JSON" > "$SCRATCH/sources.json"

# Agent step: author $SCRATCH/annotations.json (claims with source/wiki_quote/quote/verdict).
if [ ! -f "$SCRATCH/annotations.json" ]; then
  cat >&2 <<EOF

NEXT (agent step): for each source read its $SCRATCH/s<i>/dump.txt and $MD, then write
$SCRATCH/annotations.json — claims with: wiki_quote (verbatim DECK text), source (s0/s1/…),
quote (verbatim source text), verdict, detail. Re-run: scripts/review.sh $DECK
EOF
  echo "SCRATCH=$SCRATCH"; exit 2
fi

# Annotate each source against its claims, into $SCRATCH/annotated.<id>.<type>.
for i in "${!SRCS[@]}"; do
  id="s$i"; w="$SCRATCH/$id"
  typ="$("$VENV" -c "import json;print(json.load(open('$w/meta.json'))['type'])")"
  "$VENV" -c "import json;a=json.load(open('$SCRATCH/annotations.json'))['annotations'];json.dump({'annotations':[x for x in a if x.get('source')=='$id']},open('$SCRATCH/ann.$id.json','w'))"
  "$VENV" "$SKILL/annotate_${typ}.py" --source "$w/source.$typ" \
    --annotations "$SCRATCH/ann.$id.json" --out "$SCRATCH/annotated.$id.$typ"
done

# Ingest -> review.json + annotated.<id>.* in the deck folder.
"$VENV" source-review/ingest.py --workdir "$SCRATCH" --slug "$SLUG" \
  --out "$(dirname "$DECK_DIR")" --title "$SLUG"

# Install the shared in-deck viewer (+ vendored pdf.js) + add the <script> include to the deck.
mkdir -p decks/_assets/pdfjs
cp source-review/viewer/review.js decks/_assets/review.js
cp source-review/viewer/review.css decks/_assets/review.css
cp source-review/viewer/pdfjs/pdf.min.mjs source-review/viewer/pdfjs/pdf.worker.min.mjs \
   source-review/viewer/pdfjs/LICENSE decks/_assets/pdfjs/
# Append the include to the SOURCE the deck is authored in: for template
# decks that is slides.tpl.qmd (an include only in slides.qmd would be silently
# dropped by the next build_deck.py run), then rebuild so slides.qmd has it too.
# Relative to the deck folder (decks/<category>/<deck> -> ../../_assets), so it
# also resolves when the site is served under a sub-path (GitHub Pages).
UP="$(printf '%s' "$DECK" | tr -cd '/' | sed 's#/#../#g')../"
INCLUDE="\\n<!-- sr:review-include -->\\n<script src=\"${UP}_assets/review.js\"></script>\\n<link rel=\"stylesheet\" href=\"${UP}_assets/review.css\">\\n"
TPL="${MD%/*}/slides.tpl.${MD##*.}"
if [ -f "$TPL" ]; then
  if ! grep -q 'sr:review-include' "$TPL"; then
    printf "$INCLUDE" >> "$TPL"
    (cd "$DECK_DIR" && python3 build_deck.py)
  fi
elif ! grep -q 'sr:review-include' "$MD"; then
  printf "$INCLUDE" >> "$MD"
fi

echo "review wired for ${DECK} (${#SRCS[@]} source(s)); open the deck and click Review"
