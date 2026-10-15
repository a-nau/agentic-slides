#!/usr/bin/env python3
"""Turn a multi-source annotate-source workdir into UI-ready review data.

The workdir must contain:
  sources.json        — list of {id, url, title, type} source descriptors
  annotations.json    — {"annotations": [...]} where each item carries
                        "source" (matches a sources.json id) and "wiki_quote"
  annotated.<id>.pdf  — for each PDF source
  annotated.<id>.html — for each HTML source

This copies each annotated document into `<out>/<slug>/` and writes
`review.json` (see CONTRACT.md).

Usage:
  ingest.py --workdir <dir> --slug <slug> --out <dir> \
      [--title "…"] [--generated-at YYYY-MM-DD]
"""
from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
VERDICTS = ("supported", "contradicted", "not_found", "unverifiable", "reference")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _popup_text(ann: dict) -> str:
    claim = (
        ann.get("claim") or ann.get("note") or ann.get("wiki_quote") or ""
    ).strip()
    verdict = ann.get("verdict")
    head = "[Auto-Review]" + (f" {verdict.upper()}" if verdict else "")
    text = f'{head}: Matched to "{claim}" in the extracted text.'
    detail = (ann.get("detail") or "").strip()
    return f"{text} {detail}".strip() if detail else text


def _search_page(page, quote: str) -> list:
    quote = _norm(quote)
    if not quote:
        return []
    hits = page.search_for(quote)
    if hits:
        return hits
    words = quote.split(" ")
    for n in range(len(words), 3, -1):
        hits = page.search_for(" ".join(words[:n]))
        if hits:
            return hits
    if len(words) > 8:
        hits = page.search_for(" ".join(words[2:10]))
        if hits:
            return hits
    return []


def _frac_rects(page, rects) -> list[list[float]]:
    w, h = page.rect.width, page.rect.height
    out = []
    for r in rects:
        if not (w and h):
            continue
        out.append([
            round(max(0.0, min(1.0, r.x0 / w)), 5),
            round(max(0.0, min(1.0, r.y0 / h)), 5),
            round(max(0.0, min(1.0, r.x1 / w)), 5),
            round(max(0.0, min(1.0, r.y1 / h)), 5),
        ])
    return out


def _resolve_pdf_jump(doc, ann) -> dict | None:
    quote = (ann.get("quote") or "").strip()
    if not quote:
        return None
    hint = ann.get("page")
    order = []
    if isinstance(hint, int) and 1 <= hint <= len(doc):
        order.append(hint - 1)
    order += [i for i in range(len(doc)) if i != (hint - 1 if hint else -1)]
    for idx in order:
        rects = _search_page(doc[idx], quote)
        if rects:
            return {"page": idx + 1, "rects": _frac_rects(doc[idx], rects)}
    return None



def _inject_html_anchors(html_path: Path, anns: list[dict], out_path: Path) -> list[dict | None]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_path.read_text(encoding="utf-8", errors="replace"), "lxml")
    marks = [m for m in soup.find_all("mark") if "x-hl" in (m.get("class") or [])]
    used: set[int] = set()
    jumps: list[dict | None] = []
    for idx, ann in enumerate(anns):
        if not (ann.get("quote") or "").strip():
            jumps.append(None)
            continue
        want = _popup_text(ann)
        anchor = None
        for j, mark in enumerate(marks):
            if j in used:
                continue
            if (mark.get("data-note") or "").strip() == want:
                anchor = f"x-anno-{idx}"
                mark["id"] = anchor
                used.add(j)
                break
        jumps.append({"anchor": anchor} if anchor else None)
    out_path.write_text(str(soup), encoding="utf-8")
    return jumps


def _claim(idx: int, ann: dict, jump: dict | None) -> dict:
    wiki = (ann.get("wiki_quote") or "").strip()
    if not wiki:
        raise SystemExit(f"claim {idx} ({ann.get('claim')!r}) missing required wiki_quote")
    verdict = ann.get("verdict") or "unverifiable"
    kind = ann.get("kind") or ("reference" if verdict == "reference" else "claim")
    return {
        "idx": idx,
        "source": ann.get("source"),
        "kind": kind,
        "verdict": verdict,
        "wiki_quote": wiki,
        "quote": (ann.get("quote") or "").strip(),
        "detail": (ann.get("detail") or "").strip(),
        "jump": jump,
    }


def _resolve_jump(workdir: Path, src: dict, ann: dict) -> dict | None:
    """Resolve one claim's jump against its source's annotated doc (PDF only)."""
    if src["type"] == "pdf":
        import fitz
        doc = fitz.open(workdir / f"annotated.{src['id']}.pdf")
        try:
            return _resolve_pdf_jump(doc, ann)
        finally:
            doc.close()
    return None  # html handled in bulk


def build_review(workdir, slug, out_dir, title=None, generated_at=None):
    import datetime, json, shutil
    from collections import Counter
    workdir, out_dir = Path(workdir), Path(out_dir)
    srcs = json.loads((workdir / "sources.json").read_text(encoding="utf-8"))
    anns = json.loads((workdir / "annotations.json").read_text(encoding="utf-8"))["annotations"]
    by_id = {s["id"]: s for s in srcs}
    dest = out_dir / slug
    dest.mkdir(parents=True, exist_ok=True)

    html_jumps = {}
    for s in srcs:
        sid, typ = s["id"], s["type"]
        if typ == "pdf":
            shutil.copy(workdir / f"annotated.{sid}.pdf", dest / f"annotated.{sid}.pdf")
        else:
            # Pass full anns list so _inject_html_anchors uses global indices for anchor names.
            jumps = _inject_html_anchors(workdir / f"annotated.{sid}.html", anns,
                                         dest / f"annotated.{sid}.html")
            html_jumps[sid] = dict(enumerate(jumps))

    claims = []
    for idx, ann in enumerate(anns):
        sid = ann.get("source")
        if sid not in by_id:
            raise SystemExit(f"claim {idx} references unknown source {sid!r}")
        if by_id[sid]["type"] == "pdf":
            jump = _resolve_jump(workdir, by_id[sid], ann)
        else:
            jump = html_jumps[sid][idx]
        claims.append(_claim(idx, ann, jump))

    tally = Counter(c["verdict"] for c in claims)
    review = {
        "slug": slug,
        "title": title or slug,
        "generated_at": generated_at or datetime.date.today().isoformat(),
        "sources": [{"id": s["id"], "title": s.get("title") or s["id"],
                     "doc_type": s["type"], "url": s.get("url", "")} for s in srcs],
        "tally": {v: tally[v] for v in VERDICTS if tally.get(v)},
        "claims": claims,
    }
    (dest / "review.json").write_text(json.dumps(review, indent=2, ensure_ascii=False),
                                      encoding="utf-8")
    return review


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--title")
    ap.add_argument("--generated-at")
    a = ap.parse_args()
    r = build_review(Path(a.workdir), slug=a.slug, out_dir=Path(a.out),
                     title=a.title, generated_at=a.generated_at)
    tally = ", ".join(f"{k}={v}" for k, v in r["tally"].items()) or "none"
    print(f"wrote {a.out}/{a.slug}/review.json  ({len(r['claims'])} claims, "
          f"{len(r['sources'])} sources; {tally})")


if __name__ == "__main__":
    main()
