// node scripts/edit-mode.test.js — asserts for the edit-mode markdown splitter.
const assert = require("assert");
const { splitDeck, getFragment, setFragment } = require("./edit-mode.js");

const DECK = [
  "---", "marp: true", "theme: agentic", "---",
  "# Slide one", "",
  "---", "",
  "## Slide two", "```bash", "--- not a separator", "```", "",
  "---", "",
  "### Slide three", "~~~", "---", "~~~", "last line",
].join("\n");

const doc = splitDeck(DECK);
assert.strictEqual(doc.fmEnd, 4, "front-matter ends after line 4");
assert.strictEqual(doc.slides.length, 3, "three slides");
assert.strictEqual(getFragment(doc, 0), "# Slide one\n");
assert.ok(getFragment(doc, 1).includes("--- not a separator"), "fenced --- kept in slide 2");
assert.ok(getFragment(doc, 2).endsWith("last line"));

// round-trip: replacing a slide with itself is the identity
assert.strictEqual(setFragment(doc, 1, getFragment(doc, 1)), DECK, "identity round-trip");

// identity round-trips for the boundary slides (first and last)
assert.strictEqual(setFragment(doc, 0, getFragment(doc, 0)), DECK, "identity round-trip, first slide");
assert.strictEqual(
  setFragment(doc, doc.slides.length - 1, getFragment(doc, doc.slides.length - 1)),
  DECK,
  "identity round-trip, last slide"
);

// replacing slide 0 keeps everything else byte-identical
const edited = setFragment(doc, 0, "# EDITED\n");
const redoc = splitDeck(edited);
assert.strictEqual(getFragment(redoc, 0), "# EDITED\n");
assert.strictEqual(getFragment(redoc, 1), getFragment(doc, 1));
assert.strictEqual(getFragment(redoc, 2), getFragment(doc, 2));

// front-matter opener with trailing spaces (marp tolerates this)
const fmOpenWs = splitDeck(["---  ", "marp: true", "---", "# A", "---", "# B"].join("\n"));
assert.strictEqual(fmOpenWs.fmEnd, 3, "fmEnd with trailing-space opener");
assert.strictEqual(fmOpenWs.slides.length, 2, "no spurious slides from trailing-space opener");
assert.strictEqual(getFragment(fmOpenWs, 0), "# A");

// front-matter closer with trailing spaces (marp tolerates this)
const fmCloseWs = splitDeck(["---", "marp: true", "---   ", "# A", "---", "# B"].join("\n"));
assert.strictEqual(fmCloseWs.fmEnd, 3, "fmEnd with trailing-space closer");
assert.strictEqual(fmCloseWs.slides.length, 2, "no spurious slides from trailing-space closer");
assert.strictEqual(getFragment(fmCloseWs, 0), "# A");

// a slide separator with trailing spaces is still a separator (outside fences)
const sepWs = splitDeck(["# A", "---   ", "# B"].join("\n"));
assert.strictEqual(sepWs.fmEnd, 0);
assert.strictEqual(sepWs.slides.length, 2, "trailing-space separator splits slides");
assert.strictEqual(getFragment(sepWs, 1), "# B");

// no front-matter, single slide
const bare = splitDeck("# only");
assert.strictEqual(bare.fmEnd, 0);
assert.strictEqual(bare.slides.length, 1);
assert.strictEqual(getFragment(bare, 0), "# only");

console.log("edit-mode splitter: all assertions passed");
