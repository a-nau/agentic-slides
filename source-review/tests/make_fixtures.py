"""Generate a two-source (PDF + HTML) ingest fixture workdir."""
import json
from pathlib import Path

import fitz  # pymupdf

HERE = Path(__file__).parent / "fixtures"


def _popup_text(ann: dict) -> str:
    claim = (
        ann.get("claim") or ann.get("note") or ann.get("wiki_quote") or ""
    ).strip()
    verdict = ann.get("verdict")
    head = "[Auto-Review]" + (f" {verdict.upper()}" if verdict else "")
    text = f'{head}: Matched to "{claim}" in the extracted text.'
    detail = (ann.get("detail") or "").strip()
    # NOTE: must stay in sync with ingest._popup_text (HTML data-note matching).
    return f"{text} {detail}".strip() if detail else text


def make_workdir() -> Path:
    wd = HERE / "multi_workdir"
    wd.mkdir(parents=True, exist_ok=True)

    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "Alpha on page one.")
    doc.new_page().insert_text((72, 72), "Beta claim sentence on page two.")
    doc.save(wd / "annotated.s0.pdf"); doc.close()

    a = {"quote": "Highlighted phrase.", "verdict": "supported", "detail": "",
         "wiki_quote": "the phrase"}
    import html as _html
    note = _html.escape(_popup_text(a), quote=True)
    (wd / "annotated.s1.html").write_text(
        "<!doctype html><html><body><p>Intro. "
        f'<mark class="x-hl x-supported" data-note="{note}">Highlighted phrase.</mark>'
        " Outro.</p></body></html>", encoding="utf-8")

    (wd / "sources.json").write_text(json.dumps([
        {"id": "s0", "url": "http://x/p.pdf", "title": "PDF Source", "type": "pdf"},
        {"id": "s1", "url": "http://x/p.html", "title": "HTML Source", "type": "html"},
    ]))
    (wd / "annotations.json").write_text(json.dumps({"annotations": [
        {"source": "s0", "quote": "Beta claim sentence on page two.", "page": 1,
         "verdict": "supported", "claim": "Beta is on page two.",
         "wiki_quote": "Beta on the second slide", "detail": ""},
        {"source": "s1", "quote": "Highlighted phrase.", "verdict": "supported",
         "wiki_quote": "the phrase", "detail": ""},
        {"source": "s0", "quote": "", "verdict": "not_found",
         "claim": "Gamma is nowhere.", "wiki_quote": "Gamma claim", "detail": "Not in source."},
    ]}))
    return wd


if __name__ == "__main__":
    print(make_workdir())
