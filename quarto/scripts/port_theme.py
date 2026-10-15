#!/usr/bin/env python3
"""Port a Marp theme CSS (themes/*.css) to a reveal.js stylesheet for Quarto.

    python3 quarto/scripts/port_theme.py themes/agentic.css > quarto/themes/agentic.css
    python3 quarto/scripts/port_theme.py - < deck.css   # filter mode, used at render
                                                         # time for a deck's <style>

Marp styles one flat list of `<section>` slides with bare element selectors.
Under Quarto (slide-level 0) every slide is a `section.slide` (nested
`<section>` elements from pandoc's section-divs lack `.slide`), so each selector
is rescoped:

    section.lead h1   ->  .reveal .slides section.slide.lead h1
    h2 + p em         ->  .reveal .slides section.slide h2 + p em
    :root             ->  :root (unchanged)

reveal.js hides every slide but the current one (inline `display: block` on
`section.present`). A Marp rule that sets `display` on the slide itself is
split: the `display` declaration (made !important to beat the inline style)
only applies to the present slide and to all slides in print/scroll views;
otherwise it would un-hide every slide of that class. reveal's print view
(PDF, editable-PPTX extraction) also forces `padding/margin: 0 !important` on
slides, so a slide rule's padding and margin get an !important print copy.

Marpit makes `rem` relative to the slide, not <html>: a slide rule that sets
`font-size` also sets `--marpit-root-font-size`, and every `Nrem` becomes
`calc(var(--marpit-root-font-size, 1rem) * N)`. Same here, so a deck's
`section.small { font-size: .8em }` shrinks its headings too, as under Marp.
"""
import re
import sys

SLIDE = ".reveal .slides section.slide"
ROOT_FS = "--marpit-root-font-size"
SKIP = re.compile(r"(\"[^\"]*\"|'[^']*'|(?:attr|url|var)\([^)]*\))")


def marpit_rem(body: str) -> str:
    parts = SKIP.split(body)
    return "".join(p if i % 2 else re.sub(r"(\d*\.?\d+)rem\b",
                   rf"calc(var({ROOT_FS}, 1rem) * \1)", p) for i, p in enumerate(parts))


def split_top(css: str):
    """Yield (prelude, body) for each top-level block, plus bare `@...;` statements."""
    i, n = 0, len(css)
    while i < n:
        j = css.find("{", i)
        if css[i:].lstrip().startswith("@") and (j == -1 or ";" in css[i:j]):
            # `@import url('…;…');` — find the `;` outside quotes and parens.
            k, depth, quote = i, 0, None
            while k < n:
                c = css[k]
                if quote:
                    quote = None if c == quote else quote
                elif c in "'\"":
                    quote = c
                elif c == "(":
                    depth += 1
                elif c == ")":
                    depth -= 1
                elif c == ";" and depth == 0:
                    break
                elif c == "{" and depth == 0:
                    k = -1
                    break
                k += 1
            if k != -1:
                yield css[i:k].strip() + ";", None
                i = k + 1
                continue
        if j == -1:
            break
        depth, m = 1, j + 1
        while depth and m < n:
            depth += {"{": 1, "}": -1}.get(css[m], 0)
            m += 1
        yield css[i:j].strip(), css[j + 1 : m - 1]
        i = m


def rescope(sel: str) -> str:
    sel = sel.strip()
    if sel.startswith((":root", "html", "body", ".reveal")) or "section.slide" in sel:
        return sel  # global, or already ported (idempotent)
    m = re.match(r"section((?:[.:#\[][^\s>+~]*)?)(.*)$", sel)
    if m:
        own, rest = m.groups()
        return SLIDE + own + rest
    return f"{SLIDE} {sel}"


def is_slide_itself(sel: str) -> bool:
    return re.fullmatch(r"section(?:[.#\[][^\s>+~:]*)?", sel.strip()) is not None


def shown(sel: str) -> list[str]:
    """`section.lead` -> selectors matching only when that slide is displayed."""
    s = rescope(sel)
    return [s + ".present", f".reveal-print {s}", f".reveal-scroll {s}"]


def port(css: str) -> str:
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out = []
    for prelude, body in split_top(css):
        if body is None:
            out.append(prelude)
        elif prelude.startswith("@media") or prelude.startswith("@supports"):
            out.append(f"{prelude} {{\n{port(body)}\n}}")
        elif prelude.startswith("@"):
            out.append(f"{prelude} {{{body}}}")
        else:
            sels = prelude.split(",")
            fs = re.findall(r"(?:^|;)\s*font-size\s*:\s*([^;]+)", body)
            if fs and any(is_slide_itself(x) for x in sels):
                body = body.rstrip().rstrip(";") + f"; {ROOT_FS}: {fs[-1].strip()};"
            body = marpit_rem(body)
            decls = [d for d in body.split(";") if d.strip()]
            disp = [d for d in decls if re.match(r"\s*display\s*:", d)]
            if disp and all(is_slide_itself(x) for x in sels):
                body = ";".join(d for d in decls if d not in disp) + ";"
                out.append(",\n".join(t for x in sels for t in shown(x))
                           + " {" + ";".join(d.strip() + " !important" for d in disp) + ";}")
            out.append(",\n".join(rescope(x) for x in sels) + f" {{{body}}}")
            box = [d for d in decls if re.match(r"\s*(padding|margin)(-\w+)?\s*:", d)]
            if box and all(is_slide_itself(x) for x in sels):
                out.append(",\n".join(f".reveal-print {rescope(x)}" for x in sels)
                           + " {" + ";".join(d.strip().removesuffix("!important").strip()
                                             + " !important" for d in box) + ";}")
    return "\n".join(out)


if __name__ == "__main__":
    if sys.argv[1] == "-":  # filter mode (filters/marp-compat.lua): a deck's own <style>
        sys.stdout.write(port(sys.stdin.read()))
    else:
        src = open(sys.argv[1]).read()
        print(f"/* Generated by quarto/scripts/port_theme.py from {sys.argv[1]} — do not edit. */")
        print(port(src))
