#!/usr/bin/env python3
"""Landing pages for the decks (Quarto post-render; gitignored), served by quarto/scripts/serve.py:

    decks/index.html                 /              categories, each a card with its 3 newest decks
    decks/<category>/index.html      /<category>/   every deck in the category, newest first
    decks/mrs/index.html             MR decks, merged ones under a "Merged" fold

Decks are linked as <category>/<deck>/slides.md, the URLs they have always had.
Only the listed categories are shown, so private or scratch folders never
appear. "Newest" is the deck source's mtime (marp2qmd.py keeps the Marp deck's).
Styles: landing.css next to this script.
"""
import html
import re
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DECKS = OUT = REPO / "decks"
CATEGORIES = [("tools", "Tools"), ("projects", "Projects"), ("repos", "Repos"),
              ("reading-groups", "Reading Groups"), ("paper-reviews", "Paper Reviews"),
              ("investigations", "Investigations"), ("templates", "Templates")]
MAX_PER_BOX = 3


ICON = """<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 60' width='64' height='60'%3E %3Ctitle%3Eagentic-slides%3C/title%3E %3Cpath d='M38 14 H11 a6 6 0 0 0 -6 6 v26 a6 6 0 0 0 6 6 h40 a6 6 0 0 0 6 -6 V30' fill='none' stroke='%233b82f6' stroke-width='3.5' stroke-linecap='round'/%3E %3Crect x='13' y='27' width='20' height='3.5' rx='1.75' fill='%2393c5fd' opacity='.7'/%3E %3Crect x='13' y='35' width='28' height='3.5' rx='1.75' fill='%2393c5fd' opacity='.45'/%3E %3Cpath d='M50 4 C51.5 13 53 14.5 62 16 C53 17.5 51.5 19 50 28 C48.5 19 47 17.5 38 16 C47 14.5 48.5 13 50 4Z' fill='%233b82f6'/%3E %3Ccircle cx='40' cy='5' r='2' fill='%2393c5fd'/%3E %3C/svg%3E">"""
STYLE = (Path(__file__).parent / "landing.css").read_text()


def strip_md(s: str) -> str:
    return re.sub(r"<br */?>", " ", s.replace("**", "").replace("&nbsp;", " ")).strip()


def source(deck: Path) -> Path:
    tpl = deck / "slides.tpl.qmd"
    return tpl if tpl.exists() else deck / "slides.qmd"


def title_desc(deck: Path) -> tuple[str, str]:
    text = source(deck).read_text()
    h1 = re.search(r"^# +(.+)$", text, re.M)
    title = strip_md(re.sub(r"^#+ *", "", h1.group(0))) if h1 else deck.name.replace("-", " ").title()
    fm = re.match(r"---\n(.*?)\n---\n", text, re.S)
    desc = ""
    if fm:
        d = re.search(r"^description:[ \t]*(.*)$", fm.group(1), re.M)
        if d:
            desc = d.group(1).strip().strip("'\"").replace("''", "'")
    if not desc:  # the "## " subtitle on the lead slide
        lead = re.split(r"^---\s*$", text[fm.end():] if fm else text, maxsplit=1, flags=re.M)[0]
        h2 = re.search(r"^## +(.+)$", lead, re.M)
        desc = h2.group(1) if h2 else ""
    return title, strip_md(desc)


def decks_in(cat_dir: Path) -> list[Path]:
    found = [p.parent for p in cat_dir.glob("*/slides.qmd")]
    return sorted(found, key=lambda d: source(d).stat().st_mtime, reverse=True)


def item(href: str, deck: Path, mr: str = "") -> str:
    title, desc = title_desc(deck)
    day = datetime.fromtimestamp(source(deck).stat().st_mtime).strftime("%Y-%m-%d")
    badge = f'<span class="mr">!{mr}</span>' if mr else ""
    descp = f'<p class="item-desc">{html.escape(desc)}</p>' if desc else ""
    return (f'<a class="item" href="{href}"><div class="item-top"><span class="item-name">{badge}'
            f'{html.escape(title)}</span><span class="item-date">{day}</span></div>{descp}</a>')


def mr_num(deck: Path) -> str:
    m = re.match(r"mr-(\d+)", deck.name)
    return m.group(1) if m else ""


REPO_URL = "https://github.com/a-nau/agentic-slides"
FOOT = (f'  <p class="foot"><a href="{REPO_URL}">agentic-slides</a> · code and decks under the '
        f'<a href="{REPO_URL}/blob/main/LICENSE">MIT license</a>; figures and passages quoted from '
        f'the reviewed papers belong to their authors and are not covered '
        f'(<a href="{REPO_URL}#license">details</a>).</p>\n')


def page(title: str, h1: str, subtitle: str, body: str, back: str = "") -> str:
    back_html = f'<p class="back"><a href="{back}">&larr; all decks</a></p>' if back else ""
    return (f'<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f'<title>{title}</title>\n{ICON}\n<style>\n{STYLE}\n</style>\n</head>\n<body>\n'
            f'  <h1>{h1}</h1>\n  <p class="subtitle">{subtitle}</p>\n  {body}\n  {back_html}\n{FOOT}</body>\n</html>\n')


def plural(n: int) -> str:
    return "1 deck" if n == 1 else f"{n} decks"


def cat_box(href: str, label: str, total: int, rows: list[str]) -> str:
    return (f'<section class="cat"><div class="cat-head"><a class="cat-title" href="{href}">{label}</a>'
            f'<div class="cat-right"><span class="cat-count">{plural(total)}</span>'
            f'<a class="cat-more" href="{href}">view all &rarr;</a></div></div>'
            f'<div class="list">{"".join(rows)}</div></section>')


def main() -> None:
    boxes = {}
    for d, label in CATEGORIES:
        cat = DECKS / d
        if not cat.is_dir():
            continue
        decks = decks_in(cat)
        rows = [item(f"{x.name}/slides.md", x) for x in decks]
        body = f'<div class="wrap"><div class="list">{"".join(rows)}</div></div>' if rows else \
            '<div class="wrap"><p class="empty">No decks yet.</p></div>'
        (OUT / d).mkdir(parents=True, exist_ok=True)
        (OUT / d / "index.html").write_text(
            page(f"{label} · decks", label, "Decks in this category — newest first", body, "../index.html"))
        if decks:
            boxes[d] = cat_box(f"{d}/index.html", label, len(decks),
                               [item(f"{d}/{x.name}/slides.md", x) for x in decks[:MAX_PER_BOX]])

    mrs = DECKS / "mrs"
    active = [x for x in decks_in(mrs) if x.name.startswith("mr-")] if mrs.is_dir() else []
    merged = [x for x in decks_in(mrs / "archive") if x.name.startswith("mr-")] if (mrs / "archive").is_dir() else []
    if active or merged:
        a_html = (f'<div class="list">{"".join(item(f"{x.name}/slides.md", x, mr_num(x)) for x in active)}</div>'
                  if active else '<p class="empty">No open MR decks — see Merged below.</p>')
        m_html = (f'<details class="merged"><summary>Merged · {len(merged)}</summary><div class="list">'
                  f'{"".join(item(f"archive/{x.name}/slides.md", x, mr_num(x)) for x in merged)}</div></details>'
                  if merged else "")
        (OUT / "mrs").mkdir(parents=True, exist_ok=True)
        (OUT / "mrs" / "index.html").write_text(page(
            "MR decks", "MR decks", "Per-merge-request walkthroughs — newest first",
            f'<div class="wrap">{a_html}{m_html}</div>', "../index.html"))
        newest = sorted([(x, f"mrs/{x.name}") for x in active] +
                        [(x, f"mrs/archive/{x.name}") for x in merged],
                        key=lambda t: source(t[0]).stat().st_mtime, reverse=True)[:MAX_PER_BOX]
        boxes["mrs"] = cat_box("mrs/index.html", "MR decks", len(active) + len(merged),
                                        [item(f"{p}/slides.md", x, mr_num(x)) for x, p in newest])

    order = [d for d, _ in CATEGORIES if d != "templates"] + ["mrs", "templates"]
    cards = "".join(boxes[d] for d in order if d in boxes)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "index.html").write_text(page(
        "Slide Decks", "Slide Decks", "Browse by category — most recent decks shown first",
        f'<div class="cats">{cards}</div>'))


if __name__ == "__main__":
    main()
