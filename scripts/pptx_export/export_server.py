"""On-demand export endpoint for the dev server.

    .venv/bin/python -m scripts.pptx_export.export_server [--port 8094]

Serves ``GET /pptx/<category>/<deck>`` (editable .pptx),
``GET /html/<category>/<deck>`` (single self-contained .html) and
``GET /pdf/<category>/<deck>``: runs
``scripts/export.sh`` if the cached export is stale, then returns the file
as a download. Also serves ``GET /raw/<category>/<deck>`` (source text),
``PUT /raw/<category>/<deck>`` (write with etag guard), and
``OPTIONS /raw/<category>/<deck>`` (CORS preflight), and
``POST /preview/<deck>`` (``{markdown, page}`` → ``{html}`` of that one
slide, rendered with pandoc for the edit pane's live preview). Started/stopped
inside the :8093 deck server (quarto/scripts/serve.py), also on :8094; run
standalone with the command above for a test instance.

A deck's source is ``slides.qmd`` (``slides.tpl.qmd`` for template decks);
a Marp-sourced deck (``slides.md``) is edited as Marp and converted by the
deck server.

Exports are serialized with a lock — an export takes ~10–60s and concurrent
Chrome runs would thrash the machine — but /raw/* requests stay responsive on
separate threads.
"""

import argparse
import hmac
import json
import os
import re
import secrets
import subprocess
import sys
import threading
import time
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# fmt → (export.sh format, exports/<deck> suffix, download suffix, MIME)
FORMATS = {
    "pptx": (
        "pptx-edit", ".editable.pptx", ".editable.pptx",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
    "html": ("html", ".html", ".html", "text/html; charset=utf-8"),
    "pdf": ("pdf", ".pdf", ".pdf", "application/pdf"),
}

_EXPORT_LOCK = threading.Lock()  # exports stay serial; /raw/* stays responsive
_RAW_WRITE_LOCK = threading.Lock()  # serializes the check-then-write and the tpl rebuild


# The reader settings of _quarto.yml (`from:`), reused by /preview.
QUARTO_READER = "commonmark_x+hard_line_breaks-smart"


def deck_layout(repo: Path, deck: str) -> tuple[Path, Path, str, str]:
    """(decks root, deck dir, built file, template file) for a deck id
    ``<category>/<deck>``: Quarto ``slides.qmd``, or Marp ``slides.md`` when the
    deck is Marp-sourced (its slides.qmd is generated from it)."""
    root = repo / "decks"
    if (root / deck / "slides.md").is_file():
        return root, root / deck, "slides.md", "slides.tpl.md"
    return root, root / deck, "slides.qmd", "slides.tpl.qmd"


def parse_path(path: str) -> tuple[str, str] | None:
    """``/pptx/<deck>`` or ``/html/<deck>`` → (fmt, deck id), else None."""
    path = urllib.parse.unquote(urllib.parse.urlsplit(path).path)
    for fmt in FORMATS:
        prefix = f"/{fmt}/"
        if path.startswith(prefix):
            deck = path[len(prefix):].strip("/")
            return (fmt, deck) if deck else None
    return None


def resolve_deck(repo: Path, deck: str) -> str | None:
    """Validate a deck id against the repo; returns it iff it names a real
    deck whose resolved path stays under ``decks/`` (alias symlinks OK)."""
    if not deck or deck.startswith(("/", ".")) or ".." in deck.split("/"):
        return None
    root, deck_dir, built, _ = deck_layout(repo, deck)
    slides = deck_dir / built
    try:
        decks_root = root.resolve()
        if not slides.resolve().is_relative_to(decks_root):
            return None  # symlink escaping the decks tree
        if not slides.is_file():
            return None
    except OSError:
        return None
    return deck


def parse_raw_path(path: str) -> str | None:
    """``/raw/<deck>`` → deck id, else None."""
    path = urllib.parse.unquote(urllib.parse.urlsplit(path).path)
    if path.startswith("/raw/"):
        deck = path[len("/raw/"):].strip("/")
        return deck or None
    return None


def raw_target(repo: Path, deck: str) -> Path | None:
    """The file edit mode reads/writes: slides.tpl.qmd for template-generated
    decks (slides.qmd is a build artifact there), else slides.qmd (.md for
    Marp-sourced decks)."""
    if resolve_deck(repo, deck) is None:
        return None
    root, deck_dir, built, tpl_name = deck_layout(repo, deck)
    tpl = deck_dir / tpl_name
    if tpl.is_file():
        try:
            if not tpl.resolve().is_relative_to(root.resolve()):
                return None  # tpl symlink escaping the decks tree
        except OSError:
            return None
        return tpl
    return deck_dir / built


def read_raw(repo: Path, deck: str) -> tuple[bytes, str, bool] | None:
    """(target bytes, etag, is_tpl), or None if invalid."""
    target = raw_target(repo, deck)
    if target is None:
        return None
    data = target.read_bytes()
    etag = str(target.stat().st_mtime_ns)
    return data, etag, target.name.startswith("slides.tpl.")


def write_raw(repo: Path, deck: str, body: bytes,
              if_match: str | None) -> tuple[int, str]:
    """Guarded write of the deck's edit target. Returns (status, etag|error)."""
    target = raw_target(repo, deck)
    if target is None:
        return 404, "unknown deck"
    if not if_match:
        return 428, "If-Match header required"
    if str(target.stat().st_mtime_ns) != if_match:
        return 412, "file changed on disk"
    target.write_bytes(body)
    return 200, str(target.stat().st_mtime_ns)


def _build_deck(repo: Path, deck: str) -> subprocess.CompletedProcess:
    """Regenerate slides.qmd from slides.tpl.qmd (Marp: .md) via the deck's own build script."""
    return subprocess.run(
        [sys.executable, "build_deck.py"],
        cwd=deck_layout(repo, deck)[1], capture_output=True, text=True, timeout=60,
    )


_HR = re.compile(r"^---\s*$")
_FENCE = re.compile(r"^(```|~~~)")


def split_slides(text: str) -> list[str]:
    """Slide fragments of a Marp document — same rules as the client-side
    splitter in scripts/edit-mode.js (front-matter, fence-aware ``---``)."""
    lines = text.split("\n")
    fm_end = 0
    if lines and _HR.match(lines[0]):
        for j in range(1, len(lines)):
            if _HR.match(lines[j]):
                fm_end = j + 1
                break
    bounds: list[int] = []
    fence = None
    for i in range(fm_end, len(lines)):
        line = lines[i]
        m = _FENCE.match(line)
        if m:
            if fence is None:
                fence = m.group(1)
            elif line.startswith(fence):
                fence = None
            continue
        if fence is None and _HR.match(line):
            bounds.append(i)
    slides, start = [], fm_end
    for b in bounds:
        slides.append("\n".join(lines[start:b]))
        start = b + 1
    slides.append("\n".join(lines[start:]))
    return slides


def _source_context(repo: Path, deck: str, page: int) -> dict:
    """Snapshot of the source a comment refers to, for later playback:
    HEAD commit, whether the edit target has uncommitted changes, and the
    slide's current markdown. Best-effort — missing git etc. just omits keys."""
    ctx: dict = {}
    target = raw_target(repo, deck)
    if target is None:
        return ctx
    try:
        head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=repo,
                              capture_output=True, text=True, timeout=10)
        if head.returncode == 0:
            ctx["commit"] = head.stdout.strip()
            st = subprocess.run(
                ["git", "status", "--porcelain", "--", str(target.relative_to(repo))],
                cwd=repo, capture_output=True, text=True, timeout=10)
            if st.returncode == 0:
                ctx["dirty"] = bool(st.stdout.strip())
    except (OSError, subprocess.TimeoutExpired):
        pass
    try:
        slides = split_slides(target.read_text())
        ctx["source_file"] = target.name
        ctx["slide_src"] = slides[min(page - 1, len(slides) - 1)]
    except OSError:
        pass
    return ctx


def parse_comments_path(path: str) -> str | None:
    """``/comments/<deck>`` → deck id, else None."""
    path = urllib.parse.unquote(urllib.parse.urlsplit(path).path)
    if path.startswith("/comments/"):
        deck = path[len("/comments/"):].strip("/")
        return deck or None
    return None


def read_comments(repo: Path, deck: str) -> dict | None:
    """The deck's comments.json content ({"comments": [...]}), or None if the
    deck is invalid. A missing or unparsable file reads as no comments."""
    if resolve_deck(repo, deck) is None:
        return None
    f = deck_layout(repo, deck)[1] / "comments.json"
    if not f.is_file():
        return {"comments": []}
    try:
        data = json.loads(f.read_text())
    except ValueError:
        return {"comments": []}
    if not isinstance(data, dict) or not isinstance(data.get("comments"), list):
        return {"comments": []}
    return data


def add_comment(repo: Path, deck: str, fields: dict) -> tuple[int, dict | str]:
    """Append a comment ({page, quote, comment}); returns (200, updated doc)
    or (4xx, error). The server assigns id/created/status."""
    data = read_comments(repo, deck)
    if data is None:
        return 404, "unknown deck"
    if not isinstance(fields, dict):
        return 400, "comment must be an object"
    page, quote, comment = fields.get("page"), fields.get("quote"), fields.get("comment")
    if not (isinstance(page, int) and page >= 1
            and isinstance(quote, str) and quote.strip()
            and isinstance(comment, str) and comment.strip()):
        return 400, "need page (int >= 1), quote and comment (non-empty strings)"
    entry = {
        "id": f"c-{time.time_ns()}",
        "page": page,
        "quote": quote.strip(),
        "comment": comment.strip(),
        "status": "open",
        "created": datetime.now().astimezone().isoformat(timespec="microseconds"),
    }
    # optional anchor disambiguation: which occurrence of the quote on the
    # page, plus surrounding context (for agents locating it in the source)
    occurrence = fields.get("occurrence")
    if isinstance(occurrence, int) and not isinstance(occurrence, bool) and occurrence >= 0:
        entry["occurrence"] = occurrence
    for key in ("prefix", "suffix"):
        val = fields.get(key)
        if isinstance(val, str) and val:
            entry[key] = val[:200]
    author = fields.get("author")
    if isinstance(author, str) and author.strip():
        entry["author"] = author.strip()[:80]
    anchor = fields.get("anchor")
    if isinstance(anchor, dict) and anchor.get("kind") in ("slide", "tooltip"):
        entry["anchor"] = {"kind": anchor["kind"]}
        for key, limit in (("slide_id", 200), ("heading", 500),
                           ("tooltip_text", 10000), ("tooltip_trigger", 1000)):
            val = anchor.get(key)
            if isinstance(val, str) and val.strip():
                entry["anchor"][key] = val.strip()[:limit]
    client_created = fields.get("client_created")
    if isinstance(client_created, str) and len(client_created) <= 64:
        try:
            if datetime.fromisoformat(client_created.replace("Z", "+00:00")).tzinfo:
                entry["client_created"] = client_created
        except ValueError:
            pass
    entry["updated"] = entry["created"]
    entry["history"] = [_comment_event(entry, "created", entry["created"], author)]
    entry.update(_source_context(repo, deck, page))
    data["comments"].append(entry)
    _write_comments(repo, deck, data)
    return 200, data


def resolve_comment(repo: Path, deck: str, cid: str) -> tuple[int, dict | str]:
    """Compatibility entrypoint for callers that only resolve a comment."""
    return update_comment(repo, deck, cid, "resolve")


def _comment_event(comment: dict, action: str, at: str | None,
                   author: str | None = None) -> dict:
    event = {"action": action, "at": at, "comment": comment.get("comment", ""),
             "status": comment.get("status", "open")}
    if isinstance(author, str) and author.strip():
        event["author"] = author.strip()[:80]
    return event


def update_comment(repo: Path, deck: str, cid: str, action: str,
                   comment: str | None = None, author: str | None = None,
                   expected_updated: str | None = None) -> tuple[int, dict | str]:
    """Edit or change status without altering the original target or source.

    History is append-only. Legacy entries acquire history on their first
    change; a legacy resolution's time is unknown, so it remains null.
    An optional revision check prevents a stale browser overwriting a change.
    HTTP callers hold _RAW_WRITE_LOCK across the read/check/write operation.
    """
    data = read_comments(repo, deck)
    if data is None:
        return 404, "unknown deck"
    if action not in ("edit", "resolve", "reopen"):
        return 400, "unknown action"
    if action == "edit" and not (isinstance(comment, str) and comment.strip()):
        return 400, "comment must be a non-empty string"
    if expected_updated is not None and not isinstance(expected_updated, str):
        return 400, "expected_updated must be a timestamp string"
    for c in data["comments"]:
        if c.get("id") == cid:
            if expected_updated is not None and expected_updated != (c.get("updated") or c.get("created")):
                return 409, "comment changed; reload before saving"
            status = "resolved" if action == "resolve" else "open"
            if ((action == "edit" and c.get("comment") == comment.strip())
                    or (action != "edit" and c.get("status", "open") == status)):
                return 200, data
            if not isinstance(c.get("history"), list) or not c["history"]:
                created = _comment_event(c, "created", c.get("created"), c.get("author"))
                created["status"] = "open"
                c["history"] = [created]
                if c.get("status") == "resolved":
                    c["history"].append(_comment_event(c, "resolved", None))
            if action == "edit":
                c["comment"] = comment.strip()
            else:
                c["status"] = status
            c["updated"] = datetime.now().astimezone().isoformat(timespec="microseconds")
            event_action = {"edit": "edited", "resolve": "resolved", "reopen": "reopened"}[action]
            c["history"].append(_comment_event(c, event_action, c["updated"], author))
            _write_comments(repo, deck, data)
            return 200, data
    return 404, "unknown comment id"


def _write_comments(repo: Path, deck: str, data: dict) -> None:
    f = deck_layout(repo, deck)[1] / "comments.json"
    f.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def _newest_mtime(*paths: Path) -> float:
    newest = 0.0
    for p in paths:
        if p.is_file():
            newest = max(newest, p.stat().st_mtime)
        elif p.is_dir():
            for f in p.rglob("*"):
                if f.is_file():
                    newest = max(newest, f.stat().st_mtime)
    return newest


def is_stale(repo: Path, deck: str, fmt: str) -> bool:
    """True if the cached export is missing or older than its inputs
    (deck folder, exporter code, export script, themes)."""
    out = repo / "exports" / f"{deck}{FORMATS[fmt][1]}"
    if not out.is_file():
        return True
    q = repo / "quarto"
    inputs = _newest_mtime(
        (repo / "decks" / deck).resolve(),
        repo / "scripts" / "pptx_export",
        repo / "scripts" / "export.sh", repo / "_quarto.yml",
        q / "themes", q / "shim", q / "filters",
    )
    if fmt == "html":
        inputs = max(inputs, _newest_mtime(
            repo / "scripts" / "comments.js",
            repo / "scripts" / "client-common.js",
        ))
    return out.stat().st_mtime < inputs


def _export(repo: Path, deck: str, fmt: str) -> subprocess.CompletedProcess:
    cmd = ["bash", "scripts/export.sh", deck, FORMATS[fmt][0]]
    return subprocess.run(cmd, cwd=repo, capture_output=True, text=True, timeout=600)


def parse_preview_path(path: str) -> str | None:
    """``/preview/<deck>`` → deck id, else None."""
    path = urllib.parse.unquote(urllib.parse.urlsplit(path).path)
    if path.startswith("/preview/"):
        deck = path[len("/preview/"):].strip("/")
        return deck or None
    return None


def _pandoc(repo: Path) -> list[str]:
    """Quarto's bundled pandoc (fast: no quarto CLI start-up), else `quarto pandoc`."""
    found = sorted((repo / "quarto" / ".dist" / "quarto" / "bin" / "tools").glob("**/pandoc"))
    return [str(found[0])] if found else [str(repo / "quarto" / "bin" / "quarto"), "pandoc"]


def render_preview(repo: Path, deck: str, markdown: str, page: int) -> tuple[int, str]:
    """HTML of one slide of an (unsaved) deck source, for live preview.
    Approximate by design — pandoc with _quarto.yml's reader and Lua filter,
    but not Quarto's full pipeline; the save → re-render restores ground truth."""
    if resolve_deck(repo, deck) is None:
        return 404, "unknown deck"
    _, deck_dir, built, tpl_name = deck_layout(repo, deck)
    slides = split_slides(markdown)
    frag = slides[min(max(page, 1), len(slides)) - 1]
    if (deck_dir / tpl_name).is_file():  # FIG tokens -> inline SVG, as the build does
        proc = subprocess.run(
            [sys.executable, str(repo / "scripts" / "fig_inline.py"), str(deck_dir), "--stdin"],
            input=frag, capture_output=True, text=True, timeout=20)
        if proc.returncode == 0:
            frag = proc.stdout
    if built == "slides.md":  # Marp source: the slide rewrites the deck server's conversion makes
        sys.path.insert(0, str(REPO / "quarto" / "scripts"))
        import marp2qmd
        frag = marp2qmd.convert_body(frag, lambda _msg: None)
    proc = subprocess.run(
        _pandoc(repo) + ["-f", QUARTO_READER, "-t", "html", "--mathjax",
                         "--lua-filter", str(repo / "quarto" / "filters" / "marp-compat.lua")],
        input=frag, cwd=deck_dir, capture_output=True, text=True, timeout=20)
    if proc.returncode != 0:
        return 500, proc.stderr[-1000:]
    return 200, proc.stdout


LOOPBACK = {"localhost", "127.0.0.1", "::1"}

# Token login (on unless SLIDES_AUTH=off): every request but /healthz and CORS
# preflights needs the token, as the X-Deck-Token header (agents, curl:
# `cat .quarto/server-token`) or the deck_token_<port> cookie the deck server
# sets when a page is opened with ?token=… (the login URL scripts/start.sh prints).
TOKEN: str | None = None
_TOKEN_IN_URL = re.compile(r"(\?|;|%3f)[^\s\"]*", re.I)  # drop queries/params whole, however written
TOKEN_FILE = REPO / ".quarto" / "server-token"
COOKIE = "deck_token_"


def auth_enabled() -> bool:
    return os.environ.get("SLIDES_AUTH", "on").strip().lower() != "off"  # same test as the scripts


def load_token(path: Path = TOKEN_FILE) -> str:
    """The server's token, created once (owner-only file) and kept across restarts."""
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not path.exists():
        tmp = path.with_name(f"{path.name}.{os.getpid()}")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as fh:
            fh.write(secrets.token_urlsafe(24) + "\n")
        try:
            os.link(tmp, path)  # atomic and never overwrites: a concurrent first start wins once
        except FileExistsError:
            pass
        finally:
            os.unlink(tmp)
    st = path.stat()
    if st.st_uid != os.getuid():
        raise SystemExit(f"{path} is not owned by this user")
    if st.st_mode & 0o077:
        path.chmod(0o600)
    token = path.read_text().strip()
    if len(token) < 16:
        raise SystemExit(f"{path} holds no usable token; delete it and start again")
    return token


def token_ok(value: str | None) -> bool:
    return bool(TOKEN and value) and hmac.compare_digest(value.encode(), TOKEN.encode())


def authorized(headers) -> bool:
    """No login configured, or the request carries the token (header or cookie)."""
    if TOKEN is None:
        return True
    if token_ok(headers.get("X-Deck-Token")):
        return True
    # split by hand: SimpleCookie drops the whole header over one odd cookie of another app
    for part in (headers.get("Cookie") or "").split(";"):
        k, _, v = part.strip().partition("=")
        if k.startswith(COOKIE) and token_ok(v.strip().strip('"')):
            return True
    return False


def host_allowed(host: str | None, bind: str) -> bool:
    """On a loopback bind, the Host header must name loopback too. A page
    whose DNS was rebound to 127.0.0.1 still sends its own name as Host, so
    this stops DNS-rebinding attacks that the Origin check alone can't."""
    if bind not in LOOPBACK:
        return True
    return urllib.parse.urlsplit("//" + (host or "")).hostname in LOOPBACK


ORIGIN_PORTS: set[int] = set()  # the deck server's own ports (serve.py sets them); empty: any


def origin_allowed(origin: str | None, host: str | None, path: str) -> bool:
    """Browser requests must come from this server's own pages: same host, http,
    and (when ORIGIN_PORTS is set) the deck or API port. No Origin means
    a non-browser client (curl, an agent). Origin "null" is an exported HTML
    file opened from disk; it may only use the comment API. Blocks drive-by
    writes from arbitrary websites without any token or login."""
    if not origin:
        return True
    if origin == "null":
        return parse_comments_path(path) is not None
    o = urllib.parse.urlsplit(origin)
    h = urllib.parse.urlsplit("//" + (host or ""))
    if o.scheme != "http" or not o.hostname or o.hostname != h.hostname:
        return False
    try:
        port = o.port or 80
    except ValueError:
        return False
    return not ORIGIN_PORTS or port in ORIGIN_PORTS


class ExportHandler(BaseHTTPRequestHandler):
    def _guard(self, auth: bool = True) -> bool:
        """True (and a 403/401 sent) when the request's Host/Origin is not allowed
        or, with token login on, it doesn't carry the token."""
        host = self.headers.get("Host")
        if not (host_allowed(host, getattr(getattr(self, "server", None), "bind_host", "127.0.0.1"))
                and origin_allowed(self.headers.get("Origin"), host, self.path)):
            self._respond(403, b"origin not allowed", "text/plain")
            return True
        if auth and not authorized(self.headers):
            self._respond(401, b"login required: open the deck URL scripts/start.sh prints "
                          b"(it carries ?token=...), or send X-Deck-Token: <.quarto/server-token>",
                          "text/plain")
            return True
        return False

    def do_GET(self):  # noqa: N802 (http.server API)
        if urllib.parse.urlsplit(self.path).path == "/healthz":
            return self._respond(200, b"ok", "text/plain")
        if self._guard():
            return

        cm_deck = parse_comments_path(self.path)
        if cm_deck is not None:
            data = read_comments(REPO, cm_deck)
            if data is None:
                return self._respond(404, b"unknown deck", "text/plain")
            return self._respond(200, json.dumps(data).encode(),
                                 "application/json; charset=utf-8")

        raw_deck = parse_raw_path(self.path)
        if raw_deck is not None:
            got = read_raw(REPO, raw_deck)
            if got is None:
                return self._respond(404, b"unknown deck", "text/plain")
            data, etag, is_tpl = got
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "text/markdown; charset=utf-8")
            self.send_header("ETag", etag)
            self.send_header("X-Edit-Target", raw_target(REPO, raw_deck).name)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        parsed = parse_path(self.path)
        fmt, deck = parsed if parsed else (None, None)
        deck = resolve_deck(REPO, deck) if deck else None
        if deck is None:
            return self._respond(404, b"unknown deck", "text/plain")

        with _EXPORT_LOCK:
            if is_stale(REPO, deck, fmt):
                self.log_message("exporting %s (%s) ...", deck, fmt)
                try:
                    proc = _export(REPO, deck, fmt)
                except subprocess.TimeoutExpired:
                    return self._respond(504, b"export timed out", "text/plain")
                if proc.returncode != 0:
                    tail = (proc.stdout + proc.stderr)[-2000:]
                    return self._respond(
                        500, f"export failed:\n{tail}".encode(), "text/plain")

        _, out_suffix, dl_suffix, mime = FORMATS[fmt]
        out = REPO / "exports" / f"{deck}{out_suffix}"
        data = out.read_bytes()
        fname = deck.rsplit("/", 1)[-1] + dl_suffix
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", mime)
        self.send_header("Content-Disposition", f'attachment; filename="{fname}"')
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _cors(self):
        origin = self.headers.get("Origin")
        if origin and origin_allowed(origin, self.headers.get("Host"), self.path):
            self.send_header("Access-Control-Allow-Origin", origin)
            if origin != "null":  # exported files (login off) need no cookie
                self.send_header("Access-Control-Allow-Credentials", "true")  # the login cookie
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Expose-Headers", "ETag, X-Edit-Target")

    def do_OPTIONS(self):  # noqa: N802 (http.server API)
        if self._guard(auth=False):  # preflights carry no cookie
            return
        self.send_response(204)
        self._cors()
        self.send_header("Access-Control-Allow-Methods", "GET, PUT, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "If-Match, Content-Type, X-Deck-Token")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self):  # noqa: N802 (http.server API)
        if self._guard():
            return
        pv_deck = parse_preview_path(self.path)
        if pv_deck is not None:
            return self._preview(pv_deck)
        deck = parse_comments_path(self.path)
        if deck is None:
            return self._respond(404, b"not found", "text/plain")
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return self._respond(400, b"bad content-length", "text/plain")
        if length <= 0 or length > 100_000:
            return self._respond(400, b"empty or oversized body", "text/plain")
        body = self.rfile.read(length)
        if len(body) != length:
            return self._respond(400, b"truncated body", "text/plain")
        try:
            req = json.loads(body)
        except ValueError:
            return self._respond(400, b"bad json", "text/plain")
        if not isinstance(req, dict):
            return self._respond(400, b"request must be an object", "text/plain")
        with _RAW_WRITE_LOCK:
            if req.get("action") == "add":
                status, result = add_comment(REPO, deck, req.get("comment") or {})
            elif req.get("action") in ("edit", "resolve", "reopen"):
                status, result = update_comment(
                    REPO, deck, req.get("id") or "", req["action"],
                    comment=req.get("comment"), author=req.get("author"),
                    expected_updated=req.get("expected_updated"))
            else:
                status, result = 400, "unknown action"
        if status != 200:
            return self._respond(status, str(result).encode(), "text/plain")
        return self._respond(200, json.dumps(result).encode(),
                             "application/json; charset=utf-8")

    def do_PUT(self):  # noqa: N802 (http.server API)
        if self._guard():
            return
        deck = parse_raw_path(self.path)
        if deck is None:
            return self._respond(404, b"not found", "text/plain")
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return self._respond(400, b"bad content-length", "text/plain")
        if length <= 0 or length > 4_000_000:
            return self._respond(400, b"empty or oversized body", "text/plain")
        body = self.rfile.read(length)
        if len(body) != length:
            return self._respond(400, b"truncated body", "text/plain")
        with _RAW_WRITE_LOCK:
            status, result = write_raw(REPO, deck, body,
                                       self.headers.get("If-Match"))
            if status != 200:
                return self._respond(status, result.encode(), "text/plain")
            target = raw_target(REPO, deck)
            if target is not None and target.name.startswith("slides.tpl."):
                try:
                    proc = _build_deck(REPO, deck)
                except subprocess.TimeoutExpired:
                    return self._respond(
                        500, b"build_deck.py timed out", "text/plain",
                        etag=result)
                if proc.returncode != 0:
                    tail = (proc.stdout + proc.stderr)[-1000:]
                    return self._respond(
                        500, f"build failed:\n{tail}".encode(), "text/plain",
                        etag=result)
        self.send_response(200)
        self._cors()
        self.send_header("ETag", result)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _preview(self, deck: str):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return self._respond(400, b"bad content-length", "text/plain")
        if length <= 0 or length > 4_000_000:
            return self._respond(400, b"empty or oversized body", "text/plain")
        try:
            req = json.loads(self.rfile.read(length))
            markdown, page = req["markdown"], int(req.get("page") or 1)
            if not isinstance(markdown, str):
                raise ValueError
        except (ValueError, KeyError, TypeError):
            return self._respond(400, b"need {markdown, page}", "text/plain")
        try:
            status, out = render_preview(REPO, deck, markdown, page)
        except subprocess.TimeoutExpired:
            return self._respond(504, b"preview timed out", "text/plain")
        if status != 200:
            return self._respond(status, out.encode(), "text/plain")
        return self._respond(200, json.dumps({"html": out}).encode(),
                             "application/json; charset=utf-8")

    def log_message(self, fmt, *args):
        """Request log lines never carry the login token (a stray ?token= on an API path,
        in any case or encoding): the query string is dropped whole."""
        super().log_message(fmt, *(_TOKEN_IN_URL.sub(r"\1…", a) if isinstance(a, str) else a for a in args))

    def _respond(self, code: int, body: bytes, ctype: str, etag: str | None = None):
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", ctype)
        if etag is not None:
            self.send_header("ETag", etag)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _log(msg):
    """Unbuffered, timestamped line on stderr — survives a signal death, unlike a
    buffered print to a redirected stdout (which is how this server used to die
    without leaving a single line behind)."""
    import datetime as _dt
    sys.stderr.write(f"[{_dt.datetime.now():%Y-%m-%d %H:%M:%S}] export-server: {msg}\n")
    sys.stderr.flush()


def main(argv=None):
    import os
    import signal

    ap = argparse.ArgumentParser(prog="scripts.pptx_export.export_server")
    ap.add_argument("--port", type=int, default=8094)
    ap.add_argument("--host", default=os.environ.get("SLIDES_HOST", "127.0.0.1"),
                    help="bind address; 0.0.0.0 to reach it from other machines")
    args = ap.parse_args(argv)
    global TOKEN, ORIGIN_PORTS
    TOKEN = load_token() if auth_enabled() else None
    ORIGIN_PORTS = {args.port}
    ThreadingHTTPServer.allow_reuse_address = True     # restart cleanly after a kill
    ThreadingHTTPServer.daemon_threads = True
    server = ThreadingHTTPServer((args.host, args.port), ExportHandler)
    server.bind_host = args.host
    _log(f"listening on http://{args.host}:{args.port} pid={os.getpid()} ppid={os.getppid()} "
         f"pgid={os.getpgrp()} sid={os.getsid(0)} "
         "(GET /pptx/<deck>, /html/<deck>, /raw/<deck> GET/PUT, /comments/<deck> GET/POST, "
         "POST /preview/<deck>)")

    def _die(signum, _frame):
        # Record who is stopping us; without this the process vanished silently.
        _log(f"received {signal.Signals(signum).name} — shutting down "
             f"(ppid now {os.getppid()})")
        raise SystemExit(128 + signum)

    for sig in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        signal.signal(sig, _die)
    try:
        server.serve_forever()
    finally:
        _log("serve_forever returned")


if __name__ == "__main__":
    sys.exit(main())
