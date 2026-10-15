# Publishing

## Publishing on GitHub Pages

[`.github/workflows/pages.yml`](../.github/workflows/pages.yml) publishes every
deck on each push to `main`: [`scripts/build_site.sh`](../scripts/build_site.sh)
renders each deck with Quarto and generates the landing pages. One-time setup:
**Settings → Pages → Source: GitHub Actions**.

Downloads are off by default. To prebuild them — self-contained **HTML**,
**editable PPTX** and **PDF** for every deck (`scripts/export.sh`, about 20 s
per deck) — run the workflow by hand: **Actions → Deploy decks to GitHub Pages
→ Run workflow**, tick **exports**. The next push to `main` publishes without
them again. Locally that is `SITE_EXPORTS=1 scripts/build_site.sh`.

Preview locally with `scripts/build_site.sh` (output in `_site/`, needs the
`scripts/setup.sh` toolchain, plus Google Chrome for the exports) and any
static file server, e.g. `python3 -m http.server -d _site 8197`.

Site layout: `decks/<category>/<deck>/slides.html` (the pre-Quarto URLs
`<category>/<deck>/slides.html` redirect there), `exports/<category>/<deck>.*`
(with exports on), and `quarto/themes/` + `quarto/vendor/` for the decks' theme and MathJax.

The published site is read-only: the deck's download buttons (with exports
on) link the prebuilt files, while edit mode and comments need the local
server and are hidden. The fact-check results (`review.json`, which holds a verbatim quote
from the source for every claim) and the `annotated.*` source copies (full
third-party papers/pages) are gitignored and never published, so the site
has no fact-check pane; run `scripts/review.sh` locally to see it. Slide
comments (`comments.json`) are gitignored too.

The workflows (and `scripts/setup.sh`) pin every action to a commit SHA, every Python dependency to an
exact version and its SHA-256 hashes (`scripts/pptx_export/requirements.lock`,
installed with `pip --require-hashes`), the Quarto release download to its
published SHA-256 (`quarto/scripts/setup.sh`), and the npm-fetched MathJax and
fonts to their file hashes (`quarto/vendor.sha256`);
the build job only reads the repo, and only the deploy job may publish. To
change a Python version, edit `.github/constraints.txt` and regenerate the lock
with the `pip-compile` command at its top. [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)
runs the unit tests on every push and pull request.
