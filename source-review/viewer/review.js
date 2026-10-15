/* source-review in-deck review. Loaded via <script src="/_assets/review.js"> in a deck.
 * Fetches review.json next to the deck; shows a top-right button when present; on click
 * narrows the deck, highlights the current slide's claims, and opens a claim-driven source
 * pane. PDF sources render via pdf.js with clickable verdict-colored passage overlays;
 * clicking a passage in the source jumps the deck to the slide making that claim. */
(function () {
  "use strict";
  var data = null, sources = {}, on = false, panel, frame, pages, label, msg;
  var ASSET = document.currentScript && document.currentScript.src
    ? new URL(".", document.currentScript.src).href : "/_assets/";

  function rel(p) { return new URL(p, location.href).href; }
  function esc(w) { return w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }
  function quoteRe(c) {
    return new RegExp(c.wiki_quote.trim().split(/\s+/).map(esc).join("\\s+"));
  }

  function init() {
    fetch(rel("review.json"))
      .then(function (r) { if (!r.ok) throw 0; return r.json(); })
      .then(function (j) {
        data = j; (j.sources || []).forEach(function (s) { sources[s.id] = s; });
        addButton();
      })
      .catch(function () { /* no review for this deck */ });
  }

  function addButton() {
    var b = document.createElement("button");
    b.id = "sr-btn"; b.type = "button"; b.textContent = "Review";
    b.addEventListener("click", toggle);
    document.body.appendChild(b);
    addLegend();
  }

  function addLegend() {  // hover "?" chip explaining review mode (visible only when on)
    var lg = document.createElement("div"); lg.id = "sr-legend";
    lg.innerHTML =
      '<div id="sr-legend-chip" tabindex="0" aria-label="Review-mode legend">?</div>' +
      '<div id="sr-legend-pop">' +
      '<p class="lg-head">Review mode</p>' +
      '<p class="lg-txt">Underlined text is fact-checked against the source. ' +
      'Click an underline to open the exact passage in the paper; ' +
      'click a highlighted passage in the paper to jump back to its slide.</p>' +
      '<p class="lg-row"><span class="sr-hl v-supported">gray underline</span>backed by the source &mdash; click to open the passage</p>' +
      '<p class="lg-row"><span class="sr-hl v-not_found">red dashed</span>not backed by the paper &mdash; click for why</p>' +
      "</div>";
    document.body.appendChild(lg);
  }

  function toggle() {
    on = !on;
    document.body.classList.toggle("sr-on", on);
    if (window.Reveal && Reveal.layout) setTimeout(function () { Reveal.layout(); }, 0);  // Quarto decks
    document.getElementById("sr-btn").classList.toggle("active", on);
    if (on) { ensurePanel(); highlightAll(); } else { panel.style.display = "none"; clearHi(); }
  }

  function ensurePanel() {
    if (!panel) {
      panel = document.createElement("div"); panel.id = "sr-panel";
      label = document.createElement("div"); label.id = "sr-srclabel";
      label.textContent = "Click a highlight to see its source";
      msg = document.createElement("div"); msg.id = "sr-msg"; msg.style.display = "none";
      pages = document.createElement("div"); pages.id = "sr-pages"; pages.style.display = "none";
      frame = document.createElement("iframe"); frame.id = "sr-frame";
      panel.appendChild(label); panel.appendChild(msg); panel.appendChild(pages); panel.appendChild(frame);
      document.body.appendChild(panel);
    }
    panel.style.display = "flex";
  }

  /* ---- deck -> source ---- */

  var avail = {};  // annotated-doc availability cache, keyed by url
  var VLABEL = { supported: "Supported", contradicted: "Contradicted",
                 not_found: "Not in source",
                 reference: "Reference", unverifiable: "Unverifiable" };
  var KLABEL = { claim: "Claim", important: "Important", definition: "Definition", reference: "Reference" };

  function escHtml(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  function showMsg(html) {  // message pane replaces the source view
    pages.style.display = "none"; frame.style.display = "none";
    msg.style.display = "block"; msg.innerHTML = html;
  }

  function showSource(claim) {
    var s = sources[claim.source]; if (!s) return;
    if (!claim.jump) {  // not_found / unverifiable: explain instead of navigating
      label.textContent = s.title || s.id;
      showMsg(
        '<span class="sr-verdict v-' + escHtml(claim.verdict) + '">' +
          escHtml((KLABEL[claim.kind] ? KLABEL[claim.kind] + " — " : "") + (VLABEL[claim.verdict] || claim.verdict)) + "</span>" +
        '<p class="sr-claimtext">&ldquo;' + escHtml(claim.claim || claim.wiki_quote) + "&rdquo;</p>" +
        (claim.detail ? '<p class="sr-detail">' + escHtml(claim.detail) + "</p>" : "") +
        '<p class="sr-note">This statement was not located in the source — the slide draws on ' +
        "context beyond it. That is acceptable; only <em>contradicted</em> claims signal an error. " +
        "There is no passage to jump to.</p>");
      return;
    }
    var url = rel("annotated." + s.id + "." + (s.doc_type === "pdf" ? "pdf" : "html"));
    if (avail[url] === true) return navigate(s, claim, url);
    if (avail[url] === false) return missing(s);
    fetch(url, { method: "HEAD" })
      .then(function (r) { avail[url] = r.ok; r.ok ? navigate(s, claim, url) : missing(s); })
      .catch(function () { avail[url] = false; missing(s); });
  }

  function missing(s) {
    label.textContent = s.title || s.id;
    showMsg('<p class="sr-claimtext">Annotated source not available</p>' +
      '<p class="sr-note">The regenerable <code>annotated.*</code> file is missing in this ' +
      "checkout. Re-create it with <code>scripts/review.sh</code>.</p>");
  }

  function navigate(s, claim, url) {
    label.textContent = s.title || s.id;
    msg.style.display = "none";
    if (s.doc_type === "pdf") return showPdf(s, claim);
    pages.style.display = "none"; frame.style.display = "block";
    if (claim.jump.anchor) {
      var anchor = claim.jump.anchor;
      var jump = function () {
        try {
          var w = frame.contentWindow;
          var el = w.document.getElementById(anchor);
          if (el) { el.scrollIntoView({ behavior: "smooth", block: "center" }); flashEl(el); }
          else { w.location.hash = "#" + anchor; }
        } catch (e) { /* loading / cross-origin: ignore */ }
      };
      if (frame.dataset.loaded === url) { jump(); }
      else { frame.onload = function () { frame.dataset.loaded = url; wireHtmlClicks(); jump(); }; frame.src = url; }
    } else if (frame.dataset.loaded !== url) {
      frame.onload = function () { frame.dataset.loaded = url; wireHtmlClicks(); };
      frame.src = url;
    }
  }

  /* ---- pdf.js source panel (rendered pages + clickable passage overlays) ---- */

  var _pdfjs = null;
  function ensurePdfJs() {
    if (_pdfjs) return _pdfjs;
    // pdf.js ships as an ES module (see pdfjs/README.md); resolve the URL
    // against the page so import() works from any script location.
    _pdfjs = import(new URL(ASSET + "pdfjs/pdf.min.mjs", location.href).href).then(function (lib) {
      lib.GlobalWorkerOptions.workerSrc = new URL(ASSET + "pdfjs/pdf.worker.min.mjs", location.href).href;
      return lib;
    });
    return _pdfjs;
  }

  var pdfDocs = {}, renderedFor = null, pageEls = {};

  function showPdf(s, claim) {
    frame.style.display = "none"; pages.style.display = "block";
    var done = function () {
      var wrap = pageEls[claim.jump.page]; if (!wrap) return;
      var hls = wrap.querySelectorAll('.pdf-hl[data-idx="' + claim.idx + '"]');
      // center the passage itself (not the page top) in the scroll pane
      var top = wrap.offsetTop + (hls.length ? hls[0].offsetTop : 0);
      pages.scrollTo({ top: Math.max(0, top - pages.clientHeight / 2), behavior: "smooth" });
      hls.forEach(pulse);
    };
    if (renderedFor === s.id) return done();
    renderPdf(s).then(done).catch(function () { missing(s); });
  }

  function renderPdf(s) {
    var url = rel("annotated." + s.id + ".pdf");
    return ensurePdfJs().then(function (lib) {
      return pdfDocs[s.id] || (pdfDocs[s.id] = lib.getDocument({ url: url, isEvalSupported: false }).promise);
    }).then(function (pdf) {
      pages.innerHTML = ""; pageEls = {}; renderedFor = s.id;
      var claims = (data.claims || []).filter(function (c) {
        return c.source === s.id && c.jump && c.jump.page;
      });
      var nums = claims.map(function (c) { return c.jump.page; })
        .filter(function (v, i, a) { return a.indexOf(v) === i; })
        .sort(function (a, b) { return a - b; });
      var targetW = Math.max(320, (pages.clientWidth || 600) - 24);
      var ratio = window.devicePixelRatio || 1;
      var chain = Promise.resolve();
      nums.forEach(function (pno) {
        chain = chain.then(function () { return pdf.getPage(pno); }).then(function (page) {
          var scale = targetW / page.getViewport({ scale: 1 }).width;
          var vp = page.getViewport({ scale: scale });
          var wrap = document.createElement("div");
          wrap.className = "pdf-page";
          wrap.style.width = vp.width + "px"; wrap.style.height = vp.height + "px";
          var canvas = document.createElement("canvas");
          canvas.width = Math.floor(vp.width * ratio); canvas.height = Math.floor(vp.height * ratio);
          canvas.style.width = vp.width + "px"; canvas.style.height = vp.height + "px";
          wrap.appendChild(canvas);
          var lab = document.createElement("span");
          lab.className = "pg-label"; lab.textContent = "p." + pno;
          wrap.appendChild(lab);
          pages.appendChild(wrap);
          pageEls[pno] = wrap;
          return page.render({
            canvasContext: canvas.getContext("2d"), viewport: vp,
            transform: ratio !== 1 ? [ratio, 0, 0, ratio, 0, 0] : undefined
          }).promise.then(function () {
            claims.filter(function (c) { return c.jump.page === pno && c.jump.rects; })
              .forEach(function (c) {
                c.jump.rects.forEach(function (r) {
                  var hl = document.createElement("div");
                  hl.className = "pdf-hl v-" + c.verdict; hl.dataset.idx = c.idx;
                  hl.title = "Jump to the slide making this claim";
                  hl.style.left = (r[0] * vp.width) + "px";
                  hl.style.top = (r[1] * vp.height) + "px";
                  hl.style.width = ((r[2] - r[0]) * vp.width) + "px";
                  hl.style.height = ((r[3] - r[1]) * vp.height) + "px";
                  hl.addEventListener("click", function () { jumpToSlide(c.idx); });
                  wrap.appendChild(hl);
                });
              });
          });
        });
      });
      return chain;
    });
  }

  /* ---- source -> deck (reverse jump) ---- */

  function jumpToSlide(idx) {
    // every slide is pre-highlighted, so the span (and its slide) already exist
    var span = document.querySelector('span.sr-hl[data-idx="' + idx + '"]');
    if (!span) return;
    var sec = span.closest("section[id]"); if (!sec) return;
    if ((location.hash || "#1") !== "#" + sec.id) location.hash = "#" + sec.id;  // Marp follows
    document.querySelectorAll("span.sr-hl").forEach(function (x) { x.classList.remove("active"); });
    span.classList.add("active"); flashEl(span);
  }

  function wireHtmlClicks() {  // clickable marks inside the annotated HTML iframe
    try {
      var doc = frame.contentWindow.document;
      doc.querySelectorAll('mark[id^="x-anno-"]').forEach(function (m) {
        if (m.dataset.srWired) return;
        m.dataset.srWired = "1"; m.style.cursor = "pointer";
        m.addEventListener("click", function () { jumpToSlide(parseInt(m.id.slice(7), 10)); });
      });
    } catch (e) { /* cross-origin: skip */ }
  }

  /* ---- effects ---- */

  function flashEl(el) {
    el.style.transition = "outline-color .25s ease";
    el.style.outline = "3px solid #ff8a3d";
    el.style.outlineOffset = "2px";
    setTimeout(function () { el.style.outline = "3px solid transparent"; }, 1300);
  }

  function pulse(hl) {
    hl.classList.remove("pulse"); void hl.offsetWidth; hl.classList.add("pulse");
    setTimeout(function () { hl.classList.remove("pulse"); }, 1300);
  }

  /* ---- slide highlighting ---- */

  function clearHi() {
    document.querySelectorAll("section span.sr-hl").forEach(function (s) {
      s.parentNode.replaceChild(document.createTextNode(s.textContent), s);
    });
  }

  function wrapFirst(root, claim) {
    var re = quoteRe(claim);
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: function (n) {
        if (!n.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
        if (n.parentElement && n.parentElement.closest("span.sr-hl")) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    var node;
    while ((node = walker.nextNode())) {
      var m = re.exec(node.nodeValue); if (!m) continue;
      var tail = node.splitText(m.index); tail.splitText(m[0].length);
      var span = document.createElement("span");
      span.className = "sr-hl k-" + (claim.kind || "claim") + " v-" + claim.verdict; span.dataset.idx = claim.idx;
      if (!claim.jump) {
        span.dataset.nojump = "1";
        span.title = "Not located in the source — this claim draws on context beyond it";
      }
      span.textContent = tail.nodeValue;
      tail.parentNode.replaceChild(span, tail);
      return true;
    }
    return false;
  }

  function highlightAll() {
    // Highlight every claim on every slide up front: Marp's own navigation updates
    // the URL via history.replaceState (no hashchange event), so per-slide
    // re-highlighting on navigation is unreliable — and all-at-once is what a
    // review pass wants anyway. Each claim marks its first occurrence in deck order.
    clearHi();
    if (!data) return;
    var secs = Array.prototype.slice.call(document.querySelectorAll("section[id]"));
    (data.claims || []).filter(function (c) { return c.wiki_quote; })
      .slice().sort(function (a, b) { return a.wiki_quote.length - b.wiki_quote.length; })
      .forEach(function (c) {
        var wrapped = secs.some(function (sec) { return wrapFirst(sec, c); });
        if (!wrapped) {
          var crossNode = secs.some(function (sec) { return quoteRe(c).test(sec.textContent); });
          console.warn("[source-review] claim " + c.idx + (crossNode
            ? " wiki_quote spans multiple text nodes (not highlighted): "
            : " wiki_quote not found on any slide: ") + JSON.stringify(c.wiki_quote));
        }
      });
    document.querySelectorAll("span.sr-hl").forEach(function (el) {
      el.addEventListener("click", function () {
        document.querySelectorAll("span.sr-hl").forEach(function (x) { x.classList.remove("active"); });
        el.classList.add("active");
        showSource(data.claims[Number(el.dataset.idx)]);
      });
    });
  }

  // Quarto dev server swaps re-rendered slides in place: re-highlight claims.
  window.addEventListener("deck:updated", function () { if (on) highlightAll(); });

  if (document.readyState !== "loading") init();
  else document.addEventListener("DOMContentLoaded", init);
})();
