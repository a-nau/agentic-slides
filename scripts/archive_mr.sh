#!/usr/bin/env bash
#
# Archive a merged MR deck: move it under decks/mrs/archive/ and
# regenerate the landing pages (it then shows under the collapsible "Merged"
# section instead of the active list). Run this once an MR is merged.
#
#   Usage: scripts/archive_mr.sh <iid|folder>
#     scripts/archive_mr.sh 42
#     scripts/archive_mr.sh mr-42-add-cache
set -euo pipefail
cd "$(dirname "$0")/.."

arg="${1:?Usage: $0 <iid|folder>   e.g. 42  or  mr-42-add-cache}"
MR_DIR="decks/mrs"

src=""
if [ -d "$MR_DIR/$arg" ]; then
    src="$MR_DIR/$arg"                       # exact folder name
else
    iid="${arg#mr-}"; iid="${iid%%-*}"       # pull the numeric iid out of either form
    for d in "$MR_DIR"/mr-"${iid}"-*/; do
        [ -d "$d" ] && { src="${d%/}"; break; }
    done
fi

[ -n "$src" ] && [ -d "$src/" ] || { echo "No active MR deck matching '$arg' under $MR_DIR/." >&2; exit 1; }

mkdir -p "$MR_DIR/archive"
dst="$MR_DIR/archive/$(basename "$src")"
[ -e "$dst" ] && { echo "Already archived: $dst" >&2; exit 1; }

git mv "$src" "$dst" 2>/dev/null || mv "$src" "$dst"
python3 quarto/scripts/gen_index.py

echo "Archived $(basename "$src") → $dst"
echo "Commit to record the move and the refreshed landing page."
