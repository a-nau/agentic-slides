#!/usr/bin/env python3
"""Ingest PDF annotations into a deck's comments.json.

    .venv/bin/python scripts/ingest_pdf_comments.py <annotated.pdf> <category>/<deck>

Someone reviews the exported PDF in any reader (sticky notes, highlights with
notes, free-text boxes) and sends the annotated file back; this pulls every
annotation that carries text into decks/<deck>/comments.json — the same file
the in-browser comment layer writes — so agents pick them up identically.
PDF page numbers map 1:1 to slide pages. The highlighted text itself is not
recoverable from a PDF, so the quote is a placeholder (no slide highlight in
the browser; agents work from page + note + captured slide_src).
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from scripts.pptx_export.export_server import add_comment, resolve_deck  # noqa: E402

# annotation subtypes that carry reviewer intent
SUBTYPES = {"/Text": "note", "/FreeText": "text box", "/Highlight": "highlight",
            "/Underline": "underline", "/Squiggly": "squiggly", "/StrikeOut": "strike-out"}


def main(argv: list[str]) -> int:
    try:
        from pypdf import PdfReader
    except ImportError:
        print("pypdf missing: .venv/bin/pip install pypdf", file=sys.stderr)
        return 1
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 1
    pdf_path, deck = Path(argv[0]), argv[1]
    if resolve_deck(REPO, deck) is None:
        print(f"unknown deck: {deck}", file=sys.stderr)
        return 1

    reader = PdfReader(pdf_path)
    added = skipped = 0
    for pageno, page in enumerate(reader.pages, start=1):
        for annot in (page.get("/Annots") or []):
            a = annot.get_object()
            subtype = str(a.get("/Subtype", ""))
            if subtype not in SUBTYPES:
                continue
            note = str(a.get("/Contents", "") or "").strip()
            if not note:
                skipped += 1  # e.g. a bare highlight without a typed note
                continue
            status, result = add_comment(REPO, deck, {
                "page": pageno,
                "quote": f"(pdf {SUBTYPES[subtype]}, p.{pageno})",
                "comment": note,
                "author": str(a.get("/T", "") or "pdf annotation"),
            })
            if status != 200:
                print(f"p.{pageno}: rejected — {result}", file=sys.stderr)
                continue
            added += 1
            print(f"p.{pageno}: {SUBTYPES[subtype]} — {note[:60]}")
    print(f"\n{added} comment(s) added to decks/{deck}/comments.json"
          + (f" ({skipped} empty annotation(s) skipped)" if skipped else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
