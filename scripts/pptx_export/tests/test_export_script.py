import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "export.sh"


def _write_executable(path, text):
    path.write_text(text)
    path.chmod(0o755)


@pytest.mark.skipif(not (REPO / "quarto/.dist").is_dir(), reason="quarto not set up")
def test_pptx_export_extracts_the_in_place_render(tmp_path):
    # the exporter must read the deck rendered next to its source, so the
    # deck-relative assets (images/, slides_files/) resolve
    fake_python = tmp_path / "python"
    _write_executable(fake_python, '#!/usr/bin/env bash\nprintf \'%s\\n\' "$@" > "$FAKE_PYTHON_ARGS"\n')
    args_file = tmp_path / "python-args"
    env = dict(os.environ, PPTX_PYTHON=str(fake_python), FAKE_PYTHON_ARGS=str(args_file))

    # The repo ships no throwaway deck, so stage one in-tree.
    deck = REPO / "decks" / "templates" / "_test-export"
    deck.mkdir(parents=True)
    try:
        (deck / "slides.qmd").write_text(
            "---\npagetitle: test\ncss:\n- ../../../quarto/themes/base.css\n"
            "- ../../../quarto/themes/agentic.css\n---\n\n# Test\n")
        subprocess.run([str(SCRIPT), "templates/_test-export", "pptx"],
                       cwd=REPO, env=env, check=True, capture_output=True, text=True)

        args = args_file.read_text().splitlines()
        assert args[:2] == ["-m", "scripts.pptx_export"]
        assert args[2] == "decks/templates/_test-export/slides.html" and (REPO / args[2]).is_file()
        assert args[3] == "exports/templates/_test-export.editable.pptx"
    finally:
        shutil.rmtree(deck)
        # the render's post-render step listed the throwaway deck: list again
        subprocess.run([sys.executable, str(REPO / "quarto/scripts/gen_index.py")], cwd=REPO)
