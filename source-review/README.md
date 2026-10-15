# source-review

Source-verification kit: turn an [`annotate-source`] workdir into UI-ready review
data and an in-deck split-pane viewer. Vendored into agentic-slides
(`scripts/review.sh` drives it).

## What it owns
- `CONTRACT.md` — the `review.json` schema (the stable plug point).
- `ingest.py` — multi-source workdir → `review.json` + per-source `annotated.<id>.*`.
- `viewer/review.{js,css}` — in-deck front-end: highlight + source panel.

## What it does NOT own
The fact-check itself. The agent-driven `annotate-source` skill decomposes the
document into claims and writes `annotations.json`; `source-review` consumes the
workdir it produces. Only PDF and HTML sources are supported.

## Use

### ingest.py

The workdir must contain:
- `sources.json` — list of `{id, url, title, type}` source descriptors
- `annotations.json` — `{"annotations": [...]}` where each claim carries `source`
  (matching a `sources.json` id) and `wiki_quote`
- `annotated.<id>.pdf` or `annotated.<id>.html` — one file per source

```bash
python ingest.py --workdir <annotate-workdir> --slug <slug> --out <dir> \
    [--title "…"] [--generated-at YYYY-MM-DD]
```

Output is written to `<out>/<slug>/`:
- `review.json` — claim data, tally, and source list (see `CONTRACT.md`)
- `annotated.<id>.*` — copied/processed source documents (one per source)

### viewer/review.{js,css}

`review.js` is the in-deck front-end. A consumer page loads it once:

```html
<script src="/_assets/review.js"></script>
<link rel="stylesheet" href="/_assets/review.css">
```

On load, `review.js` fetches `review.json` beside the page. If present, a
top-right **Review** button (`#sr-btn`) appears. Clicking it:
- adds `body.sr-on` and narrows the slide area,
- wraps the current slide's claim text in `span.sr-hl` highlights,
- opens a side panel (`#sr-panel`) with an iframe (`#sr-frame`).

Clicking a highlight loads the corresponding `annotated.<id>.*` into the iframe,
jumping to the correct page (PDF: `#page=N`) or anchor (HTML: `#x-anno-N`).

A deck without `review.json` shows no button and loads no extra assets.
