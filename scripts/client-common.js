/* Shared helpers for the browser layers in every deck (control-bar buttons,
 * edit mode, comments). Injected FIRST by quarto/scripts/gen_client.py (via
 * include-after-body), so exported HTML carries them too. Must never contain
 * a literal closing script tag. */
var DeckClient = (function () {
  // Deck id + API base. On the dev server both derive from the URL; exported
  // single-file HTML ships window.CM_CONFIG = {deck, base, exported} instead.
  // Decks are served at /<category>/<deck>/slides.md (or .html): deck id
  // <category>/<deck>. The API port comes from the server that served the page
  // (quarto/scripts/serve.py injects window.DECK_API_PORT); 8094 is only the
  // last-resort default for a page served without it.
  function deckInfo() {
    // Static site (GitHub Pages, scripts/build_site.sh sets DECK_STATIC): no
    // server, so no edit mode and no live comments; deck-controls.html links
    // the prebuilt downloads instead.
    if (typeof window !== "undefined" && window.DECK_STATIC) return null;
    var cfg = (typeof window !== "undefined" && window.CM_CONFIG) || null;
    var m = location.pathname.match(/^\/(.+?)\/slides\.(?:md|html)$/);
    if (!m && !(cfg && cfg.deck && cfg.base)) return null;
    var port = (typeof window !== "undefined" && window.DECK_API_PORT) || 8094;
    return {
      deck: cfg && cfg.deck ? cfg.deck : decodeURIComponent(m[1]),
      base: cfg && cfg.base ? cfg.base
        : location.protocol + "//" + location.hostname + ":" + port,
      exported: !!(cfg && cfg.exported),
    };
  }

  // reveal.js has no on-screen controller like Marp's bespoke one: build an
  // equivalent bar once (hover to show), so every layer can mount into it
  // through onOsc. It keeps bespoke's class name, which the layers style.
  function revealOsc() {
    if (typeof document === "undefined" || !document.querySelector(".reveal .slides")) return null;
    var osc = document.querySelector(".bespoke-marp-osc");
    if (osc) return osc;
    var css = document.createElement("style");
    css.textContent =
      ".reveal-osc{position:fixed;left:50%;bottom:10px;transform:translateX(-50%);" +
      "z-index:2147483646;display:flex;align-items:center;gap:2px;padding:2px 6px;" +
      "background:rgba(0,0,0,.7);border-radius:8px;opacity:0;transition:opacity .2s;" +
      "white-space:nowrap}" +
      ".reveal-osc.show,.reveal-osc:hover,.reveal-osc:focus-within{opacity:1}" +
      "@media print{.reveal-osc{display:none!important}}";
    document.head.appendChild(css);
    osc = document.createElement("div");
    osc.className = "bespoke-marp-osc reveal-osc";
    document.body.appendChild(osc);
    var hide = null;
    document.addEventListener("mousemove", function () {
      osc.classList.add("show");
      clearTimeout(hide);
      hide = setTimeout(function () { osc.classList.remove("show"); }, 2000);
    });
    return osc;
  }

  // Wait for the on-screen controller bar, then mount into it; the fallback
  // runs if the bar never appears (no reveal.js deck on the page).
  function onOsc(add, fallback) {
    var tries = 0;
    revealOsc();
    var t = setInterval(function () {
      var osc = document.querySelector(".bespoke-marp-osc");
      if (osc) {
        clearInterval(t);
        add(osc);
      } else if (++tries > 50) {
        clearInterval(t);
        if (fallback) fallback();
      }
    }, 100);
  }

  return { deckInfo: deckInfo, onOsc: onOsc };
})();

if (typeof module !== "undefined" && module.exports) {
  module.exports = DeckClient;
}
