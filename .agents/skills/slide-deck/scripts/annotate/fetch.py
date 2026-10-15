#!/usr/bin/env python3
"""Fetch a source document (URL or local path) and emit the LLM-readable dump.

Detects PDF vs HTML, writes the raw source plus a location-tagged text dump
that the in-loop LLM reads to produce annotations.json.

Outputs into <workdir>:
  source.pdf | source.html   raw document
  meta.json                  {"type": "pdf"|"html", "source_file", "title", "origin"}
  dump.txt                   page-tagged (PDF) or readable (HTML) text for the LLM

Usage:
  fetch.py <url-or-path> [--workdir DIR]
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from urllib.parse import urlparse


def _is_url(s: str) -> bool:
    return urlparse(s).scheme in ("http", "https")


def _normalize_arxiv(url: str) -> str:
    # arxiv abstract pages -> direct PDF
    m = re.match(r"https?://arxiv\.org/abs/(.+?)/?$", url)
    if m:
        return f"https://arxiv.org/pdf/{m.group(1)}"
    return url


def _sniff_type(content_type: str, url_or_path: str, head: bytes) -> str:
    ct = (content_type or "").lower()
    if "pdf" in ct:
        return "pdf"
    if "html" in ct or "xml" in ct:
        return "html"
    if head[:5] == b"%PDF-":
        return "pdf"
    lower = url_or_path.lower().split("?")[0]
    if lower.endswith(".pdf"):
        return "pdf"
    if lower.endswith((".html", ".htm")):
        return "html"
    # default: treat as html (most blog posts omit a clean content-type)
    return "html"


def _singlefile_cmd(url: str, dest: str):
    """Resolve a SingleFile invocation: prefer an installed binary, else npx."""
    if shutil.which("single-file"):
        return ["single-file", url, dest]
    if shutil.which("npx"):
        return ["npx", "--yes", "--package", "single-file-cli", "single-file", url, dest]
    return None


def _capture_singlefile(url: str, dest: str) -> bool:
    """Save a faithful, self-contained copy of the page (inlined CSS/images).

    Returns True on success. Best-effort: any failure (no CLI, no browser,
    timeout) returns False so the caller falls back to a raw download.
    """
    cmd = _singlefile_cmd(url, dest)
    if cmd is None:
        return False
    try:
        subprocess.run(
            cmd, check=True, timeout=240,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except (subprocess.SubprocessError, OSError):
        return False
    return os.path.isfile(dest) and os.path.getsize(dest) > 0


def _load(source: str, workdir: str):
    if _is_url(source):
        import requests

        url = _normalize_arxiv(source)
        resp = requests.get(
            url,
            timeout=60,
            headers={"User-Agent": "Mozilla/5.0 (annotate-source)"},
            allow_redirects=True,
        )
        resp.raise_for_status()
        data = resp.content
        doc_type = _sniff_type(resp.headers.get("content-type", ""), url, data[:8])
        origin = url
        dest = os.path.join(workdir, f"source.{doc_type}")
        # For HTML, prefer a SingleFile capture so the annotated copy looks like
        # the original page. Fall back to the raw download if it is unavailable.
        if doc_type == "html" and _capture_singlefile(url, dest):
            return doc_type, dest, origin
        if doc_type == "html":
            print(
                "fetch.py: SingleFile unavailable — saved raw HTML "
                "(page may render without its original styling/images). "
                "Install with: npm i -g single-file-cli",
                file=sys.stderr,
            )
        with open(dest, "wb") as fh:
            fh.write(data)
        return doc_type, dest, origin

    path = os.path.expanduser(source)
    if not os.path.isfile(path):
        sys.exit(f"fetch.py: no such file: {path}")
    with open(path, "rb") as fh:
        data = fh.read()
    doc_type = _sniff_type("", path, data[:8])
    origin = os.path.abspath(path)
    dest = os.path.join(workdir, f"source.{doc_type}")
    with open(dest, "wb") as fh:
        fh.write(data)
    return doc_type, dest, origin


def _dump_pdf(src: str, dump_path: str) -> str:
    import fitz

    doc = fitz.open(src)
    title = doc.metadata.get("title") or ""
    parts = []
    for i, page in enumerate(doc, start=1):
        parts.append(f"[[page={i}]]")
        parts.append(page.get_text("text").strip())
    doc.close()
    with open(dump_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(parts))
    return title


def _dump_html(src: str, dump_path: str) -> str:
    from bs4 import BeautifulSoup

    with open(src, "r", encoding="utf-8", errors="replace") as fh:
        soup = BeautifulSoup(fh.read(), "lxml")
    title = soup.title.get_text(strip=True) if soup.title else ""
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "form"]):
        tag.decompose()
    body = soup.body or soup
    text = body.get_text("\n", strip=True)
    # collapse runs of blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    with open(dump_path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return title


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", help="URL or local path to the document")
    ap.add_argument("--workdir", default=".", help="output directory (default: cwd)")
    args = ap.parse_args()

    os.makedirs(args.workdir, exist_ok=True)
    doc_type, dest, origin = _load(args.source, args.workdir)
    dump_path = os.path.join(args.workdir, "dump.txt")
    if doc_type == "pdf":
        title = _dump_pdf(dest, dump_path)
    else:
        title = _dump_html(dest, dump_path)

    meta = {"type": doc_type, "source_file": dest, "title": title, "origin": origin}
    with open(os.path.join(args.workdir, "meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)

    print(json.dumps(meta, indent=2))
    print(f"\ndump.txt written ({os.path.getsize(dump_path)} bytes) — read it to build annotations.json")


if __name__ == "__main__":
    main()
