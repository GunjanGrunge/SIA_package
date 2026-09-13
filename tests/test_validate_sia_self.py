import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

import validate_sia  # noqa: E402  (sia/tests is on sys.path when run from that dir)


def test_assert_contains_raises_on_missing_pattern(tmp_path, monkeypatch):
    monkeypatch.setattr(validate_sia, "SIA_ROOT", tmp_path)
    (tmp_path / "sample.md").write_text("# Title\nbody text\n", encoding="utf-8")
    try:
        validate_sia.assert_contains("sample.md", [r"^# Title$", r"not present here"])
        assert False, "expected AssertionError"
    except AssertionError as exc:
        assert "not present here" in str(exc)


def test_assert_contains_passes_when_all_patterns_found(tmp_path, monkeypatch):
    monkeypatch.setattr(validate_sia, "SIA_ROOT", tmp_path)
    (tmp_path / "sample.md").write_text("# Title\nbody text\n", encoding="utf-8")
    validate_sia.assert_contains("sample.md", [r"^# Title$", r"body text"])


def test_assert_contains_raises_on_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(validate_sia, "SIA_ROOT", tmp_path)
    try:
        validate_sia.assert_contains("missing.md", [r"anything"])
        assert False, "expected AssertionError"
    except AssertionError as exc:
        assert "does not exist" in str(exc)
