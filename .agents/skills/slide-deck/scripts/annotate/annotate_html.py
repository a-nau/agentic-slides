#!/usr/bin/env python3
"""Inject highlights + hover/click popups into an HTML document.

Wraps each annotation's verbatim `quote` in a <mark class="x-hl x-<verdict>"
data-note="..."> and injects a self-contained CSS+JS overlay so each highlight
shows its note as a hover tooltip (click to pin). Matching is whitespace-flexible
within a single text node; quotes that span tags fall back to a leading word-run,
and anything unmatched is reported. Output is a standalone .html.

annotations.json shape: see annotate_pdf.py. `page` is ignored for HTML.
Each popup reads: [Auto-Review] <VERDICT>: Matched to "<claim>" in the
extracted text. <detail>

Usage:
  annotate_html.py --source source.html --annotations annotations.json --out OUT.html
"""
import argparse
import json
import re
import sys
from collections import Counter

from bs4 import BeautifulSoup, NavigableString

VERDICT_CLASS = {
    "supported": "x-supported",
    "contradicted": "x-contradicted",
    "not_found": "x-notfound",
    "unverifiable": "x-notfound",
}

STYLE = """
.x-hl{background:#fff3a3;border-radius:2px;padding:0 1px;cursor:help;
 box-shadow:inset 0 -2px 0 rgba(0,0,0,.12);}
.x-hl.x-supported{background:#b8e6b8;}
.x-hl.x-contradicted{background:#f3b0b0;}
.x-hl.x-notfound{background:#ffe08a;}
#x-pop{position:fixed;max-width:340px;z-index:99999;display:none;
 background:#1f2430;color:#f2f4f8;padding:10px 12px;border-radius:8px;
 font:13px/1.45 -apple-system,Segoe UI,Roboto,sans-serif;
 box-shadow:0 6px 24px rgba(0,0,0,.35);}
#x-pop.pinned{outline:2px solid #3b82f6;}
"""

SCRIPT = """
(function(){
 var pop=document.getElementById('x-pop'),pinned=false;
 function show(el,x,y){
  var n=el.getAttribute('data-note')||'';
  pop.textContent=n;
  pop.style.display='block';
  var px=Math.min(x+12,window.innerWidth-pop.offsetWidth-12);
  var py=Math.min(y+12,window.innerHeight-pop.offsetHeight-12);
  pop.style.left=px+'px';pop.style.top=py+'px';
 }
 document.querySelectorAll('.x-hl').forEach(function(el){
  el.addEventListener('mouseenter',function(e){if(!pinned)show(el,e.clientX,e.clientY);});
  el.addEventListener('mousemove',function(e){if(!pinned&&pop.style.display==='block'){
   pop.style.left=Math.min(e.clientX+12,window.innerWidth-pop.offsetWidth-12)+'px';
   pop.style.top=Math.min(e.clientY+12,window.innerHeight-pop.offsetHeight-12)+'px';}});
  el.addEventListener('mouseleave',function(){if(!pinned)pop.style.display='none';});
  el.addEventListener('click',function(e){e.stopPropagation();pinned=true;
   pop.classList.add('pinned');show(el,e.clientX,e.clientY);});
 });
 document.addEventListener('click',function(){pinned=false;pop.classList.remove('pinned');
  pop.style.display='none';});
})();
"""


def _popup_text(ann) -> str:
    claim = (
        ann.get("claim") or ann.get("note") or ann.get("wiki_quote") or ""
    ).strip()
    verdict = ann.get("verdict")
    head = "[Auto-Review]" + (f" {verdict.upper()}" if verdict else "")
    text = f'{head}: Matched to "{claim}" in the extracted text.'
    detail = (ann.get("detail") or "").strip()
    return f"{text} {detail}".strip() if detail else text


def _quote_regex(quote: str) -> re.Pattern:
    words = [re.escape(w) for w in quote.split()]
    return re.compile(r"\s+".join(words))


def _try_wrap(soup, node: NavigableString, pattern: re.Pattern, ann) -> bool:
    m = pattern.search(str(node))
    if not m:
        return False
    text = str(node)
    mark = soup.new_tag("mark")
    cls = "x-hl"
    verdict = ann.get("verdict")
    if verdict in VERDICT_CLASS:
        cls += " " + VERDICT_CLASS[verdict]
    mark["class"] = cls
    mark["data-note"] = _popup_text(ann)
    mark.string = m.group(0)
    pieces = [text[: m.start()], mark, text[m.end():]]
    node.replace_with(*[p for p in pieces if p != ""])
    return True


def _annotate(soup, ann) -> bool:
    quote = (ann.get("quote") or "").strip()
    if not quote:
        return False
    nodes = [n for n in soup.find_all(string=True)
             if n.parent.name not in ("script", "style") and n.strip()]
    full = _quote_regex(quote)
    for node in nodes:
        if _try_wrap(soup, node, full, ann):
            return True
    # Fallback: leading word-run (quote may span tags); needs >=4 words.
    words = quote.split()
    if len(words) >= 4:
        lead = _quote_regex(" ".join(words[:6]))
        for node in nodes:
            if _try_wrap(soup, node, lead, ann):
                return True
    return False


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", required=True)
    ap.add_argument("--annotations", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with open(args.annotations, encoding="utf-8") as fh:
        anns = json.load(fh).get("annotations", [])
    with open(args.source, encoding="utf-8", errors="replace") as fh:
        soup = BeautifulSoup(fh.read(), "lxml")

    applied, skipped, unmatched = 0, 0, []
    verdicts = Counter()
    for ann in anns:
        verdicts[ann.get("verdict")] += 1
        quote = (ann.get("quote") or "").strip()
        if not quote:
            skipped += 1
            continue
        if _annotate(soup, ann):
            applied += 1
        else:
            unmatched.append(quote[:80])

    head = soup.head or soup.html
    style = soup.new_tag("style")
    style.string = STYLE
    head.append(style)
    pop = soup.new_tag("div", id="x-pop")
    (soup.body or soup).append(pop)
    script = soup.new_tag("script")
    script.string = SCRIPT
    (soup.body or soup).append(script)

    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(str(soup))

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
