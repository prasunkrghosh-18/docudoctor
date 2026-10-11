"""Unit tests for AST scanner and issue detection."""

from pathlib import Path
from docudoctor.models import IssueType, Severity
from docudoctor.scanner import scan_file


def test_scanner_detects_undocumented_functions(tmp_path: Path):
    test_file = tmp_path / "sample.py"
    test_file.write_text(
        """def add(a: int, b: int) -> int:
    return a + b
""",
        encoding="utf-8",
    )

    report, funcs = scan_file(test_file)
    assert report.total_functions == 1
    assert report.documented_functions == 0
    assert any(i.issue_type == IssueType.MISSING_DOCSTRING for i in report.issues)


def test_scanner_detects_mutable_defaults(tmp_path: Path):
    test_file = tmp_path / "sample.py"
    test_file.write_text(
        """def append_item(val: int, items=[]):
    items.append(val)
    return items
""",
        encoding="utf-8",
    )

    report, _ = scan_file(test_file)
    assert any(i.issue_type == IssueType.MUTABLE_DEFAULT_ARG for i in report.issues)


def test_scanner_handles_clean_code(tmp_path: Path):
    test_file = tmp_path / "sample.py"
    test_file.write_text(
        '''def multiply(a: int, b: int) -> int:
    """Multiply two integers.

    Args:
        a: First number.
        b: Second number.

    Returns:
        The product.
    """
    return a * b
''',
        encoding="utf-8",
    )

    report, _ = scan_file(test_file)
    assert report.documented_functions == 1
    assert report.typed_returns == 1
    assert len(report.issues) == 0
    assert report.score == 100.0
