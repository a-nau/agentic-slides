"""CLI: turn a rendered deck HTML (reveal.js, loaded in its print view) into an editable .pptx.

    python -m scripts.pptx_export RENDERED_HTML OUT_PPTX [--png-dir DIR] [--dump-model FILE]

Rendering (markdown -> HTML) is done upstream by scripts/export.sh via Quarto;
this tool does the extract + build stages.
"""

import argparse
import json
import os
import sys
import tempfile

from . import build, extract


def _convert(args, png_dir):
    model = extract.extract_html(args.html, png_dir=png_dir)

    if args.dump_model:
        with open(args.dump_model, "w") as fh:
            json.dump(model, fh, indent=2)

    n_text = sum(1 for s in model["slides"] for e in s["elements"]
                 if e["kind"] == "text")
    n_fig = sum(1 for s in model["slides"] for e in s["elements"]
                if e["kind"] == "figure")
    print(f"  extracted {len(model['slides'])} slides, "
          f"{n_text} text boxes, {n_fig} figures")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    build.build_pptx(model, args.out)
    print(f"  ✓ {args.out}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="scripts.pptx_export")
    ap.add_argument("html", help="rendered deck HTML (decks/<category>/<deck>/slides.html)")
    ap.add_argument("out", help="output .pptx path")
    ap.add_argument("--png-dir", help="dir for figure PNG fallbacks "
                    "(default: a temp dir)")
    ap.add_argument("--dump-model", help="also write the slide-model JSON here")
    args = ap.parse_args(argv)

    if not os.path.isfile(args.html):
        ap.error(f"HTML not found: {args.html}")

    if args.png_dir:
        _convert(args, args.png_dir)
    else:
        with tempfile.TemporaryDirectory(prefix="pptx-fig-") as png_dir:
            _convert(args, png_dir)


if __name__ == "__main__":
    sys.exit(main())
