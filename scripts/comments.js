/* Slide comments for the deck server. Inlined into every deck by
 * quarto/scripts/gen_client.py (like edit-mode.js — must never contain a literal
 * closing script tag). Select text on a slide -> "Comment" chip -> note.
 * Persisted to decks/<deck>/comments.json via the deck server's comments API, where
 * agents pick them up: each entry has {id, page, quote, comment, status};
 * an agent greps the quote in slides.qmd, does the work, sets status resolved.
 * Open comments render as highlights; click a highlight to read/resolve. */
(function () {
  if (typeof document === "undefined") return; // node context
  var info = DeckClient.deckInfo(); // client-common.js: URL on the dev server,
  if (!info) return;                // window.CM_CONFIG in exported HTML
  var deck = info.deck, base = info.base;
  var apiHost = base.replace(/^[a-z]+:\/\//, ""); // host:port actually in use (messages)
  var comments = [];
  var pending = null, editing = null, saving = false, listFilter = "open";

  var SVG_NS = "http://www.w3.org/2000/svg";

  var css = document.createElement("style");
  css.textContent = [
    "span.cm-hl{background:rgba(255,138,61,.22);border-bottom:2px solid #ff8a3d;cursor:pointer}",
    "tspan.cm-hl{fill:#ff8a3d;text-decoration:underline;cursor:pointer}",
    "#cm-chip{position:fixed;display:none;z-index:100002;border:1px solid #ff8a3d;",
    "border-radius:999px;background:#1a120a;color:#ffb27d;font:600 12px/1 system-ui,sans-serif;",
    "padding:6px 12px;cursor:pointer;box-shadow:0 4px 16px rgba(0,0,0,.5)}",
    "#cm-card,#cm-editor{position:fixed;display:none;z-index:100002;width:350px;box-sizing:border-box;max-width:calc(100vw - 16px);max-height:calc(100vh - 16px);overflow:auto;",
    "background:#141414;border:1px solid #2a2a2a;border-left:3px solid #ff8a3d;border-radius:10px;",
    "padding:12px 14px;box-shadow:0 10px 30px rgba(0,0,0,.65);font:13px/1.45 system-ui,sans-serif;color:#d6d9dc}",
    "#cm-card .cm-quote,#cm-editor .cm-quote{color:#8a8f96;font-size:11.5px;font-style:italic;",
    "margin-bottom:8px;max-height:8em;overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere}",
    "#cm-card .cm-text{white-space:pre-wrap;margin-bottom:10px}",
    "#cm-card .cm-meta{color:#6b7178;font-size:11px;margin-bottom:10px}",
    "#cm-editor textarea{width:100%;box-sizing:border-box;height:72px;background:#0d0f10;",
    "color:#d6d9dc;border:1px solid #2a2a2a;border-radius:6px;padding:8px;resize:vertical;",
    "font:13px/1.45 system-ui,sans-serif;outline:none}",
    "#cm-editor textarea:focus{border-color:#ff8a3d}",
    "#cm-target{display:block;width:100%;margin:6px 0 10px;background:#0d0f10;color:#d6d9dc;padding:6px;border:1px solid #555;border-radius:6px}",
    ".cm-context{color:#ffb27d;font-size:11px;margin-bottom:8px;overflow-wrap:anywhere}",
    "#cm-history{margin:10px 0;color:#b2b8bf;font-size:11px}",
    "#cm-history summary{cursor:pointer;color:#ffb27d}",
    "#cm-history ol{padding-left:20px}#cm-history li{margin:8px 0;white-space:pre-wrap;overflow-wrap:anywhere}",
    ".cm-btn:disabled{opacity:.5;cursor:wait}",
    "body.cm-selecting #tipcard,body.cm-commenting #tipcard{display:none!important}",
    "#cm-author{width:100%;box-sizing:border-box;background:#0d0f10;color:#8a8f96;",
    "border:1px solid #2a2a2a;border-radius:6px;padding:6px 8px;margin-bottom:8px;",
    "font:12px/1.4 system-ui,sans-serif;outline:none}",
    ".cm-btn{border:1px solid #ff8a3d;border-radius:999px;background:#ff8a3d;color:#131313;",
    "font:600 12px/1 system-ui,sans-serif;padding:6px 14px;cursor:pointer;margin-right:8px}",
    ".cm-btn.ghost{background:transparent;color:#ffb27d}",
    "#cm-editor .cm-row{margin-top:10px}",
    ".bespoke-marp-osc button.dl-export.cm-badge{border-color:rgba(255,138,61,.7);color:#ffb27d}",
    "#cm-list{position:fixed;display:none;z-index:100002;width:380px;box-sizing:border-box;max-width:calc(100vw - 16px);max-height:70vh;overflow:auto;",
    "background:#141414;border:1px solid #2a2a2a;border-left:3px solid #ff8a3d;border-radius:10px;",
    "padding:6px;box-shadow:0 10px 30px rgba(0,0,0,.65);font:12.5px/1.4 system-ui,sans-serif}",
    "#cm-list .cm-item{display:block;width:100%;text-align:left;background:none;border:0;",
    "border-radius:6px;padding:8px 10px;color:#d6d9dc;cursor:pointer;font:inherit}",
    "#cm-list .cm-item:hover{background:#1e1e1e}",
    "#cm-list .cm-item .pg{color:#ffb27d;font-weight:700;margin-right:6px}",
    "#cm-list .cm-item .q{color:#8a8f96;font-style:italic}",
    "#cm-list .cm-list-filter{display:flex;gap:6px;padding:8px}#cm-list .cm-list-filter button[aria-pressed=true]{background:#ff8a3d;color:#131313}",
    "#cm-list .cm-empty{padding:12px;color:#8a8f96}",
    "#cm-badge-fallback{position:fixed;bottom:14px;right:14px;z-index:100001}",
    "#cm-toast{position:fixed;left:50%;bottom:24px;transform:translateX(-50%);display:none;",
    "z-index:100003;max-width:520px;background:#2a1512;border:1px solid #c0563f;",
    "border-left:3px solid #e06c5a;border-radius:10px;padding:10px 16px;color:#f0c5b8;",
    "font:13px/1.5 system-ui,sans-serif;box-shadow:0 10px 30px rgba(0,0,0,.65)}",
    "#cm-toast b{color:#ff8a3d}",
    "@media print{#cm-chip,#cm-card,#cm-editor,#cm-list,#cm-toast,#cm-badge-fallback{display:none!important}.cm-hl{background:none;border-bottom:none;fill:inherit;text-decoration:none}}",
  ].join("");
  document.head.appendChild(css);

  var chip = document.createElement("button");
  chip.id = "cm-chip"; chip.type = "button"; chip.textContent = "💬 Comment";
  document.body.appendChild(chip);

  var card = document.createElement("div");
  card.id = "cm-card";
  document.body.appendChild(card);

  var editor = document.createElement("div");
  editor.id = "cm-editor";
  editor.innerHTML =
    '<div class="cm-context"></div>' +
    '<label id="cm-target-label">Comment on<select id="cm-target"><option value="slide">Selected slide text</option><option value="tooltip">Tooltip explanation</option></select></label>' +
    '<div class="cm-quote"></div>' +
    '<input id="cm-author" aria-label="Your name" placeholder="your name (optional, remembered)">' +
    '<textarea aria-label="Comment" placeholder="What should change here?"></textarea>' +
    '<div class="cm-row"><button type="button" class="cm-btn" id="cm-save">Comment</button>' +
    '<button type="button" class="cm-btn ghost" id="cm-cancel">Cancel</button></div>';
  document.body.appendChild(editor);
  var edQuote = editor.querySelector(".cm-quote");
  var edText = editor.querySelector("textarea");
  var edAuthor = editor.querySelector("#cm-author");
  var edTarget = editor.querySelector("#cm-target");
  var saveButton = editor.querySelector("#cm-save");

  // Failure notice: a queued comment is NOT saved, and silently pretending it
  // was cost three weeks of lost feedback once. Say so, loudly.
  var toast = document.createElement("div");
  toast.id = "cm-toast";
  document.body.appendChild(toast);
  var toastTimer = null;
  function showToast(html, ms) {
    toast.innerHTML = html;
    toast.style.display = "block";
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toast.style.display = "none"; }, ms || 9000);
  }

  var list = document.createElement("div");
  list.id = "cm-list";
  document.body.appendChild(list);
  var badge = null; // OSC button, mounted below

  function esc(w) { return w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }
  function quoteRe(q) { return new RegExp(q.trim().split(/\s+/).map(esc).join("\\s+")); }
  function escHtml(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  function place(el, x, y) {
    el.style.display = "block";
    var r = el.getBoundingClientRect();
    if (x + r.width > innerWidth - 8) x = innerWidth - r.width - 8;
    if (y + r.height > innerHeight - 8) y = Math.min(y - r.height - 12, innerHeight - r.height - 8);
    el.style.left = Math.max(8, x) + "px";
    el.style.top = Math.max(8, y) + "px";
  }
  function hideAll() {
    chip.style.display = "none"; card.style.display = "none";
    editor.style.display = "none"; list.style.display = "none";
    document.body.classList.remove("cm-commenting");
  }

  function timestamp(value) {
    if (!value) return "Time unknown";
    var date = new Date(value);
    return isNaN(date.getTime()) ? String(value) : date.toLocaleString(undefined, {
      year: "numeric", month: "short", day: "numeric", hour: "2-digit",
      minute: "2-digit", second: "2-digit", timeZoneName: "short",
    });
  }

  function timeHtml(value) {
    return '<time datetime="' + escHtml(value || "") + '" title="' + escHtml(value || "Not recorded") + '">' + escHtml(timestamp(value)) + '</time>';
  }

  function targetLabel(c) {
    var a = c.anchor || {};
    var sec = commentSection(c);
    var page = sec ? Number(sec.id) : c.page;
    return (sec ? "Slide " : "Original slide ") + page +
      (page !== c.page ? " (originally " + c.page + ")" : "") + (a.heading ? " · " + a.heading : "") +
      (a.kind === "tooltip" ? " · Tooltip: " + (a.tooltip_trigger || "explanation") : " · Slide text");
  }

  /* ---- rendering ---- */

  function clearHi() {
    document.querySelectorAll(".cm-hl").forEach(function (s) {
      s.parentNode.replaceChild(document.createTextNode(s.textContent), s);
    });
    // merge the text-node fragments splitText left behind, so offsets stay sane
    document.querySelectorAll("section[id]").forEach(function (s) { s.normalize(); });
  }

  function collectText(root) {
    // Concatenation of the root's text nodes: selections routinely cross
    // markup (bold, links), so all matching happens in this combined string.
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: function (n) {
        if (n.parentElement && n.parentElement.closest("script,style,.slide-id,#cm-card,#cm-editor")) {
          return NodeFilter.FILTER_REJECT;
        }
        return NodeFilter.FILTER_ACCEPT;
      },
    });
    var node, all = "", parts = [];
    while ((node = walker.nextNode())) {
      parts.push({ node: node, start: all.length });
      all += node.nodeValue;
    }
    return { all: all, parts: parts };
  }

  function findMatches(all, quote) {
    var re = new RegExp(quoteRe(quote).source, "g");
    var out = [], m2;
    while ((m2 = re.exec(all))) {
      out.push({ index: m2.index, length: m2[0].length });
      if (re.lastIndex === m2.index) re.lastIndex++;
    }
    return out;
  }

  function targetMatches(t, quote, tooltipText) {
    return findMatches(t.all, quote).filter(function (m) {
      if (tooltipText == null) return true;
      var part = t.parts.find(function (p) { return p.start <= m.index && p.start + p.node.nodeValue.length > m.index; });
      var tip = part && part.node.parentElement.closest("[data-tip]");
      return tip && tip.getAttribute("data-tip").trim() === tooltipText.trim();
    });
  }

  function wrapFirst(root, c) {
    var t = collectText(root);
    var all = t.all, parts = t.parts;
    var quote = c.anchor && c.anchor.kind === "tooltip" ? c.anchor.tooltip_trigger : c.quote;
    if (!quote) return false;
    var matches = targetMatches(t, quote, c.anchor && c.anchor.kind === "tooltip" ? c.anchor.tooltip_text : null);
    if (!matches.length) return false;
    // anchor to the occurrence recorded at selection time (clamped: the deck
    // may have changed since); old comments without one take the first
    var hit = matches[Math.min(c.occurrence || 0, matches.length - 1)];
    // Context distinguishes repeated phrases after text was inserted earlier.
    var contextual = matches.filter(function (m) {
      return (!c.prefix || all.slice(0, m.index).trimEnd().endsWith(c.prefix)) &&
        (!c.suffix || all.slice(m.index + m.length).trimStart().startsWith(c.suffix));
    });
    if (contextual.length === 1) hit = contextual[0];
    var s = hit.index, e = s + hit.length;
    parts.forEach(function (p) {
      var len = p.node.nodeValue.length;
      var from = Math.max(s - p.start, 0), to = Math.min(e - p.start, len);
      if (from >= to || !p.node.nodeValue.slice(from, to).trim()) return;
      // Overlapping comments stay accessible in the list; do not nest spans.
      if (p.node.parentElement.closest(".cm-hl")) return;
      var target = p.node;
      if (from > 0) target = target.splitText(from);
      if (to - from < target.nodeValue.length) target.splitText(to - from);
      // Namespace matters: an HTML <span> parented to an SVG <text> is not
      // rendered by the SVG renderer at all, so the quoted words vanish from
      // the figure. Inside SVG we must wrap in a <tspan> instead.
      var parent = target.parentNode;
      var inSvg = parent && parent.namespaceURI === SVG_NS && parent.tagName !== "foreignObject";
      var span;
      if (inSvg) {
        span = document.createElementNS(SVG_NS, "tspan");
        span.setAttribute("class", "cm-hl");
        span.setAttribute("data-id", c.id);
      } else {
        span = document.createElement("span");
        span.className = "cm-hl";
        span.dataset.id = c.id;
        span.title = "Open comment — click to view";
      }
      span.textContent = target.nodeValue;
      parent.replaceChild(span, target);
    });
    return true;
  }

  function sectionFor(page) {
    var secs = document.querySelectorAll("section[id]");
    for (var i = 0; i < secs.length; i++) {
      if (Number(secs[i].id) === page) return secs[i];
    }
    return null;
  }

  function commentSection(c) {
    var id = c.anchor && c.anchor.slide_id;
    if (id) {
      var anchor = document.getElementById(id);
      return anchor && anchor.closest("section[id]");
    }
    return sectionFor(c.page);
  }

  // Quarto dev server swaps re-rendered slides in place: re-anchor highlights.
  window.addEventListener("deck:updated", function () { render(); });

  function openComments() {
    return comments.filter(function (c) { return c.status === "open"; });
  }

  function render() {
    clearHi();
    openComments().forEach(function (c) {
      var sec = commentSection(c);
      var ok = sec ? wrapFirst(sec, c) : false;
      if (!ok && !(c.anchor && c.anchor.slide_id)) {
        // fall back to any slide (the quote may have moved), else leave unrendered
        var secs = document.querySelectorAll("section[id]");
        for (var i = 0; i < secs.length && !ok; i++) ok = wrapFirst(secs[i], c);
      }
    });
    if (badge) {
      var n = openComments().length;
      badge.querySelector("span").textContent = "💬 " + n;
    }
  }

  function showList(x, y) {
    hideAll();
    list.innerHTML = "";
    var filters = document.createElement("div");
    filters.className = "cm-list-filter";
    ["open", "resolved", "all"].forEach(function (filter) {
      var button = document.createElement("button");
      button.type = "button"; button.className = "cm-btn ghost";
      button.dataset.filter = filter;
      button.textContent = filter[0].toUpperCase() + filter.slice(1);
      button.setAttribute("aria-pressed", String(listFilter === filter));
      button.addEventListener("click", function () { listFilter = filter; showList(x, y); });
      filters.appendChild(button);
    });
    list.appendChild(filters);
    var visible = comments.filter(function (c) { return listFilter === "all" || c.status === listFilter; });
    visible.sort(function (a, b) { return (Date.parse(b.updated || b.created) || 0) - (Date.parse(a.updated || a.created) || 0); });
    visible.forEach(function (c) {
      var item = document.createElement("button");
      item.type = "button";
      item.className = "cm-item";
      item.innerHTML = '<span class="pg">' + escHtml(targetLabel(c)) + "</span>" + escHtml(c.comment) +
        '<br><span class="q">&ldquo;' + escHtml(c.quote.slice(0, 60)) + '&rdquo;' +
        (c.author ? " — " + escHtml(c.author) : "") + "</span><br>" +
        escHtml(c.status) + " · " + timeHtml(c.updated || c.created);
      item.addEventListener("click", function (e) {
        e.stopPropagation();
        var sec = commentSection(c);
        if (sec && (location.hash || "#1") !== "#" + sec.id) location.hash = "#" + sec.id;
        setTimeout(function () {
          var hl = Array.from(document.querySelectorAll(".cm-hl")).find(function (el) { return el.dataset.id === c.id; });
          if (hl) {
            hl.style.transition = "outline-color .25s ease";
            hl.style.outline = "3px solid #ff8a3d";
            hl.style.outlineOffset = "2px";
            setTimeout(function () { hl.style.outline = "3px solid transparent"; }, 1300);
          }
          showCard(c, x, y);
        }, 150);
      });
      list.appendChild(item);
    });
    if (!visible.length) {
      var empty = document.createElement("div");
      empty.className = "cm-empty";
      empty.textContent = "No " + (listFilter === "all" ? "" : listFilter + " ") +
        "comments. Select slide text to add one (Ctrl/⌘ + Alt + M).";
      list.appendChild(empty);
    }
    place(list, x, y - 30);
  }

  /* ---- server ---- */

  function refetch() {
    return fetch(base + "/comments/" + deck, { credentials: "include" })  // the login cookie (API on another port)
      .then(function (r) { if (!r.ok) throw 0; return r.json(); })
      .then(function (j) { comments = j.comments || []; render(); })
      .catch(function () {});
  }

  function post(payload) {
    return fetch(base + "/comments/" + deck, {
      method: "POST", credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).then(function (r) {
      if (!r.ok) { var err = new Error("Comment request failed"); err.status = r.status; throw err; }
      return r.json();
    })
      .then(function (j) { comments = j.comments || []; render(); });
  }

  /* ---- view / resolve ---- */

  function showCard(c, x, y) {
    hideAll();
    var history = c.history || [{ action: "created", at: c.created, comment: c.comment, author: c.author }];
    card.innerHTML =
      '<div class="cm-context">' + escHtml(targetLabel(c)) + '</div>' +
      '<div class="cm-quote">&ldquo;' + escHtml(c.quote) + '&rdquo;</div>' +
      '<div class="cm-text">' + escHtml(c.comment) + "</div>" +
      '<div class="cm-meta">' + escHtml((c.author ? c.author + " · " : "") + c.status) +
        '<br>Created ' + timeHtml(c.client_created || c.created) +
        (c.updated ? '<br>Updated ' + timeHtml(c.updated) : '') + '</div>' +
      '<details id="cm-history"><summary>History (' + history.length + ')</summary><ol>' +
      history.map(function (h) {
        return '<li>' + escHtml(h.action) + ' · ' + timeHtml(h.at) +
          (h.author ? ' · ' + escHtml(h.author) : '') +
          ((h.action === 'created' || h.action === 'edited') ? '<br>' + escHtml(h.comment) : '') + '</li>';
      }).join('') + '</ol></details>' +
      '<button type="button" class="cm-btn" id="cm-edit">Edit</button>' +
      '<button type="button" class="cm-btn ghost" id="cm-' + (c.status === "resolved" ? "reopen" : "resolve") + '">' +
      (c.status === "resolved" ? "Reopen" : "Resolve") + '</button>';
    card.querySelector("#cm-edit").addEventListener("click", function () { openEditor(c, x, y); });
    card.querySelector("#cm-history").addEventListener("toggle", function () { place(card, x, y); });
    var statusButton = card.querySelector("#cm-resolve,#cm-reopen");
    statusButton.addEventListener("click", function () {
      statusButton.disabled = true;
      var author = "";
      try { author = localStorage.getItem("cm-author") || ""; } catch (e) {}
      post({ action: c.status === "resolved" ? "reopen" : "resolve", id: c.id,
        author: author || undefined, expected_updated: c.updated || c.created || null,
      }).then(hideAll, function (err) {
        statusButton.disabled = false;
        showToast(err.status === 409 ? "<b>Comment changed elsewhere.</b> Reopen it from the list to see the latest version." :
          "<b>Not saved.</b> Could not change the comment status. Please retry.");
        if (err.status === 409) refetch();
      });
    });
    place(card, x, y);
    document.body.classList.add("cm-commenting");
  }

  document.addEventListener("click", function (e) {
    var hl = e.target.closest && e.target.closest(".cm-hl");
    if (hl) {
      if (editor.style.display === "block" || (window.getSelection() && !window.getSelection().isCollapsed)) return;
      var c = comments.filter(function (x) { return x.id === hl.dataset.id; })[0];
      if (c) { e.stopPropagation(); showCard(c, e.clientX + 10, e.clientY + 10); }
      return;
    }
    if (!e.target.closest("#cm-card,#cm-editor,#cm-chip,#cm-list,.cm-badge") && editor.style.display !== "block") hideAll();
  }, true);

  /* ---- add flow ---- */

  function prepareSelection(point) {
    if (editor.style.display === "block") return false;
    var sel = window.getSelection();
    var text = sel && !sel.isCollapsed ? sel.toString().trim() : "";
    if (!text || !sel.rangeCount) { chip.style.display = "none"; pending = null; return false; }
    var range = sel.getRangeAt(0);
    var node = range.startContainer.nodeType === 1 ? range.startContainer : range.startContainer.parentElement;
    var sec = node && node.closest("section[id]");
    if (!sec || !sec.contains(range.endContainer)) { pending = null; chip.style.display = "none"; return false; }
    // which occurrence of the quote did the user select? locate the
    // selection start in the section's combined text and pick the nearest
    // match; also record surrounding context so agents can disambiguate.
    var t = collectText(sec);
    var selStart = 0;
    for (var i = 0; i < t.parts.length; i++) {
      if (t.parts[i].node === range.startContainer) {
        selStart = t.parts[i].start + range.startOffset;
        break;
      }
      if (range.comparePoint(t.parts[i].node, 0) < 0) selStart = t.parts[i].start + t.parts[i].node.nodeValue.length;
    }
    var matches = findMatches(t.all, text);
    var occurrence = 0, bestDist = Infinity;
    matches.forEach(function (hit, idx) {
      var d = Math.abs(hit.index - selStart);
      if (d < bestDist) { bestDist = d; occurrence = idx; }
    });
    var hit = matches[occurrence] || { index: selStart, length: text.length };
    // Pointer release is predictable for multiline/backward selections.
    // Keyboard selections use the actual focus caret instead of a union box.
    var focus = range.cloneRange();
    focus.setStart(sel.focusNode, sel.focusOffset); focus.collapse(true);
    var r = focus.getBoundingClientRect();
    if (!r.width && !r.height) {
      var rects = range.getClientRects();
      r = rects[rects.length - 1] || range.getBoundingClientRect();
    }
    var stable = sec.querySelector(".slide-id[id]");
    var heading = sec.querySelector("h1,h2,h3");
    var tip = node.closest("[data-tip]");
    if (!tip) {
      var tips = Array.from(sec.querySelectorAll("[data-tip]")).filter(function (el) { return range.intersectsNode(el); });
      if (tips.length === 1) tip = tips[0];
    }
    var tooltip = null;
    if (tip) {
      var trigger = tip.textContent.trim();
      var tipPart = t.parts.find(function (p) { return tip.contains(p.node); });
      var tipMatches = targetMatches(t, trigger, tip.getAttribute("data-tip"));
      var tipIndex = tipMatches.findIndex(function (m) { return tipPart && m.index >= tipPart.start && m.index < tipPart.start + tip.textContent.length; });
      var tipHit = tipMatches[Math.max(0, tipIndex)];
      tooltip = { text: tip.getAttribute("data-tip"), trigger: trigger, occurrence: Math.max(0, tipIndex),
        prefix: tipHit ? t.all.slice(Math.max(0, tipHit.index - 40), tipHit.index).trim() : "",
        suffix: tipHit ? t.all.slice(tipHit.index + tipHit.length, tipHit.index + tipHit.length + 40).trim() : "" };
    }
    pending = {
      page: Number(sec.id), quote: text, occurrence: occurrence,
      prefix: t.all.slice(Math.max(0, hit.index - 40), hit.index).trim(),
      suffix: t.all.slice(hit.index + hit.length, hit.index + hit.length + 40).trim(),
      anchor: { kind: "slide", slide_id: stable ? stable.id : undefined,
        heading: heading ? heading.textContent.trim() : undefined },
      tooltip: tooltip,
      x: (point ? point.x : r.right) + 8, y: (point ? point.y : r.bottom) + 8,
    };
    place(chip, pending.x, pending.y);
    document.body.classList.add("cm-commenting");
    return true;
  }

  document.addEventListener("mousedown", function (e) {
    if (e.button === 0 && e.target.closest && e.target.closest("section[id]")) {
      document.body.classList.add("cm-selecting");
      chip.style.display = "none";
    }
  }, true);
  document.addEventListener("mouseup", function (e) {
    document.body.classList.remove("cm-selecting");
    if (e.button !== 0 || (e.target.closest && e.target.closest("#cm-chip,#cm-card,#cm-editor,#cm-list,.cm-badge,#tip-toggle,#ed-panel,#sr-panel"))) return;
    setTimeout(function () { prepareSelection({ x: e.clientX, y: e.clientY }); }, 0);
  }, true);

  function openEditor(c, x, y) {
    hideAll(); editing = c || null;
    editor.querySelector("#cm-target-label").style.display = !c && pending.tooltip ? "block" : "none";
    edTarget.value = "slide";
    edQuote.textContent = "“" + (c ? c.quote : pending.quote) + "”";
    editor.querySelector(".cm-context").textContent = targetLabel(c || pending);
    edText.value = c ? c.comment : "";
    saveButton.textContent = c ? "Save changes" : "Comment";
    try { edAuthor.value = localStorage.getItem("cm-author") || ""; } catch (e) {}
    place(editor, x, y);
    document.body.classList.add("cm-commenting");
    edText.focus();
  }

  edTarget.addEventListener("change", function () {
    if (!pending || !pending.tooltip) return;
    edQuote.textContent = "“" + (edTarget.value === "tooltip" ? pending.tooltip.text : pending.quote) + "”";
    editor.querySelector(".cm-context").textContent = targetLabel(edTarget.value === "tooltip" ? {
      page: pending.page, anchor: Object.assign({}, pending.anchor, { kind: "tooltip", tooltip_trigger: pending.tooltip.trigger }),
    } : pending);
    place(editor, pending.x, pending.y);
  });

  chip.addEventListener("click", function (e) {
    e.stopPropagation();
    if (!pending) return;
    openEditor(null, pending.x, pending.y);
  });
  // Keep the browser selection intact until the target has been captured.
  chip.addEventListener("mousedown", function (e) { e.preventDefault(); });

  document.addEventListener("keydown", function (e) {
    if (e.target.closest && e.target.closest("input,textarea,select,[contenteditable=true]")) return;
    if ((e.ctrlKey || e.metaKey) && e.altKey && e.key.toLowerCase() === "m") {
      if (prepareSelection()) { e.preventDefault(); e.stopPropagation(); openEditor(null, pending.x, pending.y); }
    } else if (e.key === "Escape" && !saving) { hideAll(); pending = null; editing = null; }
  }, true);

  function selectionMoved() {
    chip.style.display = "none";
    document.body.classList.remove("cm-selecting");
    if (editor.style.display !== "block") { pending = null; hideAll(); }
    else {
      var r = editor.getBoundingClientRect();
      place(editor, r.left, r.top);
    }
  }
  window.addEventListener("resize", selectionMoved);
  window.addEventListener("hashchange", selectionMoved);
  window.addEventListener("blur", function () { document.body.classList.remove("cm-selecting"); });
  document.addEventListener("scroll", function (e) {
    if (!(e.target.closest && e.target.closest("#cm-card,#cm-editor,#cm-list"))) selectionMoved();
  }, true);

  /* offline queue: exported HTML may be opened without reach to the server —
     stash failed adds in localStorage and flush on the next load that has it */
  function qkey() { return "cm-queue:" + deck; }
  function readQueue() {
    try { return JSON.parse(localStorage.getItem(qkey())) || []; } catch (e) { return []; }
  }
  function writeQueue(q) {
    try { q.length ? localStorage.setItem(qkey(), JSON.stringify(q))
                   : localStorage.removeItem(qkey()); } catch (e) {}
  }
  function flushQueue() {
    var q = readQueue();
    if (!q.length) return Promise.resolve();
    writeQueue([]);
    var chain = Promise.resolve();
    q.forEach(function (payload) {
      chain = chain.then(function () {
        return post(payload).catch(function () {
          writeQueue(readQueue().concat([payload])); // still unreachable: re-stash
        });
      });
    });
    return chain;
  }

  function submit() {
    if (saving || (!pending && !editing) || !edText.value.trim()) return;
    var author = edAuthor.value.trim();
    try { author ? localStorage.setItem("cm-author", author)
                 : localStorage.removeItem("cm-author"); } catch (e) {}
    var anchor = pending && Object.assign({}, pending.anchor);
    var tooltip = !editing && edTarget.value === "tooltip" && pending.tooltip;
    if (tooltip) {
      anchor.kind = "tooltip"; anchor.tooltip_trigger = tooltip.trigger; anchor.tooltip_text = tooltip.text;
    }
    var payload = editing ? { action: "edit", id: editing.id, comment: edText.value.trim(),
      author: author || undefined, expected_updated: editing.updated || editing.created || null,
    } : { action: "add", comment: {
      page: pending.page, quote: tooltip ? tooltip.text : pending.quote, comment: edText.value.trim(),
      occurrence: tooltip ? tooltip.occurrence : pending.occurrence,
      prefix: tooltip ? tooltip.prefix : pending.prefix, suffix: tooltip ? tooltip.suffix : pending.suffix,
      author: author || undefined, anchor: anchor, client_created: new Date().toISOString(),
    } };
    saving = true;
    editor.querySelectorAll("button,input,textarea,select").forEach(function (el) { el.disabled = true; });
    function ready() {
      saving = false;
      editor.querySelectorAll("button,input,textarea,select").forEach(function (el) { el.disabled = false; });
    }
    post(payload).then(function () { ready(); pending = null; editing = null; hideAll(); },
      function (err) {
        ready();
        if (editing || err.status) {
          showToast(err.status === 409 ? "<b>Comment changed elsewhere. Your draft is still here.</b><br>Copy it before cancelling; reopen the comment from the list to review the latest version." :
            "<b>Not saved. Your draft is still here.</b><br>Please retry when the comment server is available.");
          if (err.status === 409) refetch();
          return;
        }
        writeQueue(readQueue().concat([payload]));
        pending = null; hideAll();
        showToast("<b>Not saved \u2014 comment server unreachable.</b><br>" +
          "Kept in this browser (" + readQueue().length + " queued) and sent automatically " +
          "when the server at " + apiHost + " is back. Do not clear site data.", 12000);
      });
  }
  editor.querySelector("#cm-save").addEventListener("click", submit);
  editor.querySelector("#cm-cancel").addEventListener("click", function () { pending = null; editing = null; hideAll(); });

  // keys typed in the editor must not reach bespoke's navigation handler
  editor.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && !saving) { pending = null; editing = null; hideAll(); }
    else if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); submit(); }
    e.stopPropagation();
  });
  card.addEventListener("keydown", function (e) { e.stopPropagation(); });
  list.addEventListener("keydown", function (e) { e.stopPropagation(); });

  // Keep comments/history reachable even on a deck with zero open comments.
  // Any comments queued offline flush first, so they show in the same pass.
  function warnStranded() {
    var n = readQueue().length;
    if (n) showToast("<b>" + n + " comment" + (n > 1 ? "s" : "") +
      " on this deck are queued in this browser, not saved.</b><br>" +
      "The comment server at " + apiHost + " is unreachable \u2014 start it " +
      "(scripts/start.sh; scripts/install_services.sh keeps it alive) " +
      "and reload to send them.", 15000);
  }

  function mountBadge(osc) {
    badge = document.createElement("button");
    badge.type = "button";
    badge.className = "dl-export cm-badge";
    badge.title = "Comments and history — select text or press Ctrl/⌘ + Alt + M to add";
    badge.setAttribute("aria-label", "Comments and history");
    badge.innerHTML = "<span></span>";
    badge.addEventListener("click", function (e) {
      e.preventDefault(); e.stopPropagation();
      if (editor.style.display === "block") { edText.focus(); return; }
      var r = badge.getBoundingClientRect();
      list.style.display === "block" ? hideAll() : showList(r.left, r.top);
    });
    if (!osc) { badge.id = "cm-badge-fallback"; badge.classList.add("cm-btn"); }
    (osc || document.body).appendChild(badge);
    render(); // badge count for already-fetched comments
  }
  DeckClient.onOsc(mountBadge, function () { mountBadge(null); });
  fetch(base + "/healthz").then(function (r) {
    if (!r.ok) { warnStranded(); return; }
    flushQueue().then(refetch, refetch);
  }).catch(warnStranded);
})();
