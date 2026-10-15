#!/usr/bin/env bash
#
# Scaffold a new deck with the agentic theme.
#   Usage: scripts/new_deck.sh <category>/<name> ["Title"]
#   e.g.   scripts/new_deck.sh tools/my-topic "My Topic"
set -euo pipefail
cd "$(dirname "$0")/.."

[ $# -ge 1 ] && [[ "$1" =~ ^[^/]+/[^/]+$ ]] || { echo "usage: $0 <category>/<name> [\"Title\"]" >&2; exit 1; }
dir="decks/$1"
title="${2:-$(basename "$1" | awk -F- '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) substr($i,2)} 1')}"
[ ! -e "$dir/slides.qmd" ] || { echo "$dir/slides.qmd already exists" >&2; exit 1; }

mkdir -p "$dir/images"
cat > "$dir/slides.qmd" <<MD
---
pagetitle: $title
css:
- ../../../quarto/themes/base.css
- ../../../quarto/themes/agentic.css
---

<!-- paginate: true -->
<!-- _class: title -->

<p class="kicker">Deck type</p>

# $title

## One sentence on what this deck is about

<p class="byline">Who it is for · date</p>

---

## Each slide title states its point

- Content here
MD
echo "created $dir/slides.qmd — live at http://localhost:8093/$1/slides.md (with scripts/start.sh running)"
