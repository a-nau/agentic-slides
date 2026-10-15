#!/usr/bin/env python3
"""Convert a Marp deck (decks/<category>/<deck>/slides.md) into a Quarto deck, in place.

    python3 quarto/scripts/marp2qmd.py decks/templates/example [...]
        # migrate: slides.qmd replaces slides.md (template decks: slides.tpl.qmd
        # + build_deck.py rewritten and rerun); the Marp sources are deleted
    python3 quarto/scripts/marp2qmd.py --keep <deck dir>
        # Marp-sourced deck: slides.md stays the source, slides.qmd is generated
        # from it (what scripts/serve.py does for every new/changed slides.md)

The deck body is kept as-is: _quarto.yml renders with slide-level 0
(slides split on `---` like Marp), quarto/shim/marp-compat.html applies the
comment directives, and quarto/filters/marp-compat.lua keeps pandoc's HTML
structure Marp-like. This script only rewrites what pandoc cannot read the
Marp way:

- front matter: theme -> ported css, paginate/class -> comment directives on
  the first slide, title -> pagetitle (a `title` would add a Quarto title slide)
- Marp image sizing `![w:900 alt](src)` -> `![alt](src){width=900}`
- a slide separator `---` gets a blank line after it: pandoc would read
  `---` + text + `---` as a YAML metadata block, markdown-it never does
- decks not at decks/<category>/<deck> depth get their own MathJax URL
  (_quarto.yml's relative one assumes that depth)
"""
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
QROOT = REPO / "quarto"
DECKS = REPO / "decks"
DROP = {"marp", "html", "theme", "paginate", "class", "math", "size", "headingDivider"}
GENERATED = "# generated from slides.md by quarto/scripts/marp2qmd.py: edit slides.md, not this file\n"


def load_front_matter(text: str) -> dict:
    """YAML, or — like Marpit's loose YAML — one `key: value` per line with the
    value kept as a string (e.g. an unquoted description containing ': ')."""
    try:
        return yaml.safe_load(text) or {}
    except yaml.YAMLError:
        meta = {}
        for line in text.splitlines():
            k, sep, v = line.partition(":")
            if sep and k.strip() and not line[:1].isspace():
                v = v.strip()
                meta[k.strip()] = {"true": True, "false": False}.get(v, v.strip("\"'"))
        return meta


def blank_after_separators(body: str) -> str:
    """`---` slide separators (outside code fences) followed by a blank line."""
    lines, out, fence = body.split("\n"), [], None
    for i, line in enumerate(lines):
        f = re.match(r"^(```|~~~)", line)
        if f:
            fence = None if fence and line.startswith(fence) else (fence or f.group(1))
        out.append(line)
        if not fence and not f and re.match(r"^---\s*$", line) and i + 1 < len(lines) and lines[i + 1].strip():
            out.append("")
    return "\n".join(out)


def convert_text(src: str, deck_out: Path, warn, generated: bool = False) -> str:
    m = re.match(r"---\n(.*?)\n---\n(.*)", src, re.S)
    meta, body = (load_front_matter(m.group(1)), m.group(2)) if m else ({}, src)

    themes = QROOT / "themes"
    depth = len(deck_out.resolve().relative_to(REPO).parts)
    rel = Path(*[".."] * depth) / "quarto" / "themes"
    theme = meta.get("theme", "agentic")
    if not (themes / f"{theme}.css").exists():
        warn(f"theme {theme!r} has no ported css; using agentic")
        theme = "agentic"
    out = {"pagetitle": meta.get("title") or deck_out.name}
    out.update({k: v for k, v in meta.items() if k not in DROP | {"title"}})
    out["css"] = [str(rel / "base.css"), str(rel / f"{theme}.css")]
    if depth != 3:
        out["html-math-method"] = {"method": "mathjax",
                                   "url": str(rel.parent / "vendor" / "mathjax" / "tex-svg.js")}
    if meta.get("size"):
        warn(f"size {meta['size']!r} ignored (16:9 only)")

    lead = "".join(f"<!-- {k}: {str(meta[k]).lower() if isinstance(meta[k], bool) else meta[k]} -->\n"
                   for k in ("paginate", "class") if k in meta)

    body = convert_body(body, warn)
    head = yaml.safe_dump(out, sort_keys=False, allow_unicode=True, width=1000)
    return f"---\n{GENERATED if generated else ''}{head}---\n\n{lead}{body}"


def convert_body(body: str, warn) -> str:
    """The slide-text rewrites (also used per slide by the edit-pane preview)."""
    if "<style scoped" in body:
        warn("<style scoped> is not supported (left unported)")

    def image(mi):
        alt, src = mi.group(1), mi.group(2)
        size = re.findall(r"\b(w|h|width|height):(\S+)", alt)
        if not size and not re.match(r"\s*bg\b", alt):
            return mi.group(0)
        if re.match(r"\s*bg\b", alt):
            warn(f"background image {src} left as a plain image")
        alt = re.sub(r"\b(bg|center|fit|contain|cover|(w|h|width|height):\S+)\b", "", alt).strip()
        attrs = " ".join(f"{'width' if k.startswith('w') else 'height'}={v}" for k, v in size)
        return f"![{alt}]({src}){{{attrs}}}" if attrs else f"![{alt}]({src})"

    body = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)", image, body)
    return blank_after_separators(body)


def convert(deck: Path, keep: bool = False):
    deck = deck.resolve()
    if (deck / ".quarto-native").exists():  # authored in Quarto: never overwrite
        print(f"{deck.relative_to(REPO)}: native Quarto deck, skipped")
        return
    md, tpl = deck / "slides.md", deck / "slides.tpl.md"
    if not md.exists():
        raise FileNotFoundError(f"no slides.md in {deck}")
    st = md.stat()
    warns = []
    warn = lambda msg: warns.append(msg)  # noqa: E731
    if keep:
        (deck / "slides.qmd").write_text(convert_text(md.read_text(), deck, warn, generated=True))
    else:
        # Migration deletes the Marp sources: never inside a nested repo (e.g. a
        # separate decks repo under decks/), whose files this repo does not own.
        for d in [deck, *deck.parents]:
            if d == REPO:
                break
            if (d / ".git").exists():
                raise RuntimeError(f"inside a separate git repo ({d}) — use --keep")
        if tpl.exists():
            (deck / "slides.tpl.qmd").write_text(convert_text(tpl.read_text(), deck, warn))
            build = deck / "build_deck.py"
            build.write_text(build.read_text().replace("slides.tpl.md", "slides.tpl.qmd")
                             .replace('"slides.md"', '"slides.qmd"')
                             .replace("wrote slides.md", "wrote slides.qmd"))
            subprocess.run([sys.executable, str(build)], check=True, cwd=deck)
            tpl.unlink()
        else:
            (deck / "slides.qmd").write_text(convert_text(md.read_text(), deck, warn))
        md.unlink()
    # keep the Marp deck's date, so "newest first" listings stay meaningful
    for f in ("slides.qmd", "slides.tpl.qmd"):
        if (deck / f).exists():
            os.utime(deck / f, (st.st_atime, st.st_mtime))
    print(f"{deck.relative_to(REPO)}: {'slides.md -> slides.qmd' if keep else 'migrated'}")
    for w in warns:
        print(f"  warning: {w}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--keep", action="store_true", help="keep slides.md as the source; generate slides.qmd")
    ap.add_argument("decks", nargs="+", type=Path)
    args = ap.parse_args()
    failed = []
    for d in args.decks:
        try:
            convert(d, args.keep)
        except Exception as e:  # keep going; report every deck that needs a hand
            failed.append(d)
            print(f"{d}: FAILED — {type(e).__name__}: {str(e).strip().splitlines()[-1][:200]}")
    if failed:
        sys.exit(f"{len(failed)} deck(s) failed")
