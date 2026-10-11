"""Unit tests for code patcher and docstring injection."""

import ast
from pathlib import Path
from docudoctor.doctor.patcher import patch_file_docstrings
from docudoctor.scanner import scan_file


def test_patcher_inserts_valid_docstring(tmp_path: Path):
    test_file = tmp_path / "calc.py"
    test_file.write_text(
        """def compute(x: float, factor: float = 2.0) -> float:
    return x * factor
""",
        encoding="utf-8",
    )

    _, funcs = scan_file(test_file)
    orig, patched, count = patch_file_docstrings(test_file, funcs)

    assert count == 1
    assert '"""Compute.' in patched
    assert "factor (float)" in patched
    assert "Defaults to 2.0" in patched

    # Verify that the patched code is syntactically valid Python!
    parsed = ast.parse(patched)
    assert parsed is not None
