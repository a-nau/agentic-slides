"""Tests for the on-demand export HTTP endpoint (pure logic, no sockets)."""

import json
import io
import os
import time
from datetime import datetime

import pytest

from scripts.pptx_export import export_server


@pytest.fixture()
def repo(tmp_path):
    (tmp_path / "decks/tools/demo").mkdir(parents=True)
    (tmp_path / "decks/tools/demo/slides.md").write_text("# hi\n")
    (tmp_path / "scripts/pptx_export").mkdir(parents=True)
    (tmp_path / "scripts/export.sh").parent.mkdir(exist_ok=True)
    (tmp_path / "scripts/export.sh").write_text("#!/bin/bash\n")
    # legacy alias symlink, like decks/demo -> tools/demo
    os.symlink("tools/demo", tmp_path / "decks/demo")
    return tmp_path


class TestResolveDeck:
    def test_valid_deck(self, repo):
        assert export_server.resolve_deck(repo, "tools/demo") == "tools/demo"

    def test_alias_symlink_ok(self, repo):
        assert export_server.resolve_deck(repo, "demo") == "demo"

    def test_missing_deck(self, repo):
        assert export_server.resolve_deck(repo, "tools/nope") is None

    def test_traversal_rejected(self, repo):
        assert export_server.resolve_deck(repo, "../../etc/passwd") is None
        assert export_server.resolve_deck(repo, "tools/../../x") is None

    def test_absolute_rejected(self, repo):
        assert export_server.resolve_deck(repo, "/etc/passwd") is None

    def test_escaping_symlink_rejected(self, repo, tmp_path_factory):
        outside = tmp_path_factory.mktemp("outside")
        (outside / "slides.md").write_text("# evil\n")
        os.symlink(outside, repo / "decks/evil")
        assert export_server.resolve_deck(repo, "evil") is None


class TestIsStale:
    def test_missing_output_is_stale(self, repo):
        assert export_server.is_stale(repo, "tools/demo", "pptx") is True

    def test_fresh_output_not_stale(self, repo):
        out = repo / "exports/tools/demo.editable.pptx"
        out.parent.mkdir(parents=True)
        out.write_bytes(b"pk")
        future = time.time() + 60
        os.utime(out, (future, future))
        assert export_server.is_stale(repo, "tools/demo", "pptx") is False

    def test_newer_slides_make_it_stale(self, repo):
        out = repo / "exports/tools/demo.editable.pptx"
        out.parent.mkdir(parents=True)
        out.write_bytes(b"pk")
        past = time.time() - 3600
        os.utime(out, (past, past))
        assert export_server.is_stale(repo, "tools/demo", "pptx") is True

    def test_html_output_checked_per_format(self, repo):
        out = repo / "exports/tools/demo.html"
        out.parent.mkdir(parents=True)
        out.write_bytes(b"<html>")
        future = time.time() + 60
        os.utime(out, (future, future))
        assert export_server.is_stale(repo, "tools/demo", "html") is False
        assert export_server.is_stale(repo, "tools/demo", "pptx") is True

    @pytest.mark.parametrize("script", ["comments.js", "client-common.js"])
    def test_comment_client_change_invalidates_only_html(self, repo, script):
        output_time = time.time() + 60
        for suffix in (".html", ".editable.pptx"):
            out = repo / f"exports/tools/demo{suffix}"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"export")
            os.utime(out, (output_time, output_time))
        client = repo / "scripts" / script
        client.write_text("// client\n")
        assert export_server.is_stale(repo, "tools/demo", "html") is False
        os.utime(client, (output_time + 60, output_time + 60))
        assert export_server.is_stale(repo, "tools/demo", "html") is True
        assert export_server.is_stale(repo, "tools/demo", "pptx") is False


class TestParsePath:
    def test_pptx_route(self):
        assert export_server.parse_path("/pptx/tools/demo") == ("pptx", "tools/demo")

    def test_html_route(self):
        assert export_server.parse_path("/html/tools/demo") == ("html", "tools/demo")

    def test_strips_query_and_unquotes(self):
        assert export_server.parse_path("/pptx/tools/demo?x=1") == ("pptx", "tools/demo")
        assert export_server.parse_path("/pptx/tools/my%20deck") == ("pptx", "tools/my deck")

    def test_other_routes_none(self):
        assert export_server.parse_path("/") is None
        assert export_server.parse_path("/png/tools/demo") is None
        assert export_server.parse_path("/pptx/") is None
        assert export_server.parse_path("/html/") is None


class TestParseRawPath:
    def test_raw_route(self):
        assert export_server.parse_raw_path("/raw/tools/demo") == "tools/demo"

    def test_strips_query_and_unquotes(self):
        assert export_server.parse_raw_path("/raw/tools/my%20deck?x=1") == "tools/my deck"

    def test_other_routes_none(self):
        assert export_server.parse_raw_path("/pptx/tools/demo") is None
        assert export_server.parse_raw_path("/raw/") is None
        assert export_server.parse_raw_path("/") is None


class TestRawTarget:
    def test_plain_deck_targets_slides_md(self, repo):
        assert export_server.raw_target(repo, "tools/demo").name == "slides.md"

    def test_tpl_deck_targets_tpl(self, repo):
        (repo / "decks/tools/demo/slides.tpl.md").write_text("# tpl\n")
        assert export_server.raw_target(repo, "tools/demo").name == "slides.tpl.md"

    def test_invalid_deck_none(self, repo):
        assert export_server.raw_target(repo, "tools/nope") is None
        assert export_server.raw_target(repo, "../../etc/passwd") is None

    def test_escaping_tpl_symlink_rejected(self, repo, tmp_path_factory):
        outside = tmp_path_factory.mktemp("outside")
        (outside / "evil.md").write_text("# evil\n")
        os.symlink(outside / "evil.md", repo / "decks/tools/demo/slides.tpl.md")
        assert export_server.raw_target(repo, "tools/demo") is None
        assert export_server.read_raw(repo, "tools/demo") is None
        assert export_server.write_raw(repo, "tools/demo", b"x\n", "1")[0] == 404


class TestReadRaw:
    def test_reads_content_and_etag(self, repo):
        data, etag, is_tpl = export_server.read_raw(repo, "tools/demo")
        assert data == b"# hi\n"
        slides = repo / "decks/tools/demo/slides.md"
        assert etag == str(slides.stat().st_mtime_ns)
        assert is_tpl is False

    def test_tpl_deck_reads_tpl_content(self, repo):
        (repo / "decks/tools/demo/slides.tpl.md").write_text("# tpl\n")
        data, etag, is_tpl = export_server.read_raw(repo, "tools/demo")
        assert data == b"# tpl\n"
        assert is_tpl is True

    def test_invalid_deck_none(self, repo):
        assert export_server.read_raw(repo, "tools/nope") is None


class TestWriteRaw:
    def _etag(self, repo, name="slides.md"):
        return str((repo / "decks/tools/demo" / name).stat().st_mtime_ns)

    def test_write_roundtrip(self, repo):
        status, new_etag = export_server.write_raw(
            repo, "tools/demo", b"# edited\n", self._etag(repo))
        assert status == 200
        assert (repo / "decks/tools/demo/slides.md").read_bytes() == b"# edited\n"
        assert new_etag == self._etag(repo)

    def test_tpl_deck_writes_tpl_not_slides(self, repo):
        (repo / "decks/tools/demo/slides.tpl.md").write_text("# tpl\n")
        status, _ = export_server.write_raw(
            repo, "tools/demo", b"# tpl edited\n", self._etag(repo, "slides.tpl.md"))
        assert status == 200
        assert (repo / "decks/tools/demo/slides.tpl.md").read_bytes() == b"# tpl edited\n"
        assert (repo / "decks/tools/demo/slides.md").read_bytes() == b"# hi\n"  # untouched

    def test_stale_etag_412(self, repo):
        status, msg = export_server.write_raw(repo, "tools/demo", b"x\n", "12345")
        assert status == 412
        assert (repo / "decks/tools/demo/slides.md").read_bytes() == b"# hi\n"

    def test_missing_etag_428(self, repo):
        assert export_server.write_raw(repo, "tools/demo", b"x\n", None)[0] == 428
        assert export_server.write_raw(repo, "tools/demo", b"x\n", "")[0] == 428

    def test_invalid_deck_404(self, repo):
        assert export_server.write_raw(repo, "tools/nope", b"x\n", "1")[0] == 404
        assert export_server.write_raw(repo, "../../x", b"x\n", "1")[0] == 404

class TestTokenLogin:
    @pytest.fixture(autouse=True)
    def _token(self, monkeypatch):
        monkeypatch.setattr(export_server, "TOKEN", "s3cret")

    def test_header_or_cookie(self):
        assert export_server.authorized({"X-Deck-Token": "s3cret"})
        assert export_server.authorized({"Cookie": "other=1; deck_token_8093=s3cret"})

    def test_missing_wrong_or_malformed(self):
        assert not export_server.authorized({})
        assert not export_server.authorized({"X-Deck-Token": "nope"})
        assert not export_server.authorized({"Cookie": "deck_token_8093=nope"})
        assert not export_server.authorized({"Cookie": "foo=s3cret"})
        assert not export_server.authorized({"Cookie": '"\\x'})

    def test_other_apps_odd_cookie_does_not_break_login(self):
        assert export_server.authorized({"Cookie": 'foo[bar]=1; j={"a": 1}; deck_token_8093=s3cret'})

    def test_off_means_open(self, monkeypatch):
        monkeypatch.setattr(export_server, "TOKEN", None)
        assert export_server.authorized({})

    def test_token_file_private_and_stable(self, tmp_path):
        f = tmp_path / ".quarto/server-token"
        t = export_server.load_token(f)
        assert len(t) >= 32 and (f.stat().st_mode & 0o777) == 0o600
        assert export_server.load_token(f) == t

    def test_token_file_mode_tightened_and_owner_checked(self, tmp_path):
        f = tmp_path / "server-token"
        f.write_text("x" * 32 + "\n"); f.chmod(0o644)
        assert export_server.load_token(f) == "x" * 32 and (f.stat().st_mode & 0o777) == 0o600

    def test_empty_token_file_refused(self, tmp_path):
        f = tmp_path / "server-token"; f.write_text("")
        with pytest.raises(SystemExit):
            export_server.load_token(f)

    def test_auth_switch(self, monkeypatch):
        monkeypatch.delenv("SLIDES_AUTH", raising=False)
        assert export_server.auth_enabled()
        monkeypatch.setenv("SLIDES_AUTH", " OFF ")
        assert not export_server.auth_enabled()
        monkeypatch.setenv("SLIDES_AUTH", "false")  # only "off" turns it off, as in the scripts
        assert export_server.auth_enabled()


class TestBuildDeck:
    def test_build_regenerates_slides(self, repo):
        d = repo / "decks/tools/demo"
        (d / "slides.tpl.md").write_text("# tpl\n")
        (d / "build_deck.py").write_text(
            "from pathlib import Path\n"
            "h = Path(__file__).parent\n"
            "(h / 'slides.md').write_text("
            "(h / 'slides.tpl.md').read_text().replace('tpl', 'built'))\n")
        proc = export_server._build_deck(repo, "tools/demo")
        assert proc.returncode == 0
        assert (d / "slides.md").read_text() == "# built\n"

    def test_build_failure_reported(self, repo):
        d = repo / "decks/tools/demo"
        (d / "slides.tpl.md").write_text("# tpl\n")
        (d / "build_deck.py").write_text("raise SystemExit('boom')\n")
        proc = export_server._build_deck(repo, "tools/demo")
        assert proc.returncode != 0


class TestComments:
    def test_missing_file_reads_empty(self, repo):
        assert export_server.read_comments(repo, "tools/demo") == {"comments": []}

    def test_invalid_deck_none(self, repo):
        assert export_server.read_comments(repo, "tools/nope") is None

    def test_add_and_resolve_roundtrip(self, repo):
        status, doc = export_server.add_comment(
            repo, "tools/demo", {"page": 2, "quote": "hi", "comment": "fix this"})
        assert status == 200
        c = doc["comments"][0]
        assert c["page"] == 2 and c["status"] == "open" and c["id"].startswith("c-")
        on_disk = json.loads((repo / "decks/tools/demo/comments.json").read_text())
        assert on_disk == doc
        status, doc2 = export_server.resolve_comment(repo, "tools/demo", c["id"])
        assert status == 200
        assert doc2["comments"][0]["status"] == "resolved"
        on_disk = json.loads((repo / "decks/tools/demo/comments.json").read_text())
        assert on_disk["comments"][0]["status"] == "resolved"

    def test_add_validates_fields(self, repo):
        bad = [
            {"page": 0, "quote": "q", "comment": "c"},
            {"page": "1", "quote": "q", "comment": "c"},
            {"page": 1, "quote": "  ", "comment": "c"},
            {"page": 1, "quote": "q", "comment": ""},
            {},
        ]
        for fields in bad:
            assert export_server.add_comment(repo, "tools/demo", fields)[0] == 400
        assert not (repo / "decks/tools/demo/comments.json").exists()

    def test_add_invalid_deck_404(self, repo):
        assert export_server.add_comment(
            repo, "../../x", {"page": 1, "quote": "q", "comment": "c"})[0] == 404

    def test_resolve_unknown_id_404(self, repo):
        assert export_server.resolve_comment(repo, "tools/demo", "c-x")[0] == 404

    def test_corrupt_file_reads_empty(self, repo):
        (repo / "decks/tools/demo/comments.json").write_text("{nope")
        assert export_server.read_comments(repo, "tools/demo") == {"comments": []}

    def test_parse_comments_path(self):
        assert export_server.parse_comments_path("/comments/tools/demo") == "tools/demo"
        assert export_server.parse_comments_path("/comments/") is None
        assert export_server.parse_comments_path("/raw/tools/demo") is None

    def test_optional_anchor_fields(self, repo):
        status, doc = export_server.add_comment(repo, "tools/demo", {
            "page": 1, "quote": "word", "comment": "second one",
            "occurrence": 1, "prefix": "before ", "suffix": " after"})
        assert status == 200
        c = doc["comments"][-1]
        assert c["occurrence"] == 1 and c["prefix"] == "before " and c["suffix"] == " after"

    def test_bad_anchor_fields_dropped(self, repo):
        status, doc = export_server.add_comment(repo, "tools/demo", {
            "page": 1, "quote": "word", "comment": "c",
            "occurrence": -1, "prefix": 7, "suffix": ""})
        assert status == 200
        c = doc["comments"][-1]
        assert "occurrence" not in c and "prefix" not in c and "suffix" not in c

    def test_bool_occurrence_dropped(self, repo):
        status, doc = export_server.add_comment(repo, "tools/demo", {
            "page": 1, "quote": "word", "comment": "c", "occurrence": True})
        assert status == 200
        assert "occurrence" not in doc["comments"][-1]

    def test_edit_preserves_creation_target_and_snapshot(self, repo):
        _, doc = export_server.add_comment(repo, "tools/demo", {
            "page": 1, "quote": "hi", "comment": "original", "author": "Alex",
            "anchor": {"kind": "tooltip", "slide_id": "intro", "heading": "Hi",
                       "tooltip_text": "Tooltip hi", "tooltip_trigger": "Details"},
            "client_created": "2026-10-02T10:04:05.123Z"})
        original = doc["comments"][0]
        status, doc = export_server.update_comment(
            repo, "tools/demo", original["id"], "edit", "  corrected  ",
            author="Reviewer", expected_updated=original["created"])
        assert status == 200
        edited = doc["comments"][0]
        assert edited["comment"] == "corrected"
        for key in ("id", "page", "quote", "created", "author", "slide_src", "anchor",
                    "client_created"):
            assert edited[key] == original[key]
        assert edited["updated"] != edited["created"]
        assert datetime.fromisoformat(edited["updated"]).tzinfo is not None
        assert edited["history"] == [
            {"action": "created", "at": original["created"], "comment": "original",
             "status": "open", "author": "Alex"},
            {"action": "edited", "at": edited["updated"], "comment": "corrected",
             "status": "open", "author": "Reviewer"},
        ]
        assert export_server.read_comments(repo, "tools/demo") == doc

    def test_resolve_reopen_records_events_and_repeated_action_is_noop(self, repo):
        _, doc = export_server.add_comment(repo, "tools/demo", {
            "page": 1, "quote": "hi", "comment": "fix"})
        cid = doc["comments"][0]["id"]
        _, resolved = export_server.resolve_comment(repo, "tools/demo", cid)
        repeated = export_server.resolve_comment(repo, "tools/demo", cid)
        assert repeated == (200, resolved)
        status, reopened = export_server.update_comment(repo, "tools/demo", cid, "reopen")
        assert status == 200
        c = reopened["comments"][0]
        assert c["status"] == "open"
        assert [e["action"] for e in c["history"]] == ["created", "resolved", "reopened"]
        assert [e["status"] for e in c["history"]] == ["open", "resolved", "open"]
        assert all(datetime.fromisoformat(e["at"]).tzinfo for e in c["history"])

    @pytest.mark.parametrize("status", ["open", "resolved"])
    def test_edit_legacy_preserves_unknown_fields_and_does_not_invent_times(self, repo, status):
        original = {"id": "old", "created": "2026-01-02T03:04:05-08:00",
                    "page": 1, "quote": "hi", "comment": "old comment", "status": status,
                    "commit": "abc123", "custom": {"retain": True}}
        f = repo / "decks/tools/demo/comments.json"
        f.write_text(json.dumps({"comments": [original], "custom_doc": 42}))
        code, doc = export_server.update_comment(
            repo, "tools/demo", "old", "edit", "new comment",
            expected_updated=original["created"])
        assert code == 200 and doc["custom_doc"] == 42
        c = doc["comments"][0]
        assert c["created"] == original["created"]
        assert c["custom"] == original["custom"] and c["commit"] == "abc123"
        assert c["status"] == status
        assert c["history"][0] == {
            "action": "created", "at": original["created"],
            "comment": "old comment", "status": "open"}
        if status == "resolved":
            assert c["history"][1]["action"] == "resolved"
            assert c["history"][1]["at"] is None
        assert c["history"][-1]["comment"] == "new comment"

    def test_legacy_without_creation_time_stays_unknown(self, repo):
        f = repo / "decks/tools/demo/comments.json"
        f.write_text(json.dumps({"comments": [
            {"id": "old", "page": 1, "quote": "hi", "comment": "fix"}]}))
        code, doc = export_server.update_comment(repo, "tools/demo", "old", "edit", "fixed")
        assert code == 200
        assert "created" not in doc["comments"][0]
        assert doc["comments"][0]["history"][0]["at"] is None

    @pytest.mark.parametrize("action", ["edit", "resolve", "reopen"])
    def test_stale_update_is_rejected_without_changing_file(self, repo, action):
        _, doc = export_server.add_comment(repo, "tools/demo", {
            "page": 1, "quote": "hi", "comment": "initial"})
        c = doc["comments"][0]
        export_server.update_comment(repo, "tools/demo", c["id"], "edit", "already edited")
        f = repo / "decks/tools/demo/comments.json"
        before = f.read_bytes()
        code, _ = export_server.update_comment(
            repo, "tools/demo", c["id"], action, "stale edit",
            expected_updated=c["created"])
        assert code == 409
        assert f.read_bytes() == before

    @pytest.mark.parametrize("comment", [None, "", "  ", {}, 42])
    def test_edit_rejects_invalid_text_without_changing_file(self, repo, comment):
        _, doc = export_server.add_comment(repo, "tools/demo", {
            "page": 1, "quote": "hi", "comment": "initial"})
        code, _ = export_server.update_comment(
            repo, "tools/demo", doc["comments"][0]["id"], "edit", comment)
        assert code == 400
        assert export_server.read_comments(repo, "tools/demo") == doc

    def test_creation_has_timestamps_and_optional_target_metadata(self, repo):
        anchor = {"kind": "tooltip", "slide_id": "stable", "heading": "Intro",
                  "tooltip_text": "More detail", "tooltip_trigger": "Details"}
        status, doc = export_server.add_comment(repo, "tools/demo", {
            "page": 1, "quote": "hi", "comment": "fix", "anchor": anchor,
            "client_created": "2026-10-02T10:04:05.123Z"})
        c = doc["comments"][0]
        assert status == 200 and c["anchor"] == anchor
        assert c["client_created"] == "2026-10-02T10:04:05.123Z"
        assert c["updated"] == c["created"] == c["history"][0]["at"]
        assert datetime.fromisoformat(c["created"]).tzinfo is not None

    def test_malformed_optional_metadata_dropped(self, repo):
        _, doc = export_server.add_comment(repo, "tools/demo", {
            "page": 1, "quote": "hi", "comment": "fix", "anchor": "bad",
            "client_created": "yesterday"})
        assert "anchor" not in doc["comments"][0]
        assert "client_created" not in doc["comments"][0]
        _, doc = export_server.add_comment(repo, "tools/demo", {
            "page": 1, "quote": "hi", "comment": "fix",
            "anchor": {"kind": "slide", "heading": 42, "slide_id": "x" * 1000},
            "client_created": "2026-10-02T10:04:05"})
        assert doc["comments"][-1]["anchor"] == {"kind": "slide", "slide_id": "x" * 200}
        assert "client_created" not in doc["comments"][-1]


class TestCommentPost:
    def post(self, repo, monkeypatch, request):
        monkeypatch.setattr(export_server, "REPO", repo)
        body = json.dumps(request).encode()
        handler = object.__new__(export_server.ExportHandler)
        handler.path = "/comments/tools/demo"
        handler.headers = {"Content-Length": str(len(body)), "Host": "localhost:8094"}
        handler.rfile = io.BytesIO(body)
        responses = []
        handler._respond = lambda status, data, mime: responses.append((status, data))
        handler.do_POST()
        return responses[0]

    def test_edit_resolve_reopen_routes_and_conflict(self, repo, monkeypatch):
        status, body = self.post(repo, monkeypatch, {"action": "add", "comment": {
            "page": 1, "quote": "hi", "comment": "original"}})
        assert status == 200
        original = json.loads(body)["comments"][0]
        status, body = self.post(repo, monkeypatch, {
            "action": "edit", "id": original["id"], "comment": "edited",
            "expected_updated": original["created"], "author": "Alex"})
        assert status == 200 and json.loads(body)["comments"][0]["comment"] == "edited"
        status, _ = self.post(repo, monkeypatch, {
            "action": "resolve", "id": original["id"], "expected_updated": original["created"]})
        assert status == 409
        for action, wanted in [("resolve", "resolved"), ("reopen", "open")]:
            status, body = self.post(repo, monkeypatch, {"action": action, "id": original["id"]})
            assert status == 200 and json.loads(body)["comments"][0]["status"] == wanted

    @pytest.mark.parametrize("payload", [[], None, "bad", {"action": "add", "comment": "bad"}])
    def test_malformed_json_shape_is_bad_request(self, repo, monkeypatch, payload):
        status, _ = self.post(repo, monkeypatch, payload)
        assert status == 400


class TestSplitSlides:
    DECK = ("---\nmarp: true\ntheme: agentic\n---\n"
            "# Slide one\n\n---\n\n"
            "## Slide two\n```bash\n--- not a separator\n```\n\n---\n\n"
            "### Slide three\n~~~\n---\n~~~\nlast line")

    def test_three_slides_fences_respected(self):
        slides = export_server.split_slides(self.DECK)
        assert len(slides) == 3
        assert slides[0] == "# Slide one\n"
        assert "--- not a separator" in slides[1]
        assert slides[2].endswith("last line")

    def test_no_front_matter_single_slide(self):
        assert export_server.split_slides("# only") == ["# only"]

    def test_trailing_whitespace_delimiters(self):
        slides = export_server.split_slides("---  \nmarp: true\n---\n\n# A\n\n---   \n\n# B\n")
        assert len(slides) == 2


class TestSourceContext:
    def test_slide_src_without_git(self, repo):
        (repo / "decks/tools/demo/slides.md").write_text(
            "---\nmarp: true\n---\n\n# One\n\n---\n\n# Two here\n")
        ctx = export_server._source_context(repo, "tools/demo", 2)
        assert ctx["source_file"] == "slides.md"
        assert ctx["slide_src"].strip() == "# Two here"
        assert "commit" not in ctx  # tmp dir is not a git repo

    def test_page_clamped(self, repo):
        ctx = export_server._source_context(repo, "tools/demo", 99)
        assert "slide_src" in ctx

    def test_full_context_in_git_repo(self, repo):
        import subprocess
        def git(*args):
            subprocess.run(["git", *args], cwd=repo, capture_output=True, check=True)
        git("init", "-q")
        git("-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
        git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "x")
        ctx = export_server._source_context(repo, "tools/demo", 1)
        assert ctx.get("commit") and ctx["dirty"] is False
        (repo / "decks/tools/demo/slides.md").write_text("# changed\n")
        ctx = export_server._source_context(repo, "tools/demo", 1)
        assert ctx["dirty"] is True

    def test_add_comment_captures_context(self, repo):
        status, doc = export_server.add_comment(
            repo, "tools/demo", {"page": 1, "quote": "hi", "comment": "c"})
        assert status == 200
        c = doc["comments"][-1]
        assert c["source_file"] == "slides.md" and "slide_src" in c

    def test_author_field(self, repo):
        status, doc = export_server.add_comment(repo, "tools/demo", {
            "page": 1, "quote": "q", "comment": "c", "author": "  Alex  "})
        assert status == 200 and doc["comments"][-1]["author"] == "Alex"
        status, doc = export_server.add_comment(repo, "tools/demo", {
            "page": 1, "quote": "q", "comment": "c", "author": 42})
        assert status == 200 and "author" not in doc["comments"][-1]


class TestOriginAllowed:
    allowed = staticmethod(export_server.origin_allowed)

    def test_no_origin_is_non_browser_client(self):
        assert self.allowed(None, "localhost:8094", "/raw/tools/demo")

    def test_deck_page_on_same_host_other_port(self):
        assert self.allowed("http://localhost:8093", "localhost:8094", "/raw/tools/demo")
        assert self.allowed("http://box.example:8093", "box.example:8094", "/comments/tools/demo")

    def test_other_site_rejected(self):
        assert not self.allowed("https://evil.example", "localhost:8094", "/raw/tools/demo")
        assert not self.allowed("https://evil.example", "localhost:8094", "/comments/tools/demo")
        assert not self.allowed("http://127.0.0.1:8093", "localhost:8094", "/comments/tools/demo")

    def test_pinned_to_own_ports_and_http(self, monkeypatch):
        monkeypatch.setattr(export_server, "ORIGIN_PORTS", {8093, 8094})
        assert self.allowed("http://localhost:8093", "localhost:8094", "/raw/tools/demo")
        assert not self.allowed("http://localhost:9000", "localhost:8094", "/raw/tools/demo")
        assert not self.allowed("https://localhost:8093", "localhost:8094", "/raw/tools/demo")
        assert not self.allowed("http://localhost", "localhost:8094", "/raw/tools/demo")

    def test_file_origin_only_for_comments(self):
        assert self.allowed("null", "localhost:8094", "/comments/tools/demo")
        assert not self.allowed("null", "localhost:8094", "/raw/tools/demo")
        assert not self.allowed("null", "localhost:8094", "/pptx/tools/demo")


class TestHostAllowed:
    allowed = staticmethod(export_server.host_allowed)

    def test_loopback_bind_accepts_loopback_names(self):
        for h in ("localhost:8094", "127.0.0.1:8094", "[::1]:8094"):
            assert self.allowed(h, "127.0.0.1")

    def test_loopback_bind_rejects_rebound_name(self):
        assert not self.allowed("evil.example:8094", "127.0.0.1")
        assert not self.allowed(None, "127.0.0.1")

    def test_open_bind_accepts_any_host(self):
        assert self.allowed("box.example:8094", "0.0.0.0")
# ── Quarto decks (slides.qmd) next to Marp-sourced ones (slides.md) ─────────

@pytest.fixture()
def qrepo(repo):
    d = repo / "decks/templates/demo"
    d.mkdir(parents=True)
    (d / "slides.qmd").write_text("---\ncss: []\n---\n\n## One\n\n---\n\n## Two\n")
    t = repo / "decks/templates/tpl"
    t.mkdir(parents=True)
    (t / "slides.qmd").write_text("built\n")
    (t / "slides.tpl.qmd").write_text("source\n")
    return repo


class TestQuartoDecks:
    def test_layout(self, qrepo):
        root, d, built, tpl = export_server.deck_layout(qrepo, "templates/demo")
        assert (root, d, built, tpl) == (qrepo / "decks", qrepo / "decks/templates/demo",
                                         "slides.qmd", "slides.tpl.qmd")
        # a Marp-sourced deck keeps slides.md as its source
        assert export_server.deck_layout(qrepo, "tools/demo")[2:] == ("slides.md", "slides.tpl.md")

    def test_resolve(self, qrepo):
        assert export_server.resolve_deck(qrepo, "templates/demo") == "templates/demo"
        assert export_server.resolve_deck(qrepo, "templates/nope") is None
        assert export_server.resolve_deck(qrepo, "templates/../../x") is None

    def test_escaping_symlink_rejected(self, qrepo, tmp_path_factory):
        outside = tmp_path_factory.mktemp("outside")
        (outside / "slides.qmd").write_text("# evil\n")
        os.symlink(outside, qrepo / "decks/evil")
        assert export_server.resolve_deck(qrepo, "evil") is None

    def test_raw_targets(self, qrepo):
        assert export_server.raw_target(qrepo, "templates/demo").name == "slides.qmd"
        assert export_server.raw_target(qrepo, "templates/tpl").name == "slides.tpl.qmd"
        data, etag, is_tpl = export_server.read_raw(qrepo, "templates/tpl")
        assert data == b"source\n" and is_tpl is True
        assert export_server.read_raw(qrepo, "templates/demo")[2] is False

    def test_write_raw(self, qrepo):
        _, etag, _ = export_server.read_raw(qrepo, "templates/demo")
        status, _ = export_server.write_raw(qrepo, "templates/demo", b"new\n", etag)
        assert status == 200
        assert (qrepo / "decks/templates/demo/slides.qmd").read_text() == "new\n"

    def test_comments_live_in_deck_dir(self, qrepo):
        status, _ = export_server.add_comment(
            qrepo, "templates/demo", {"page": 2, "quote": "Two", "comment": "ok"})
        assert status == 200
        f = qrepo / "decks/templates/demo/comments.json"
        c = json.loads(f.read_text())["comments"][0]
        assert c["source_file"] == "slides.qmd" and c["slide_src"].strip() == "## Two"

    def test_stale_and_export_command(self, qrepo, monkeypatch):
        assert export_server.is_stale(qrepo, "templates/demo", "html") is True
        seen = {}
        monkeypatch.setattr(export_server.subprocess, "run",
                            lambda cmd, **kw: seen.setdefault("cmd", cmd))
        export_server._export(qrepo, "templates/demo", "pptx")
        assert seen["cmd"] == ["bash", "scripts/export.sh", "templates/demo", "pptx-edit"]

    def test_pdf_route(self):
        assert export_server.parse_path("/pdf/templates/demo") == ("pdf", "templates/demo")

    def test_parse_preview_path(self):
        assert export_server.parse_preview_path("/preview/a/b") == "a/b"
        assert export_server.parse_preview_path("/raw/a/b") is None

    def test_preview_unknown_deck(self, qrepo):
        assert export_server.render_preview(qrepo, "tools/nope", "# x", 1)[0] == 404

    def test_preview_converts_marp_source(self, qrepo, monkeypatch):
        seen = {}

        class Done:
            returncode, stdout, stderr = 0, "<p>ok</p>", ""

        def fake_run(cmd, input=None, **kw):
            seen["input"] = input
            return Done()
        monkeypatch.setattr(export_server.subprocess, "run", fake_run)
        status, html = export_server.render_preview(
            qrepo, "tools/demo", "# a\n\n---\n\n![w:300](x.png)\n", 2)
        assert status == 200 and html == "<p>ok</p>"
        assert "![](x.png){width=300}" in seen["input"]


REAL_REPO = export_server.REPO


@pytest.mark.skipif(not (REAL_REPO / "quarto/.dist").is_dir(), reason="quarto not set up")
def test_preview_renders_one_slide_with_the_project_reader():
    md = ("---\ncss: []\n---\n\n## First\n\n---\n\n<!-- _class: lead -->\n\n## Second *em*\n\n"
          "<svg viewBox=\"0 0 10 10\">\n<text>a_b *raw*</text>\n</svg>\n\n$x^2$\n")
    status, html = export_server.render_preview(REAL_REPO, "templates/visual-gallery", md, 2)
    assert status == 200
    assert "Second <em>em</em>" in html and "First" not in html
    assert "<text>a_b *raw*</text>" in html          # an HTML block stays raw (CommonMark, as in Marp)
    assert "\\(x^2\\)" in html                        # math left for MathJax
