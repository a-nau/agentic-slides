#!/usr/bin/env python3
"""Apply highlights + popup comments to a PDF from annotations.json.

Each annotation locates its verbatim `quote` via PyMuPDF search_for, highlights
the hit, colors it by `verdict`, and attaches the `note` as a popup comment.
Quotes that span line breaks are retried as word-sequence sub-searches; quotes
that never match are reported, not silently dropped. Annotations with no quote
(e.g. a not_found claim) are skipped here — they live only in the reply.

annotations.json shape:
  {"annotations": [{"quote": str, "page": int?, "verdict": str?,
                    "claim": str, "detail": str?}, ...]}

Each popup comment reads:
  [Auto-Review] <VERDICT>: Matched to "<claim>" in the extracted text. <detail>

Verdict -> highlight color:
  supported   green   contradicted  red   not_found/unverifiable  yellow
  (absent)    yellow  (plain query-mode evidence)

Usage:
  annotate_pdf.py --source source.pdf --annotations annotations.json --out OUT.pdf
"""
import argparse
import json
import re
import sys
from collections import Counter

import fitz

COLORS = {
    "supported": (0.40, 0.80, 0.40),
    "contradicted": (0.95, 0.45, 0.45),
    "not_found": (1.00, 0.85, 0.30),
    "unverifiable": (1.00, 0.85, 0.30),
    None: (1.00, 0.90, 0.35),
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _popup_text(ann) -> str:
    claim = (
        ann.get("claim") or ann.get("note") or ann.get("wiki_quote") or ""
    ).strip()
    verdict = ann.get("verdict")
    head = "[Auto-Review]" + (f" {verdict.upper()}" if verdict else "")
    text = f'{head}: Matched to "{claim}" in the extracted text.'
    detail = (ann.get("detail") or "").strip()
    return f"{text} {detail}".strip() if detail else text


def _search_page(page, quote: str):
    """Return a list of quads for the quote on this page, or [] if not found."""
    quote = _norm(quote)
    if not quote:
        return []
    quads = page.search_for(quote, quads=True)
    if quads:
        return quads
    # Fallback 1: PyMuPDF matches within a line; long quotes often break across
    # lines. Search the longest leading word-run that still resolves.
    words = quote.split(" ")
    for n in range(len(words), 3, -1):
        sub = " ".join(words[:n])
        quads = page.search_for(sub, quads=True)
        if quads:
            return quads
    # Fallback 2: try a distinctive interior phrase (skip a leading clause).
    if len(words) > 8:
        sub = " ".join(words[2:10])
        quads = page.search_for(sub, quads=True)
        if quads:
            return quads
    return []


def _locate(doc, ann):
    """Find quads for an annotation; prefer its declared page, else scan all."""
    page_no = ann.get("page")
    order = []
    if isinstance(page_no, int) and 1 <= page_no <= len(doc):
        order.append(page_no - 1)
    order += [i for i in range(len(doc)) if i != (page_no - 1 if page_no else -1)]
    for idx in order:
        quads = _search_page(doc[idx], ann["quote"])
        if quads:
            return doc[idx], quads
    return None, []


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", required=True)
    ap.add_argument("--annotations", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with open(args.annotations, encoding="utf-8") as fh:
        anns = json.load(fh).get("annotations", [])

    doc = fitz.open(args.source)
    applied, skipped, unmatched = 0, 0, []
    verdicts = Counter()
    for ann in anns:
        verdicts[ann.get("verdict")] += 1
        quote = (ann.get("quote") or "").strip()
        if not quote:
            skipped += 1
            continue
        page, quads = _locate(doc, ann)
        if not quads:
            unmatched.append(quote[:80])
            continue
        annot = page.add_highlight_annot(quads)
        annot.set_colors(stroke=COLORS.get(ann.get("verdict"), COLORS[None]))
        annot.set_info(content=_popup_text(ann))
        annot.update()
        applied += 1

    doc.save(args.out, garbage=4, deflate=True)
    doc.close()

    print(f"highlights applied: {applied}")
    if skipped:
        print(f"reply-only (no quote): {skipped}")
    if unmatched:
        print(f"UNMATCHED ({len(unmatched)}) — not highlighted:")
        for q in unmatched:
            print(f"  - {q!r}")
    if any(v for v in verdicts if v):
        print("verdicts: " + ", ".join(
            f"{v}={verdicts[v]}" for v in
            ("supported", "contradicted", "not_found", "unverifiable")
            if verdicts.get(v)))
    print(f"wrote {args.out}")
    if unmatched and applied == 0:
        sys.exit(2)


if __name__ == "__main__":
    main()
