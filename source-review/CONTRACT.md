# review.json contract (v0.2)

One `review.json` describes the source-verification of one deck against one or more sources.

```json
{
  "slug": "deck-slug",
  "title": "Human title",
  "generated_at": "2026-06-25",
  "sources": [
    {"id": "s0", "title": "Paper title", "doc_type": "pdf", "url": "https://arxiv.org/abs/2411.02385"}
  ],
  "tally": {"supported": 5, "not_found": 1},
  "claims": [
    {
      "idx": 0,
      "source": "s0",
      "verdict": "supported",
      "wiki_quote": "verbatim DECK text to highlight on the slide",
      "quote": "verbatim passage in the source",
      "detail": "",
      "jump": {"page": 1}
    }
  ]
}
```

## Fields
- `sources`: one entry per fetched source. `id` is a short stable key (`s0`, `s1`, …); `doc_type` is `"pdf"` | `"html"`.
- `claims[].source`: the `id` of the source this claim was checked against.
- `claims[].wiki_quote`: **required.** Verbatim text copied from the deck's `slides.qmd` that the claim summarizes — used to highlight the claim on the slide.
- `claims[].kind` (optional, default `"claim"`): `claim` | `important` | `definition` | `reference` — what role the text plays. Viewers render underline-only: **color = kind** (claim red, important yellow, definition green, reference gray); **dotted** everywhere except **wavy** when the source does not back the text (contradicted / not found).
- `claims[].verdict`: `supported` | `contradicted` | `not_found` | `unverifiable` | `reference`. `not_found` is acceptable (the claim draws on context beyond the source); only `contradicted` flags a discrepancy. `reference` is a second, non-verdict tier: text grounded in the source (terminology, paraphrase, figure-caption statements) rather than a fact-checked claim — viewers render it less prominently (dotted underline instead of a filled highlight).
- `claims[].quote`: verbatim text in the source backing the claim (`""` for not_found).
- `claims[].jump`: PDF `{"page": N}` (1-based) | HTML `{"anchor": "x-anno-<idx>"}` | `null`.
  PDF jumps MAY also carry `rects` (`[[x0,y0,x1,y1], …]`, page-fraction coordinates,
  top-left origin) locating the quote on the page. Optional — emitted for in-page
  consumers (e.g. pdf.js rect overlays); the in-deck viewer ignores it.
- `tally`: counts per present verdict.

Annotated source documents are named `annotated.<source-id>.{pdf,html}` and live beside `review.json`.
