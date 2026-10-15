"use strict";

// Run: node --test scripts/comments.browser.test.js
// Uses an installed Playwright (JS package or Python driver's JS package).
// All browser requests are intercepted; no running deck/server is required.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { execFileSync } = require("node:child_process");
const { test, before, after } = require("node:test");

function loadPlaywright() {
  if (process.env.PLAYWRIGHT_MODULE) return require(process.env.PLAYWRIGHT_MODULE);
  try { return require("playwright"); } catch (_) {}
  const driver = execFileSync(process.env.PYTHON || "python", ["-c",
    "import pathlib, playwright; print(pathlib.Path(playwright.__file__).parent / 'driver' / 'package')",
  ], { encoding: "utf8" }).trim();
  return require(driver);
}

const source = fs.readFileSync(path.join(__dirname, "comments.js"), "utf8");
const created = "2026-10-01T09:12:34.000Z";
const fixture = `<!doctype html><html><head><meta charset="utf-8"><style>
  body { margin: 0; background: #171717; color: #eee; font: 18px/28px sans-serif; }
  section { margin: 36px; width: 700px; }
  p { margin: 24px 0; }
  #multiline { width: 620px; }
  #tipcard { position: fixed; display: none; width: 280px; padding: 16px;
    background: #111; color: white; z-index: 9999; pointer-events: none; }
  .bespoke-marp-osc { position: fixed; bottom: 12px; left: 12px; }
</style></head><body>
  <section id="1"><a class="slide-id" id="11111111-1111-4111-8111-111111111111"></a>
    <h1>Comment regression fixture</h1>
    <p id="multiline">The first selected line extends much farther to the right.<br>The last line.</p>
    <p id="legacy">Legacy quoted words remain available.</p>
    <p><span id="trigger" data-tiphead="Tooltip heading" data-tip="A detailed explanation for the tooltip target.">Tooltip trigger words</span></p>
    <p>Learn <span id="ambiguous-tip-one" data-tip="First explanation.">Learn more</span>
      <span id="ambiguous-tip-two" data-tip="Second explanation.">Learn more</span></p>
    <svg width="600" height="60"><text id="svg-label" x="0" y="28" fill="white">SVG label stays visible</text></svg>
  </section>
  <div id="tipcard"><div class="tip-head"></div><div class="tip-body"></div></div>
  <div class="bespoke-marp-osc"></div>
  <script>
    window.DeckClient = {
      deckInfo: function () { return {deck: 'fixture', base: location.origin}; },
      onOsc: function (callback) { callback(document.querySelector('.bespoke-marp-osc')); }
    };
    // Existing deck tooltip behavior, e.g. paper-reviews/levjepa/slides.md.
    document.addEventListener('mousemove', function (ev) {
      var tip = document.getElementById('tipcard');
      var trigger = ev.target.closest && ev.target.closest('[data-tip]');
      if (trigger) {
        tip.firstChild.textContent = trigger.getAttribute('data-tiphead') || 'Explanation';
        tip.lastChild.textContent = trigger.getAttribute('data-tip');
        tip.style.display = 'block';
        tip.style.left = (ev.clientX + 16) + 'px';
        tip.style.top = (ev.clientY + 16) + 'px';
      } else tip.style.display = 'none';
    });
  </script>
</body></html>`;

let browser;
before(async () => {
  browser = await loadPlaywright().chromium.launch({ headless: true });
});
after(async () => { if (browser) await browser.close(); });

async function setup(t, initialComments = [], viewport = { width: 1000, height: 760 }) {
  const context = await browser.newContext({ viewport });
  t.after(() => context.close());
  const state = { comments: structuredClone(initialComments), posts: [], failEdits: false };
  await context.route("**/*", async route => {
    const url = new URL(route.request().url());
    if (url.pathname === "/fixture") return route.fulfill({ contentType: "text/html", body: fixture });
    if (url.pathname === "/healthz") return route.fulfill({ json: { ok: true } });
    if (url.pathname !== "/comments/fixture") return route.abort();
    if (route.request().method() === "POST") {
      const payload = route.request().postDataJSON();
      state.posts.push(payload);
      if (state.failEdits) return route.fulfill({
        status: state.failEdits === true ? 503 : state.failEdits,
        json: { error: "Comment update rejected" },
      });
      if (payload.action === "add") {
        const comment = structuredClone(payload.comment);
        comment.quote = comment.quote.trim();
        if (comment.anchor) Object.keys(comment.anchor).forEach(key => {
          if (typeof comment.anchor[key] === "string") comment.anchor[key] = comment.anchor[key].trim();
        });
        state.comments.push({ ...comment, id: "added-comment", created, status: "open" });
      } else {
        const comment = state.comments.find(c => c.id === payload.id);
        assert.ok(comment, "updates address an existing comment ID");
        if (payload.action === "edit") {
          const patch = typeof payload.comment === "object" ? payload.comment : { comment: payload.comment };
          comment.comment = patch.comment;
          comment.updated = "2026-10-02T10:20:30.000Z";
          comment.history = [
            { action: "created", at: created, comment: "Original instruction", author: "Alex", status: "open" },
            { action: "edited", at: comment.updated, comment: comment.comment, author: comment.author, status: "open" },
          ];
        } else if (payload.action === "resolve") comment.status = "resolved";
        else if (payload.action === "reopen") comment.status = "open";
      }
    }
    return route.fulfill({ json: { comments: state.comments } });
  });
  const page = await context.newPage();
  page.setDefaultTimeout(2500);
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  t.after(() => assert.deepEqual(errors, [], "comment interactions must not throw in the browser"));
  await page.goto("http://comments.test/fixture#1");
  await page.addScriptTag({ content: source });
  await page.waitForFunction(() => !!document.querySelector(".cm-badge"));
  return { page, state };
}

// Use real DOM ranges and rendered glyph geometry, with deterministic endpoints.
async function selectText(page, selector, { backward = false, release, blocked = false } = {}) {
  const pointer = await page.locator(selector).evaluate((element, options) => {
    const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    const first = nodes[0], last = nodes[nodes.length - 1];
    const range = document.createRange();
    range.setStart(first, 0); range.setEnd(last, last.length);
    const rects = [...range.getClientRects()].filter(r => r.width > 0 && r.height > 0);
    const edge = options.backward ? rects[0] : rects[rects.length - 1];
    const pointer = options.release || {
      x: options.backward ? edge.left + 1 : edge.right - 1,
      y: edge.top + edge.height / 2,
    };
    element.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, clientX: pointer.x, clientY: pointer.y, button: 0 }));
    element.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true, clientX: pointer.x, clientY: pointer.y, button: 0 }));
    const selection = getSelection();
    selection.removeAllRanges();
    selection.setBaseAndExtent(options.backward ? last : first, options.backward ? last.length : 0,
      options.backward ? first : last, options.backward ? 0 : last.length);
    if (options.blocked) element.addEventListener("mouseup", ev => ev.stopPropagation(), { once: true });
    element.dispatchEvent(new MouseEvent("mouseup", { bubbles: true, clientX: pointer.x, clientY: pointer.y, button: 0 }));
    return pointer;
  }, { backward, release, blocked });
  await page.locator("#cm-chip").waitFor({ state: "visible" });
  return pointer;
}

function oldComment(extra = {}) {
  return { id: "legacy-id", page: 1, quote: "Legacy quoted words", comment: "Original instruction",
    author: "Alex", status: "open", created, ...extra };
}

test("multiline selection keeps comment button by the release point", async t => {
  const { page } = await setup(t);
  const pointer = await selectText(page, "#multiline");
  const chip = await page.locator("#cm-chip").boundingBox();
  assert.ok(Math.abs(chip.x - pointer.x) < 40, `chip x=${chip.x}, release x=${pointer.x}`);
  assert.ok(Math.abs(chip.y - pointer.y) < 50, `chip y=${chip.y}, release y=${pointer.y}`);
});

test("backward multiline selection uses the active end", async t => {
  const { page } = await setup(t);
  const pointer = await selectText(page, "#multiline", { backward: true });
  const chip = await page.locator("#cm-chip").boundingBox();
  assert.ok(Math.abs(chip.x - pointer.x) < 40, `chip x=${chip.x}, release x=${pointer.x}`);
  assert.ok(Math.abs(chip.y - pointer.y) < 50);
});

test("comment button and editor stay inside a narrow viewport", async t => {
  const { page } = await setup(t, [], { width: 320, height: 480 });
  await selectText(page, "#legacy", { release: { x: 315, y: 470 } });
  for (const selector of ["#cm-chip", "#cm-editor"]) {
    if (selector === "#cm-editor") await page.locator("#cm-chip").click();
    const bounds = await page.locator(selector).boundingBox();
    assert.ok(bounds.x >= 0 && bounds.y >= 0, `${selector} begins inside viewport`);
    assert.ok(bounds.x + bounds.width <= 320, `${selector} right edge stays visible`);
    assert.ok(bounds.y + bounds.height <= 480, `${selector} bottom stays visible`);
  }
});

test("legacy comments and SVG labels retain visible highlights", async t => {
  const { page } = await setup(t, [oldComment(), oldComment({ id: "svg-id", quote: "SVG label stays visible" })]);
  await page.locator('#legacy .cm-hl[data-id="legacy-id"]').waitFor();
  const svgHighlight = page.locator('#svg-label .cm-hl[data-id="svg-id"]');
  await svgHighlight.waitFor();
  assert.equal(await svgHighlight.evaluate(el => el.namespaceURI), "http://www.w3.org/2000/svg");
  assert.equal(await svgHighlight.evaluate(el => el.tagName.toLowerCase()), "tspan");
  assert.ok((await svgHighlight.boundingBox()).width > 0);
});

test("comments can be edited without changing ID, quote, or creation time", async t => {
  const { page, state } = await setup(t, [oldComment()]);
  await page.locator('.cm-hl[data-id="legacy-id"]').click();
  await page.locator("#cm-edit").click();
  assert.equal(await page.locator("#cm-editor textarea").inputValue(), "Original instruction");
  await page.locator("#cm-editor textarea").fill("Clarified instruction");
  await page.locator("#cm-save").click();
  await page.locator("#cm-editor").waitFor({ state: "hidden" });
  assert.equal(state.posts.length, 1);
  assert.equal(state.posts[0].action, "edit");
  assert.equal(state.posts[0].id, "legacy-id");
  assert.equal(state.posts[0].expected_updated, created);
  assert.equal(state.comments[0].created, created);
  assert.equal(state.comments[0].quote, "Legacy quoted words");
  assert.equal(state.comments[0].comment, "Clarified instruction");
  await page.locator('.cm-hl[data-id="legacy-id"]').click();
  await page.locator("#cm-history summary").click();
  const history = await page.locator("#cm-history").innerText();
  assert.match(history, /Original instruction/);
  assert.match(history, /Clarified instruction/);
  const timestamps = await page.locator("#cm-history time").evaluateAll(elements =>
    elements.map(el => el.getAttribute("datetime") || el.title));
  assert.deepEqual(timestamps, [created, "2026-10-02T10:20:30.000Z"]);
});

test("failed edits retain the draft and do not queue a duplicate comment", async t => {
  const { page, state } = await setup(t, [oldComment()]);
  state.failEdits = true;
  await page.locator('.cm-hl[data-id="legacy-id"]').click();
  await page.locator("#cm-edit").click();
  await page.locator("#cm-editor textarea").fill("Keep this unsaved edit");
  await page.locator("#cm-save").click();
  await page.locator("#cm-toast").waitFor({ state: "visible" });
  assert.ok(await page.locator("#cm-editor").isVisible());
  assert.equal(await page.locator("#cm-editor textarea").inputValue(), "Keep this unsaved edit");
  assert.equal(state.comments[0].comment, "Original instruction");
  assert.deepEqual(await page.evaluate(() => JSON.parse(localStorage.getItem("cm-queue:fixture") || "[]")), []);
  state.failEdits = false;
  await page.locator("#cm-save").click();
  await page.locator("#cm-editor").waitFor({ state: "hidden" });
  assert.equal(state.comments[0].comment, "Keep this unsaved edit");
});

test("tooltip triggers remain selectable and tooltip content is an explicit comment target", async t => {
  const { page, state } = await setup(t);
  await page.locator("#trigger").hover();
  assert.ok(await page.locator("#tipcard").isVisible());
  await selectText(page, "#trigger", { blocked: true });
  assert.equal(await page.locator("#tipcard").isVisible(), false);
  await page.locator("#cm-chip").click();
  await page.locator("#cm-target").selectOption("tooltip");
  assert.match(await page.locator("#cm-editor .cm-quote").innerText(), /A detailed explanation/);
  await page.locator("#cm-editor textarea").fill("Clarify the explanation");
  await page.locator("#cm-save").click();
  await page.locator("#cm-editor").waitFor({ state: "hidden" });
  assert.equal(state.posts[0].comment.quote, "A detailed explanation for the tooltip target.");
  assert.equal(state.posts[0].comment.anchor.kind, "tooltip");
  assert.equal(state.posts[0].comment.anchor.slide_id, "11111111-1111-4111-8111-111111111111");
  assert.equal(state.posts[0].comment.anchor.tooltip_trigger, "Tooltip trigger words");
  assert.equal(state.posts[0].comment.anchor.tooltip_text, "A detailed explanation for the tooltip target.");
  await page.locator("#trigger").hover();
  assert.ok(await page.locator("#tipcard").isVisible(), "tooltips work again after commenting");
});

test("tooltip trigger text can still receive an ordinary slide comment", async t => {
  const { page, state } = await setup(t);
  await selectText(page, "#trigger");
  await page.locator("#cm-chip").click();
  assert.equal(await page.locator("#cm-target").inputValue(), "slide");
  await page.locator("#cm-editor textarea").fill("Change the trigger label");
  await page.locator("#cm-save").click();
  await page.locator("#cm-editor").waitFor({ state: "hidden" });
  assert.equal(state.posts[0].comment.quote, "Tooltip trigger words");
  assert.equal(state.posts[0].comment.anchor.kind, "slide");
  await page.locator('#trigger .cm-hl[data-id="added-comment"]').waitFor();
});

test("keyboard selection opens a comment editor without pointer coordinates", async t => {
  const { page } = await setup(t);
  await page.locator("#legacy").evaluate(element => {
    const range = document.createRange();
    range.selectNodeContents(element);
    getSelection().removeAllRanges();
    getSelection().addRange(range);
  });
  await page.keyboard.press("Control+Alt+m");
  await page.locator("#cm-editor").waitFor({ state: "visible" });
  assert.match(await page.locator("#cm-editor .cm-quote").innerText(), /Legacy quoted words/);
  assert.equal(await page.locator("#cm-editor textarea").evaluate(el => el === document.activeElement), true);
});

test("resolved comments remain discoverable and can be reopened", async t => {
  const { page, state } = await setup(t, [oldComment({ status: "resolved" })]);
  await page.locator(".cm-badge").click();
  await page.locator('#cm-list [data-filter="resolved"]').click();
  await page.locator("#cm-list .cm-item").click();
  await page.locator("#cm-card").waitFor({ state: "visible" });
  assert.match(await page.locator("#cm-card").innerText(), /Original instruction/);
  await page.locator("#cm-reopen").click();
  await page.locator('.cm-hl[data-id="legacy-id"]').waitFor();
  assert.equal(state.posts[0].action, "reopen");
  assert.equal(state.posts[0].id, "legacy-id");
  assert.equal(state.comments[0].status, "open");
});

test("cancelling an edit preserves the existing comment", async t => {
  const { page, state } = await setup(t, [oldComment()]);
  await page.locator('.cm-hl[data-id="legacy-id"]').click();
  await page.locator("#cm-edit").click();
  await page.locator("#cm-editor textarea").fill("Discard this draft");
  await page.locator("#cm-cancel").click();
  assert.equal(await page.locator("#cm-editor").isVisible(), false);
  assert.deepEqual(state.posts, []);
  await page.locator('.cm-hl[data-id="legacy-id"]').click();
  assert.equal(await page.locator("#cm-card .cm-text").innerText(), "Original instruction");
});

test("conflicting edits keep the draft and refresh the saved version for review", async t => {
  const { page, state } = await setup(t, [oldComment()]);
  await page.locator('.cm-hl[data-id="legacy-id"]').click();
  await page.locator("#cm-edit").click();
  await page.locator("#cm-editor textarea").fill("My concurrent draft");
  state.comments[0].comment = "Changed by another editor";
  state.comments[0].updated = "2026-10-02T08:00:00.000Z";
  state.failEdits = 409;
  const refresh = page.waitForResponse(response =>
    response.url().endsWith("/comments/fixture") && response.request().method() === "GET");
  await page.locator("#cm-save").click();
  await page.locator("#cm-toast").waitFor({ state: "visible" });
  await (await refresh).finished();
  assert.equal(state.posts[0].expected_updated, created);
  assert.equal(await page.locator("#cm-editor textarea").inputValue(), "My concurrent draft");
  assert.ok(await page.locator("#cm-editor").isVisible());
  assert.match(await page.locator("#cm-toast").innerText(), /changed elsewhere/i);
  await page.locator("#cm-cancel").click();
  await page.locator('.cm-hl[data-id="legacy-id"]').click();
  assert.equal(await page.locator("#cm-card .cm-text").innerText(), "Changed by another editor");
});

for (const sameExplanation of [false, true]) test(
  "a partial tooltip trigger selection stays attached with " + (sameExplanation ? "identical" : "different") + " explanations", async t => {
  const { page, state } = await setup(t);
  if (sameExplanation) await page.locator("#ambiguous-tip-two").evaluate(element =>
    element.setAttribute("data-tip", "First explanation."));
  await page.locator("#ambiguous-tip-one").evaluate(element => {
    const selection = getSelection();
    selection.removeAllRanges();
    const range = document.createRange();
    range.setStart(element.firstChild, 0);
    range.setEnd(element.firstChild, 5);
    selection.addRange(range);
    const rect = range.getBoundingClientRect();
    element.dispatchEvent(new MouseEvent("mouseup", {
      bubbles: true, clientX: rect.right, clientY: rect.bottom, button: 0,
    }));
  });
  await page.locator("#cm-chip").click();
  await page.locator("#cm-target").selectOption("tooltip");
  await page.locator("#cm-editor textarea").fill("Explain the first tooltip");
  await page.locator("#cm-save").click();
  await page.locator("#cm-editor").waitFor({ state: "hidden" });
  assert.equal(state.posts[0].comment.quote, "First explanation.");
  await page.locator('#ambiguous-tip-one .cm-hl[data-id="added-comment"]').waitFor();
  assert.equal(await page.locator("#ambiguous-tip-two .cm-hl").count(), 0);
});

test("tooltip comments stay highlighted after server whitespace normalization", async t => {
  const { page, state } = await setup(t);
  await page.locator("#trigger").evaluate(element =>
    element.setAttribute("data-tip", "  Explanation with whitespace\n"));
  await selectText(page, "#trigger");
  await page.locator("#cm-chip").click();
  await page.locator("#cm-target").selectOption("tooltip");
  await page.locator("#cm-editor textarea").fill("Clarify the whitespace explanation");
  await page.locator("#cm-save").click();
  await page.locator("#cm-editor").waitFor({ state: "hidden" });
  assert.equal(state.comments[0].anchor.tooltip_text, "Explanation with whitespace");
  await page.locator('#trigger .cm-hl[data-id="added-comment"]').waitFor();
});
