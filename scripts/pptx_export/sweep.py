"""Dev tool: score every slide of one or more decks by visual difference
between the rendered deck and the editable pptx, and rank the worst.

    .venv/bin/python -m scripts.pptx_export.sweep <deck> [<deck> ...]

Reuses compare.py's renderers; prints a ranking and writes side-by-side
images for the worst slides to exports/compare/<deck>/.
"""

import math
import os
import sys

from PIL import Image

from . import compare


def _rms(a: Image.Image, b: Image.Image) -> float:
    size = (320, 180)
    a = a.convert("L").resize(size)
    b = b.convert("L").resize(size)
    pa, pb = a.tobytes(), b.tobytes()
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(pa, pb)) / len(pa))


def sweep(deck: str) -> list[tuple[float, str, int]]:
    base = os.path.join(compare.REPO, "exports", "compare", deck.replace("/", "_"))
    om, pm = os.path.join(base, "deck"), os.path.join(base, "pptx")
    orig = compare.render_deck_pngs(deck, om)
    pptx_path = os.path.join(compare.REPO, "exports", f"{deck}.editable.pptx")
    pptx = compare.render_pptx_pngs(pptx_path, pm)

    scores = []
    for i in range(min(len(orig), len(pptx))):
        a = Image.open(os.path.join(om, orig[i]))
        b = Image.open(os.path.join(pm, pptx[i]))
        scores.append((_rms(a, b), deck, i + 1))
    return scores


def main(argv=None):
    argv = argv or sys.argv[1:]
    all_scores = []
    for deck in argv:
        scores = sweep(deck)
        all_scores.extend(scores)
        mean = sum(s for s, _, _ in scores) / max(1, len(scores))
        print(f"{deck}: {len(scores)} slides, mean diff {mean:.1f}")

    all_scores.sort(reverse=True)
    print("\n=== worst slides ===")
    for score, deck, num in all_scores[:15]:
        base = os.path.join(compare.REPO, "exports", "compare",
                            deck.replace("/", "_"))
        om, pm = os.path.join(base, "deck"), os.path.join(base, "pptx")
        orig = sorted(f for f in os.listdir(om) if f.startswith("orig."))
        pptx = sorted(f for f in os.listdir(pm) if f.startswith("pptx-"))
        out = os.path.join(base, f"cmp-{num:02d}.png")
        compare.stitch(os.path.join(om, orig[num - 1]),
                       os.path.join(pm, pptx[num - 1]), out)
        print(f"{score:6.1f}  {deck} slide {num}  -> {out}")


if __name__ == "__main__":
    main()
