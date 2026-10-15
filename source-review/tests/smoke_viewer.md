# In-Deck Viewer Smoke Test (SL-7 Acceptance)

Repeatable procedure to verify `viewer/review.{js,css}` wires up correctly inside
a served deck. No Playwright installation is required — the checks below are
the acceptance criteria for SL-7.

## Setup

Serve a reviewed deck that has `review.json` beside the HTML page:

```bash
cd <deck-output-dir>   # contains index.html, review.json, annotated.<id>.*
python -m http.server 8099 &
```

## Checks

### 1 — Button appears only when review.json is present

Open `http://localhost:8099/` in a browser.

**Assert:** `document.getElementById("sr-btn")` is not null.

Open a deck page where no `review.json` exists beside the HTML.

**Assert:** `document.getElementById("sr-btn")` is null (no button injected).

### 2 — Click toggles sr-on and highlights current slide

With the deck loaded and `#sr-btn` present, click the button.

**Assert:**
- `document.body.classList.contains("sr-on")` is `true`.
- `document.querySelectorAll("section:target span.sr-hl").length >= 1`
  (at least one claim highlight on the current slide).

### 3 — Clicking a highlight loads the source in the frame

Click a `span.sr-hl` element.

**Assert:**
- `document.getElementById("sr-frame")` is not null.
- Its `src` attribute contains `annotated.<id>.` followed by either `#page=N`
  (PDF source) or `#x-anno-N` (HTML source).

### 4 — Panel closes on second button click

Click `#sr-btn` again.

**Assert:**
- `document.body.classList.contains("sr-on")` is `false`.
- `#sr-panel` is hidden or `display: none`.
