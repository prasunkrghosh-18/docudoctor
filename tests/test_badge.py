"""Unit tests for SVG badge generator."""

from pathlib import Path
from docudoctor.badge import generate_svg_badge, save_project_badge
from docudoctor.models import FileReport, ProjectReport


def test_generate_svg_badge_structure():
    svg = generate_svg_badge(95.0)
    assert "<svg" in svg
    assert "</svg>" in svg
    assert "95%" in svg
    assert "#4c1" in svg  # High score green


def test_generate_svg_badge_yellow_and_red():
    svg_mid = generate_svg_badge(62.0)
    assert "62%" in svg_mid
    assert "#dfb317" in svg_mid  # Yellow

    svg_low = generate_svg_badge(20.0)
    assert "20%" in svg_low
    assert "#e05d44" in svg_low  # Red


def test_save_project_badge(tmp_path: Path):
    report = ProjectReport(
        file_reports=[
            FileReport(
                file_path=tmp_path / "mod.py",
                total_functions=2,
                total_classes=0,
                documented_functions=2,
                documented_classes=0,
                typed_returns=2,
                issues=[],
            )
        ]
    )
    badge_file = tmp_path / "test-badge.svg"
    saved = save_project_badge(report, badge_file)

    assert saved.exists()
    content = saved.read_text(encoding="utf-8")
    assert "100%" in content
