import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ingest  # noqa: E402
from tests.make_fixtures import make_workdir  # noqa: E402


def test_v2_shape_and_sources(tmp_path):
    review = ingest.build_review(make_workdir(), slug="fx", out_dir=tmp_path)
    ids = [s["id"] for s in review["sources"]]
    assert ids == ["s0", "s1"]
    assert {s["id"]: s["doc_type"] for s in review["sources"]} == {"s0": "pdf", "s1": "html"}
    assert review["tally"] == {"supported": 2, "not_found": 1}


def test_claims_resolve_against_their_source(tmp_path):
    review = ingest.build_review(make_workdir(), slug="fx", out_dir=tmp_path)
    beta, phrase, gamma = review["claims"]
    assert beta["source"] == "s0" and beta["jump"]["page"] == 2
    assert beta["wiki_quote"] == "Beta on the second slide"
    assert phrase["source"] == "s1" and phrase["jump"] == {"anchor": "x-anno-1"}
    assert gamma["jump"] is None
    assert (tmp_path / "fx" / "annotated.s0.pdf").is_file()
    assert (tmp_path / "fx" / "annotated.s1.html").is_file()
    assert 'id="x-anno-1"' in (tmp_path / "fx" / "annotated.s1.html").read_text()


def test_missing_wiki_quote_is_rejected(tmp_path):
    import json, pytest
    wd = make_workdir()
    anns = json.loads((wd / "annotations.json").read_text())
    del anns["annotations"][0]["wiki_quote"]
    (wd / "annotations.json").write_text(json.dumps(anns))
    with pytest.raises(SystemExit):
        ingest.build_review(wd, slug="fx2", out_dir=tmp_path)
