"""SVG Vector badge generator for repository documentation health."""

from pathlib import Path
from docudoctor.models import ProjectReport


def _badge_color_for_score(score: float) -> str:
    """Return hex color matching score tier."""
    if score >= 90:
        return "#4c1"       # Bright Green
    elif score >= 75:
        return "#007ec6"   # Clean Blue
    elif score >= 50:
        return "#dfb317"   # Gold / Yellow
    elif score >= 30:
        return "#fe7d37"   # Orange
    else:
        return "#e05d44"   # Red


def generate_svg_badge(score: float, label: str = "doc health") -> str:
    """
    Generate a clean Shields.io-styled SVG badge string.
    e.g. [ doc health | 88% ]
    """
    value = f"{score:.0f}%"
    color = _badge_color_for_score(score)

    # Approximate width based on character count
    label_width = len(label) * 7 + 14
    value_width = len(value) * 8 + 14
    total_width = label_width + value_width

    label_x = label_width / 2.0
    value_x = label_width + (value_width / 2.0)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="20" role="img" aria-label="{label}: {value}">
  <title>{label}: {value}</title>
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r">
    <rect width="{total_width}" height="20" rx="3" fill="#fff"/>
  </clipPath>
  <g clip-path="url(#r)">
    <rect width="{label_width}" height="20" fill="#555"/>
    <rect x="{label_width}" width="{value_width}" height="20" fill="{color}"/>
    <rect width="{total_width}" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" text-rendering="geometricPrecision" font-size="110">
    <text aria-hidden="true" x="{int(label_x * 10)}" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)">{label}</text>
    <text x="{int(label_x * 10)}" y="140" transform="scale(.1)" fill="#fff">{label}</text>
    <text aria-hidden="true" x="{int(value_x * 10)}" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)">{value}</text>
    <text x="{int(value_x * 10)}" y="140" transform="scale(.1)" fill="#fff">{value}</text>
  </g>
</svg>"""


def save_project_badge(report: ProjectReport, output_path: Path) -> Path:
    """Generate and write the SVG badge file to disk."""
    svg_content = generate_svg_badge(report.overall_score)
    output_path.write_text(svg_content, encoding="utf-8")
    return output_path
