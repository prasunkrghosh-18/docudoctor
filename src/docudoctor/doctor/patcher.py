"""Safe code patching and injection engine for inserting docstrings."""

from pathlib import Path
from typing import List, Tuple

from docudoctor.doctor.generator import DocstringStyle, generate_docstring
from docudoctor.models import FunctionMeta


def _find_header_end_line(lines: List[str], start_line_idx: int) -> int:
    """Find the line index where the function signature ends with ':'."""
    for idx in range(start_line_idx, len(lines)):
        stripped = lines[idx].split("#")[0].rstrip()
        if stripped.endswith(":"):
            return idx
    return start_line_idx


def _detect_body_indent(lines: List[str], header_end_idx: int, default_indent: str = "    ") -> str:
    """Detect the indentation level used inside the function body."""
    # Check the lines right after the header
    for idx in range(header_end_idx + 1, min(len(lines), header_end_idx + 5)):
        line = lines[idx]
        if line.strip() and not line.strip().startswith("#"):
            indent_len = len(line) - len(line.lstrip())
            return " " * indent_len

    # If empty function (e.g., pass), indent 4 spaces beyond def
    def_line = lines[header_end_idx]
    base_indent = len(def_line) - len(def_line.lstrip())
    return " " * (base_indent + 4)


def patch_file_docstrings(
    file_path: Path,
    functions: List[FunctionMeta],
    style: DocstringStyle = DocstringStyle.GOOGLE,
    use_ai: bool = False,
    ai_model: str = "llama3:latest",
) -> Tuple[str, str, int]:
    """
    Safely patch missing docstrings into a Python file.
    Returns: (original_content, patched_content, count_patched)
    """
    original_content = file_path.read_text(encoding="utf-8")
    lines = original_content.splitlines()

    # Filter functions that actually lack docstrings
    candidates = [f for f in functions if not f.docstring or not f.docstring.strip()]
    if not candidates:
        return original_content, original_content, 0

    # Sort descending by start line so modifying lower lines doesn't shift higher lines
    candidates.sort(key=lambda f: f.line_start, reverse=True)

    patched_count = 0
    for func in candidates:
        def_start_idx = func.line_start - 1
        if def_start_idx >= len(lines):
            continue

        header_end_idx = _find_header_end_line(lines, def_start_idx)
        indent = _detect_body_indent(lines, header_end_idx)

        new_doc = generate_docstring(
            func, style=style, use_ai=use_ai, ai_model=ai_model, indent=indent
        )
        doc_lines = new_doc.splitlines()

        # Insert after header_end_idx
        lines = lines[: header_end_idx + 1] + doc_lines + lines[header_end_idx + 1 :]
        patched_count += 1

    patched_content = "\n".join(lines) + ("\n" if original_content.endswith("\n") else "")
    return original_content, patched_content, patched_count
