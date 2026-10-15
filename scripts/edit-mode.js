/* Live edit mode for the :8093 deck server. Inlined into every served deck by
 * quarto/scripts/gen_client.py. Pure markdown-splitting helpers live at the top so
 * scripts/edit-mode.test.js can require() them from node; the browser UI IIFE
 * (Task 4) sits below. Must never contain a literal closing script tag. */

function splitDeck(text) {
  var lines = text.split("\n");
  var fmEnd = 0;
  if (lines.length && /^---\s*$/.test(lines[0])) {
    for (var j = 1; j < lines.length; j++) {
      if (/^---\s*$/.test(lines[j])) { fmEnd = j + 1; break; }
    }
  }
  var bounds = [];
  var fence = null;
  for (var i = fmEnd; i < lines.length; i++) {
    var l = lines[i];
    var f = l.match(/^(```|~~~)/);
    if (f) {
      if (!fence) fence = f[1];
      else if (l.slice(0, 3) === fence) fence = null;
      continue;
    }
    if (!fence && /^---\s*$/.test(l)) bounds.push(i);
  }
  var slides = [];
  var start = fmEnd;
  for (var b = 0; b < bounds.length; b++) {
    slides.push({ start: start, end: bounds[b] });
    start = bounds[b] + 1;
  }
  slides.push({ start: start, end: lines.length });
  return { lines: lines, fmEnd: fmEnd, slides: slides };
}

function getFragment(doc, n) {
  var s = doc.slides[n];
  return doc.lines.slice(s.start, s.end).join("\n");
}

function setFragment(doc, n, frag) {
  var s = doc.slides[n];
  return doc.lines.slice(0, s.start)
    .concat(frag.split("\n"), doc.lines.slice(s.end))
    .join("\n");
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { splitDeck: splitDeck, getFragment: getFragment, setFragment: setFragment };
}

(function () {
  if (typeof document === "undefined") return; // node test context
  var info = DeckClient.deckInfo(); // from client-common.js, injected first
  if (!info || info.exported) return; // never in an exported file
  var deck = info.deck, base = info.base;
  function relayout() { // reveal.js scales the deck to its container
    if (window.Reveal && Reveal.layout) setTimeout(function () { Reveal.layout(); }, 0);
  }

  var css = document.createElement("style");
  css.textContent = [
    "body.ed-on .reveal{width:56vw!important}",
    "#ed-panel{position:fixed;top:0;right:0;width:44vw;height:100vh;z-index:99998;",
    "background:#0d0f10;border-left:2px solid #3b82f6;display:none;flex-direction:column;",
    "font:13px/1.4 system-ui,sans-serif}",
    "body.ed-on #ed-panel{display:flex}",
    "#ed-head{display:flex;justify-content:space-between;align-items:center;padding:6px 10px;",
    "background:#111;color:#93c5fd;font-weight:600;border-bottom:1px solid #2a2a2a}",
    "#ed-right{display:flex;align-items:center;gap:10px}",
    "#ed-status{font-weight:400;color:#8a8f96}",
    "#ed-status.saving{color:#e3b341}#ed-status.error{color:#f85149}",
    "#ed-status.dirty{color:#e3b341}",
    "#ed-save{display:inline-flex;align-items:center;gap:6px;border:1px solid #3b82f6;",
    "border-radius:999px;background:#3b82f6;color:#0a0a0a;font:600 12px/1 system-ui,sans-serif;",
    "padding:5px 12px;cursor:pointer}",
    "#ed-save:disabled{background:transparent;border-color:#2a2a2a;color:#5a5f64;cursor:default}",
    "#ed-save kbd{font:600 10px/1 system-ui,sans-serif;border:1px solid currentColor;",
    "border-radius:4px;padding:1px 4px;opacity:.75}",
    "#ed-warn{display:none;padding:6px 10px;background:#3a2f06;color:#ffe08a;font-size:12px}",
    "#ed-ta{flex:1;background:#0d0f10;color:#d6d9dc;border:0;outline:none;resize:none;",
    "padding:12px 14px;font:13px/1.55 'JetBrains Mono',Consolas,monospace;",
    // soft-wrap long lines at the pane width instead of horizontal scrolling
    // (wrap is visual only — no newlines are inserted into the saved text)
    "white-space:pre-wrap;word-break:break-word;overflow-x:hidden;overflow-y:auto}",
    "@media print{#ed-panel{display:none!important}}",
    // mobile: bottom-sheet pane under the deck instead of a side split
    "@media (max-width: 900px){",
    "body.ed-on .reveal{width:100vw!important;height:44vh!important}",
    "#ed-panel{width:100vw;height:56vh;top:auto;bottom:0;border-left:0;border-top:2px solid #3b82f6}",
    "#ed-ta{font-size:16px}", // ≥16px stops iOS zoom-on-focus
    "#ed-save kbd{display:none}",
    "#ed-save{padding:9px 18px}",
    "}",
  ].join("");
  document.head.appendChild(css);

  var panel = document.createElement("div");
  panel.id = "ed-panel";
  panel.innerHTML =
    '<div id="ed-head"><span id="ed-title">Edit</span>' +
    '<span id="ed-right"><span id="ed-status"></span>' +
    '<button id="ed-save" type="button" title="Save to disk (Ctrl+S / ⌘S)">Save <kbd>Ctrl+S</kbd></button>' +
    "</span></div>" +
    '<div id="ed-warn"></div>' +
    '<textarea id="ed-ta" spellcheck="false"></textarea>';
  document.body.appendChild(panel);
  var ta = panel.querySelector("#ed-ta");
  var title = panel.querySelector("#ed-title");
  var warn = panel.querySelector("#ed-warn");
  var statusEl = panel.querySelector("#ed-status");
  var saveBtn = panel.querySelector("#ed-save");

  var doc = null, etag = null, page = 0, dirty = false, on = false;
  var wholeFile = false;

  function syncSaveBtn() { saveBtn.disabled = !dirty; }

  function skey() { return "edit-mode:" + location.pathname; }
  function setStatus(txt, cls) { statusEl.textContent = txt; statusEl.className = cls || ""; }
  function curPage() {
    if (window.Reveal && Reveal.getIndices && Reveal.isReady && Reveal.isReady()) {
      return Reveal.getIndices().h;
    }
    var n = parseInt((location.hash || "#1").slice(1), 10);
    return isNaN(n) ? 0 : n - 1;
  }

  // close the editor if the review pane (body class sr-on, button #sr-btn) opens
  document.addEventListener("click", function (e) {
    if (e.target && e.target.id === "sr-btn" && on) closePane();
  }, true);

  function restoreDraft() {
    if (wholeFile) return; // a per-page fragment draft must never become a whole-file payload
    var draft = null;
    try { draft = JSON.parse(sessionStorage.getItem(skey() + ":draft")); } catch (e) {}
    if (draft && !draft.wholeFile && draft.page === page && draft.text !== ta.value) {
      ta.value = draft.text;
      dirty = true;
      setStatus("restored unsaved edit — Ctrl+S to save", "dirty");
      syncSaveBtn();
    }
  }

  function showPage() {
    if (!doc) return;
    if (wholeFile) {
      title.textContent = "Whole file (slide mapping unavailable)";
      ta.value = doc.lines.join("\n");
      dirty = false;
      syncSaveBtn();
      return;
    }
    if (page >= doc.slides.length) page = doc.slides.length - 1;
    title.textContent = "Slide " + (page + 1) + " / " + doc.slides.length;
    ta.value = getFragment(doc, page);
    dirty = false;
    restoreDraft();
    syncSaveBtn();
  }

  function loadDoc() {
    statusEl.style.cursor = ""; statusEl.onclick = null; // drop any stale 412 handler
    return fetch(base + "/raw/" + deck, { credentials: "include" }).then(function (r) {
      if (!r.ok) throw new Error("raw fetch " + r.status);
      etag = r.headers.get("ETag");
      if ((r.headers.get("X-Edit-Target") || "").indexOf("slides.tpl.") === 0) {
        warn.style.display = "block";
        warn.textContent = "Editing the deck template";
      }
      return r.text();
    }).then(function (t) {
      doc = splitDeck(t);
      var domSlides = document.querySelectorAll("section[id]").length;
      wholeFile = domSlides > 0 && domSlides !== doc.slides.length;
      page = curPage();
      setStatus("loaded");
      showPage(); // restores a dangling draft (and its status message) internally
    }).catch(function (e) { setStatus("load failed: " + e.message, "error"); });
  }

  function save() {
    if (!doc || !dirty) return Promise.resolve();
    statusEl.style.cursor = ""; statusEl.onclick = null; // drop any stale 412 handler
    var full = wholeFile ? ta.value : setFragment(doc, page, ta.value);
    setStatus("saving…", "saving");
    return fetch(base + "/raw/" + deck, {
      method: "PUT", credentials: "include",
      headers: { "If-Match": etag, "Content-Type": "text/markdown" },
      body: full,
    }).then(function (r) {
      if (r.status === 412) {
        setStatus("conflict — click to reload from disk", "error");
        statusEl.style.cursor = "pointer";
        statusEl.onclick = function () {
          statusEl.style.cursor = ""; statusEl.onclick = null;
          sessionStorage.removeItem(skey() + ":draft");
          loadDoc();
        };
        return;
      }
      if (!r.ok) {
        var e2 = r.headers.get("ETag");
        if (e2) etag = e2;
        setStatus("save failed: " + r.status, "error");
        return;
      }
      etag = r.headers.get("ETag");
      doc = splitDeck(full);
      dirty = false;
      syncSaveBtn();
      setStatus("saved ✓");
      sessionStorage.removeItem(skey() + ":draft");
      // the deck server re-renders and swaps the changed slides in place.
    }).catch(function (e) { setStatus("save failed: " + e.message, "error"); });
  }

  /* live preview: the export server's POST /preview/<deck> renders just the
     current slide with pandoc and we patch its DOM in place — typing previews
     instantly, disk stays untouched until an explicit save. The patched slide
     may briefly diverge from disk; the save→re-render restores ground truth. */
  var previewOk = false, pvTimer = null, pvBusy = false, pvQueued = false;

  function checkPreview() {
    fetch(base + "/healthz")
      .then(function (r) { previewOk = r.ok; })
      .catch(function () { previewOk = false; });
  }

  function previewNow() {
    if (!previewOk || !doc || !on) return;
    if (pvBusy) { pvQueued = true; return; }
    pvBusy = true;
    var full = wholeFile ? ta.value : setFragment(doc, page, ta.value);
    var idx = curPage();
    fetch(base + "/preview/" + deck, {
      method: "POST", credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ deck: deck, markdown: full, page: idx + 1 }),
    }).then(function (r) { if (!r.ok) throw 0; return r.json(); })
      .then(function (j) {
        var live = document.querySelector('section[id="' + (idx + 1) + '"]');
        if (!live) return;
        live.innerHTML = j.html; // this one slide's body
        live.querySelectorAll(".fragment").forEach(function (f) { f.classList.add("visible"); });
        live.querySelectorAll(".notes").forEach(function (n) { n.style.display = "none"; });
        if (window.MathJax && MathJax.typesetPromise) MathJax.typesetPromise([live]).catch(function () {});
      })
      .catch(function () {})
      .then(function () {
        pvBusy = false;
        if (pvQueued) { pvQueued = false; previewNow(); }
      });
  }

  // explicit save only: button, Ctrl+S/⌘S, slide exit, pane close.
  // Keystrokes still go to the sessionStorage draft, so nothing is lost.
  ta.addEventListener("input", function () {
    dirty = true;
    setStatus("unsaved changes — Ctrl+S", "dirty");
    syncSaveBtn();
    if (!wholeFile) { // never persist the whole document into the per-page draft slot
      sessionStorage.setItem(skey() + ":draft",
        JSON.stringify({ page: page, text: ta.value, wholeFile: wholeFile }));
    }
    clearTimeout(pvTimer);
    pvTimer = setTimeout(previewNow, 250);
  });

  saveBtn.addEventListener("click", function () { save(); });

  function isSaveKey(e) {
    return (e.ctrlKey || e.metaKey) && !e.shiftKey && !e.altKey &&
      e.key.toLowerCase() === "s";
  }

  // Keys typed in the pane must not reach bespoke's document-level handler —
  // otherwise arrows/space navigate the deck while you move the caret, and
  // save-on-slide-exit then drags the pane along ("saving jumps slides").
  panel.addEventListener("keydown", function (e) {
    if (isSaveKey(e)) { e.preventDefault(); save(); }
    e.stopPropagation();
  });

  document.addEventListener("keydown", function (e) {
    if (on && isSaveKey(e)) {
      e.preventDefault();
      save();
    }
  });

  window.addEventListener("beforeunload", function (e) {
    if (on && dirty) { e.preventDefault(); e.returnValue = ""; }
  });

  // follow deck navigation (bespoke uses replaceState: no hashchange event)
  setInterval(function () {
    if (!on || !doc || wholeFile) return;
    var p = curPage();
    if (p !== page) {
      var go = function () { page = p; showPage(); persist(); };
      dirty ? save().then(go) : go();
    }
  }, 300);

  function persist() {
    sessionStorage.setItem(skey(), JSON.stringify({ open: on, page: page }));
  }

  function openPane() {
    if (document.body.classList.contains("sr-on")) {
      var sr = document.getElementById("sr-btn");
      if (sr) sr.click();
    }
    checkPreview();
    on = true;
    document.body.classList.add("ed-on");
    var b = document.getElementById("ed-btn");
    if (b) b.classList.add("active");
    relayout();
    persist();
    loadDoc();
  }

  function closePane() {
    if (dirty) save(); // save-on-exit; the draft still covers a failed attempt
    on = false;
    document.body.classList.remove("ed-on");
    var b = document.getElementById("ed-btn");
    if (b) b.classList.remove("active");
    relayout();
    persist();
  }

  function addButton(osc) {
    var btn = document.createElement("button");
    btn.id = "ed-btn";
    btn.type = "button";
    btn.className = "dl-export";
    btn.tabIndex = -1;
    btn.title = "Edit this slide's markdown";
    btn.innerHTML = "<span>Edit</span>";
    btn.addEventListener("click", function (e) {
      e.preventDefault(); e.stopPropagation();
      on ? closePane() : openPane();
    });
    osc.appendChild(btn);
  }

  // gate on the export server being up, then mount in the OSC bar
  fetch(base + "/healthz").then(function (r) {
    if (!r.ok) return;
    DeckClient.onOsc(function (osc) {
      addButton(osc);
      var st = null;
      try { st = JSON.parse(sessionStorage.getItem(skey())); } catch (e) {}
      if (st && st.open) openPane();
    });
  }).catch(function () {});
})();
