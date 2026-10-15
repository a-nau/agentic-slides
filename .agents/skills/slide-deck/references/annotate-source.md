# Annotate source — highlight + fact-check a document (PDF/HTML)

Part of the slide-deck skill. Read when fact-mapping a paper deck (the
`paper-deck` skill's Phase 3 — the slides repo's `scripts/review.sh` drives
these scripts per deck), or when asked to highlight/annotate/fact-check any
paper or blog post against its source.

Highlight the passages in a source document that answer a question — or that
back (or contradict) an existing summary — and attach the extracted insight as
a popup comment on each highlight. Deliverable: an **annotated copy of the
original** plus a short **reply**.

Two modes, set by the focus you pass:

- **query** — answer a question from the document; highlight the supporting
  passages with a note each.
- **factcheck** — given an existing reply/summary, decompose it into atomic
  claims, locate each in the source, mark it `supported` / `contradicted` /
  `not_found`, and return a *corrected* reply. The common case: validating an
  LLM paper summary or fact-extraction against the real text.

The LLM step is **you** — read the extracted text, write `annotations.json`.
Deterministic scripts handle fetching and applying highlights. The scripts
live in this skill: `scripts/annotate/{fetch,annotate_pdf,annotate_html}.py`
(`$SKILL_DIR` below = this slide-deck skill directory).

## Prerequisites

Python deps (venv, never system-wide):

```bash
python3 -m venv ~/.venvs/annotate-source
~/.venvs/annotate-source/bin/pip install pymupdf beautifulsoup4 requests lxml
```

**SingleFile (optional, recommended for HTML).** For HTML URLs `fetch.py`
uses the [SingleFile](https://github.com/gildas-lormeau/SingleFile) CLI to
save a faithful, self-contained copy (CSS + images inlined). Needs Node + a
headless Chromium:

```bash
npm install -g single-file-cli      # provides the `single-file` binary
```

If `single-file` (or `npx`) is unavailable it falls back to a raw `requests`
download (page may render unstyled) and warns. Local `.html` files are used
as-is. Use the venv interpreter for every `python3` below.

## Workflow

### 1. Fetch + extract

```bash
VENV=~/.venvs/annotate-source/bin/python
WORK=/tmp/annotate/<slug>      # any fresh dir
$VENV "$SKILL_DIR/scripts/annotate/fetch.py" "<url-or-path>" --workdir "$WORK"
```

Writes `source.pdf|html`, `meta.json` (`type`, `title`, `origin`), and
`dump.txt` — page-tagged (`[[page=N]]`) for PDF, readable text for HTML.
`arxiv.org/abs/...` is normalized to the PDF automatically.

### 2. (factcheck mode) List the facts to verify first

Before locating anything, decompose the reply/summary into an explicit
numbered list of atomic facts and show it to the user. One verifiable
statement per item — split compound sentences. This list is the checklist
for step 3 and the basis for the step-5 tally. Plain query mode: skip to 3.

### 3. Read `dump.txt` and write `annotations.json`

Read `$WORK/dump.txt`, then against the focus (or the step-2 fact list)
write `$WORK/annotations.json`:

```json
{
  "mode": "query | factcheck",
  "reply": "the overall answer, or the fact-check result (see step 5)",
  "annotations": [
    {
      "quote": "verbatim text copied EXACTLY from dump.txt",
      "page": 3,
      "verdict": "supported | contradicted | not_found | unverifiable",
      "claim": "the fact/insight this passage corresponds to",
      "detail": "optional correction or extra explanation"
    }
  ]
}
```

Each highlight gets a popup comment composed as:
`[Auto-Review] <VERDICT>: Matched to "<claim>" in the extracted text. <detail>`

Rules:

- **`quote` must be copied verbatim** from `dump.txt` — located by text
  search, paraphrase will not match. One sentence or clause; long multi-line
  quotes match on a best-effort leading run.
- `claim` is the short fact the passage backs (factcheck: the exact step-2
  item). Corrections/nuance go in `detail`. Deck fact maps may omit `claim`:
  popup text then falls back to `note`, followed by the required `wiki_quote`,
  so a source highlight never displays an empty assignment.
- `page` (PDF only) is a hint — omit it and the whole document is scanned.
  Ignored for HTML.
- `verdict` drives highlight color: green `supported`, red `contradicted`,
  yellow `not_found`/`unverifiable`. Omit in query mode for neutral yellow.
- A `not_found` claim usually has **no quote** — set `"quote": ""`. It is
  recorded in the tally/reply but produces no highlight. State the gap in
  `claim`/`detail` and in `reply`.

### 4. Apply highlights

PDF:

```bash
$VENV "$SKILL_DIR/scripts/annotate/annotate_pdf.py" \
  --source "$WORK/source.pdf" --annotations "$WORK/annotations.json" \
  --out "$WORK/annotated.pdf"
```

HTML:

```bash
$VENV "$SKILL_DIR/scripts/annotate/annotate_html.py" \
  --source "$WORK/source.html" --annotations "$WORK/annotations.json" \
  --out "$WORK/annotated.html"
```

Both print `highlights applied`, `reply-only (no quote)`, any `UNMATCHED`
quotes, and a `verdicts:` tally.

### 5. Report

Give the user the path to `annotated.pdf|html` and the `reply`.

**Factcheck mode** — the reply is a result summary built from the verdicts:

- **Correct (N):** claims supported.
- **Wrong (M):** each contradicted claim — claimed vs source, with correction.
- **Not found (K):** each claim with no located support.

State counts explicitly (`N supported, M contradicted, K not found`) and list
specifics for wrong and not-found items.

Any UNMATCHED quote: fix it (re-copy verbatim from `dump.txt`) and re-run
step 4, or record it as `not_found`/unverifiable in the reply — never pretend
it was highlighted.

## Verification

- `highlights applied` ≥ 1 (unless every claim is genuinely `not_found`).
- No UNMATCHED quotes left silently — each fixed or accounted for.
- Open `annotated.pdf` and confirm highlights carry popup comments; for HTML,
  hovering a highlight shows the note.
