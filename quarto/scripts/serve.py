#!/usr/bin/env python3
"""The deck server (:8093): serve the rendered decks at their old Marp URLs,
re-render a deck when its source changes, live-update open pages — and answer
the comments/export API (scripts/pptx_export/export_server.py) in the same process.

    .venv/bin/python quarto/scripts/serve.py [--port 8093] [--api-port 8094]

URLs are paths in decks/, as they always were (decks render in place):

    /                               landing page (quarto/scripts/gen_index.py)
    /<category>/                    category page
    /<category>/<deck>/slides.md    the deck: its rendered slides.html (.html works too)
    /<deck>/slides.md               short alias: redirects to the deck's category path
    /quarto/themes/, /quarto/vendor/  theme CSS and MathJax (decks link them relatively)

A page load is a plain file read. A watcher polls the deck sources and
renders only the changed deck; a Marp `slides.md` (e.g. a deck built with a
Marp slide-deck skill) is first converted to `slides.qmd`
next to it (marp2qmd.py --keep), so it stays the source. Open pages poll
GET /__stamp?p=<path> (served only here) and swap in re-rendered slides.

API routes (/healthz, /comments/, /raw/, /html/, /pptx/, /pdf/, /preview/)
are served on both ports; the decks' layers call the API port this server
injects into every page (window.DECK_API_PORT = --api-port, default :8094, where
exported HTML files already in circulation post their comments). DECK_API_PORT
(env) overrides it, e.g. to point a test instance at another API.
"""
import argparse
import fcntl
import html
import os
import subprocess
import sys
import threading
import time
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DECKS = REPO / "decks"
LOCK = REPO / ".quarto" / "render.lock"  # shared with quarto/scripts/render_all.sh: one render at a time
WATCH_EXT = {".qmd", ".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".css", ".js", ".json", ".mp4"}
SKIP_DIRS = {"export", "__pycache__", "node_modules", "slides_files"}
SHARED = ("quarto/themes/", "quarto/vendor/")  # served from the repo root
API_PORT = os.environ.get("DECK_API_PORT")

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(REPO))
import marp2qmd  # noqa: E402
from scripts.pptx_export import export_server  # noqa: E402

API = ("/comments/", "/raw/", "/html/", "/pptx/", "/pdf/", "/preview/")
# Quarto rewrites a deck's slides.html in place, in stages (truncated to 0 bytes,
# pandoc output, post-processed) and adds to slides_files/ mid-render: a page
# loaded then is blank. Requests for a rendering deck's output wait for the render.
RENDERING: set[Path] = set()
RENDER_DONE = threading.Condition()


def is_api(path: str) -> bool:
    p = urllib.parse.urlsplit(path).path
    return p == "/healthz" or p.startswith(API)


def log(msg: str) -> None:
    sys.stderr.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    sys.stderr.flush()


def deck_dirs():
    """Every folder under decks/ holding slides.qmd or slides.md (symlinks not followed)."""
    for root, dirs, files in os.walk(DECKS):
        dirs[:] = [d for d in dirs if not d.startswith((".", "_")) and d not in SKIP_DIRS]
        if "slides.qmd" in files or "slides.md" in files:
            yield Path(root)


def newest_input(deck: Path) -> float:
    """Newest source mtime of a deck (export/ and the deck's own data files excluded)."""
    newest = 0.0
    for root, dirs, files in os.walk(deck):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if Path(f).suffix in WATCH_EXT and f != "comments.json" and f != "review.json":
                newest = max(newest, os.stat(os.path.join(root, f)).st_mtime)
    return newest


def watch(interval: float) -> None:
    LOCK.parent.mkdir(exist_ok=True)
    while True:
        lock = open(LOCK, "w")
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:  # a full build is running: its outputs are in flux
            lock.close()
            time.sleep(interval)
            continue
        try:
            scan()
        except Exception as e:  # noqa: BLE001 — never let one bad deck stop the watcher
            log(f"scan error: {type(e).__name__}: {e}")
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
            lock.close()
        time.sleep(interval)


def scan() -> None:
    """Convert new/changed Marp decks, then render every stale deck (one at a time)."""
    for deck in list(deck_dirs()):
        md, qmd = deck / "slides.md", deck / "slides.qmd"
        if md.exists() and not (deck / ".quarto-native").exists() and (
                not qmd.exists() or md.stat().st_mtime > qmd.stat().st_mtime):
            try:
                marp2qmd.convert(deck, keep=True)
            except Exception as e:  # noqa: BLE001
                log(f"convert FAILED {deck.relative_to(DECKS)}: {e}")
                continue
        if not qmd.exists():
            continue
        out = deck / "slides.html"
        try:
            src = newest_input(deck)  # sources as of now: an edit during the render stays newer
            stale = not out.exists() or src > out.stat().st_mtime
        except OSError:
            continue
        if stale:
            with RENDER_DONE:
                RENDERING.add(deck)
            try:
                render(deck, qmd, out, src)
            finally:
                with RENDER_DONE:
                    RENDERING.discard(deck)
                    RENDER_DONE.notify_all()


def render(deck: Path, qmd: Path, out: Path, src: float) -> None:
    """Render one deck; its output gets the mtime of the sources it was rendered from."""
    t = time.time()
    p = subprocess.run([str(REPO / "quarto" / "bin" / "quarto"), "render", str(qmd.relative_to(REPO)), "--quiet"],
                       cwd=REPO, capture_output=True, text=True)
    if p.returncode == 0 and out.exists():
        # as new as the sources it was rendered from (even if the render reused
        # output) — not now, which would hide an edit made during the render
        os.utime(out, (src, src))
        log(f"rendered {deck.relative_to(DECKS)} in {time.time() - t:.1f}s")
    else:
        log(f"render FAILED {deck.relative_to(DECKS)}: {(p.stderr or p.stdout)[-400:]}")
        if out.exists():
            os.utime(out, (src, src))  # don't retry in a loop; the next edit retries
        else:  # placeholder so a never-rendered deck isn't retried every second
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(f"<pre>render failed — fix the deck and save again\n\n"
                           f"{html.escape((p.stderr or p.stdout)[-2000:])}</pre>")
            os.utime(out, (src, src))


def canonical(first: str) -> str | None:
    """decks/<category>/<first> for a short alias /<first>/…, else None."""
    if (DECKS / first).is_dir() and not (DECKS / first).is_symlink():
        return None
    for cat in sorted(DECKS.iterdir()):
        d = cat / first
        if cat.is_dir() and not cat.name.startswith((".", "_")) and \
                ((d / "slides.qmd").exists() or (d / "slides.md").exists()):
            return f"{cat.name}/{first}"
    return None


def candidates(rel: str):
    if rel == "slides.md" or rel.endswith("/slides.md"):
        rel = rel[:-len("slides.md")] + "slides.html"
    return [DECKS / rel] + ([REPO / rel] if rel.startswith(SHARED) else [])


def locate(url_path: str) -> Path | None:
    """The file behind a URL path (see the module docstring), or None."""
    rel = urllib.parse.unquote(url_path).lstrip("/")
    parts = rel.split("/")
    if any(p.startswith(".") for p in parts if p):
        return None  # dotfiles (.git of a nested decks repo, .quarto-native …)
    if rel == "" or rel.endswith("/"):
        hits = [c / "index.html" for c in candidates(rel)]
    else:
        hits = candidates(rel)
    for f in hits:
        if f.is_file():
            return f
    return None


def hold(url_path: str) -> None:
    """Wait while the file behind url_path is render output of a deck being rendered."""
    f = candidates(urllib.parse.unquote(url_path).lstrip("/"))[0]
    with RENDER_DONE:
        RENDER_DONE.wait_for(lambda: not any(
            f == d / "slides.html" or d / "slides_files" in f.parents for d in RENDERING), timeout=120)


def is_dir(url_path: str) -> bool:
    rel = urllib.parse.unquote(url_path).lstrip("/")
    return any(c.is_dir() for c in candidates(rel))


LOGIN = (b"<!DOCTYPE html><meta charset=utf-8>"
         b"<body style='font:16px system-ui;background:#0a0a0a;color:#ccc;padding:3rem'>"
         b"Login required: open the URL <code>scripts/start.sh</code> printed (it ends in "
         b"<code>?token=&hellip;</code>; the token is in <code>.quarto/server-token</code>).")

PENDING = (b"<!DOCTYPE html><meta charset=utf-8><meta http-equiv=refresh content=3>"
           b"<body style='font:16px system-ui;background:#0a0a0a;color:#ccc;padding:3rem'>"
           b"Rendering this deck&hellip; the page refreshes by itself.")


class Handler(SimpleHTTPRequestHandler, export_server.ExportHandler):
    # POST / PUT / OPTIONS come from ExportHandler (API only)
    def _host_bad(self, login: bool = False) -> bool:
        """On a loopback bind, refuse a non-loopback Host (DNS rebinding), as the API does;
        with token login on, refuse a request without the token (401). ``login``: Host only."""
        if not export_server.host_allowed(self.headers.get("Host"), getattr(self.server, "bind_host", "127.0.0.1")):
            self.send_error(403, "host not allowed")
            return True
        if login or export_server.authorized(self.headers):
            return False
        self._send(401, LOGIN, "text/html; charset=utf-8")
        return True

    def _login(self, u) -> bool:
        """``?token=<token>``: set the login cookie and drop the token from the URL."""
        q = urllib.parse.parse_qs(u.query)
        if not export_server.token_ok((q.pop("token", None) or [""])[0]):
            return False
        self.send_response(302)
        port = self.server.server_address[1]
        self.send_header("Set-Cookie", f"{export_server.COOKIE}{port}={export_server.TOKEN}; Path=/; "
                         "Max-Age=31536000; HttpOnly; SameSite=Strict")
        self.send_header("Location", urllib.parse.quote("/" + urllib.parse.unquote(u.path).lstrip("/")) + (
            "?" + urllib.parse.urlencode(q, doseq=True) if q else ""))
        self.send_header("Content-Length", "0")
        self.end_headers()
        return True

    def do_GET(self):  # noqa: N802
        if is_api(self.path):
            return export_server.ExportHandler.do_GET(self)
        u = urllib.parse.urlsplit(self.path)
        if self._host_bad(login=True) or self._login(u) or self._host_bad():
            return
        if u.path == "/__stamp":
            p = urllib.parse.parse_qs(u.query).get("p", [""])[0]
            f = locate(p)
            return self._text(str(f.stat().st_mtime_ns if f else 0).encode())
        parts = urllib.parse.unquote(u.path).lstrip("/").split("/")
        if len(parts) > 1 and parts[0]:
            canon = canonical(parts[0])
            if canon:
                return self._redirect("/" + canon + "/" + "/".join(parts[1:]), u.query)
        hold(u.path)
        f = locate(u.path)
        if f is None:
            if not u.path.endswith("/") and is_dir(u.path):
                return self._redirect(urllib.parse.unquote(u.path) + "/", u.query)
            if u.path.endswith(("/slides.md", "/slides.html")):
                deck = DECKS / urllib.parse.unquote(u.path).lstrip("/").rsplit("/", 1)[0]
                if (deck / "slides.qmd").exists() or (deck / "slides.md").exists():
                    return self._send(200, PENDING, "text/html; charset=utf-8")
            return self.send_error(404)
        rng = self.headers.get("Range", "")
        if rng.startswith("bytes="):
            return self._range(f, rng)
        self._file(f)

    def do_HEAD(self):  # noqa: N802
        if self._host_bad():
            return
        hold(urllib.parse.urlsplit(self.path).path)
        f = locate(urllib.parse.urlsplit(self.path).path)
        if f is None:
            return self.send_error(404)
        self.send_response(200)
        self.send_header("Content-Type", self.guess_type(str(f)))
        self.send_header("Content-Length", str(f.stat().st_size))
        self.end_headers()

    def _redirect(self, path: str, query: str):
        self.send_response(302)
        # path is decoded; quote it once
        self.send_header("Location", urllib.parse.quote("/" + path.lstrip("/")) + ("?" + query if query else ""))
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _text(self, body: bytes):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send(self, code: int, body: bytes, ctype: str):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _file(self, f: Path):
        if API_PORT and f.suffix == ".html":
            body = f.read_bytes().replace(
                b"<head>", f"<head>\n<script>window.DECK_API_PORT = {int(API_PORT)};</script>".encode(), 1)
            return self._send(200, body, "text/html; charset=utf-8")
        st = f.stat()
        self.send_response(200)
        self.send_header("Content-Type", self.guess_type(str(f)))
        self.send_header("Content-Length", str(st.st_size))
        self.send_header("Last-Modified", self.date_time_string(int(st.st_mtime)))
        self.end_headers()
        with open(f, "rb") as fh:
            while chunk := fh.read(1 << 20):
                self.wfile.write(chunk)

    def _range(self, f: Path, rng: str):
        """Single byte range: video seeking and pdf.js range loading need it."""
        size = f.stat().st_size
        a, _, b = rng[len("bytes="):].split(",")[0].partition("-")
        try:
            start, end = (int(a), int(b) if b else size - 1) if a else (size - int(b), size - 1)
        except ValueError:
            return self._file(f)
        if not (0 <= start <= end < size):
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.end_headers()
            return
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(str(f)))
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        with open(f, "rb") as fh:
            fh.seek(start)
            left = end - start + 1
            while left > 0:
                chunk = fh.read(min(1 << 20, left))
                if not chunk:
                    break
                self.wfile.write(chunk)
                left -= len(chunk)

    def end_headers(self):
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-cache")  # always revalidate: decks change on save
        super().end_headers()

    def log_message(self, fmt, *args):  # page loads stay quiet; API requests are logged
        if is_api(getattr(self, "path", "")):  # unset on a malformed request line
            super().log_message(fmt, *args)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--host", default=os.environ.get("SLIDES_HOST", "127.0.0.1"),
                    help="bind address; 0.0.0.0 to reach it from other machines")
    ap.add_argument("--port", type=int, default=8093)
    ap.add_argument("--api-port", type=int, default=8094, help="second port for the API (0: none)")
    ap.add_argument("--interval", type=float, default=1.0)
    args = ap.parse_args()
    if export_server.auth_enabled():
        export_server.TOKEN = export_server.load_token()
    export_server.ORIGIN_PORTS = {args.port} | ({args.api_port} if args.api_port else set())
    global API_PORT
    if args.api_port and not API_PORT:
        # The decks' layers (and HTML exported by this server) must call THIS
        # server's API port, never an assumed :8094.
        API_PORT = str(args.api_port)
        os.environ.setdefault("SLIDES_EXPORT_PORT", API_PORT)  # scripts/export.sh html
    threading.Thread(target=watch, args=(args.interval,), daemon=True).start()
    ThreadingHTTPServer.daemon_threads = True
    ThreadingHTTPServer.allow_reuse_address = True  # restart cleanly after a kill
    if args.api_port:
        api = ThreadingHTTPServer((args.host, args.api_port), Handler)
        api.bind_host = args.host  # export_server's Host/Origin guard
        threading.Thread(target=api.serve_forever, daemon=True).start()
    log(f"serving {DECKS} on http://{args.host}:{args.port}/"
        + (f" (API also on :{args.api_port})" if args.api_port else "")
        + ("; token login on (.quarto/server-token)" if export_server.TOKEN else "; token login OFF"))
    site = ThreadingHTTPServer((args.host, args.port), Handler)
    site.bind_host = args.host
    site.serve_forever()


if __name__ == "__main__":
    main()
