"""Python language adapter wrapping AST visitor, docstring generator, and patcher."""

import ast
from pathlib import Path
from typing import Optional, Tuple

from docudoctor.doctor.generator import DocstringStyle, generate_docstring
from docudoctor.doctor.patcher import _detect_body_indent, _find_header_end_line
from docudoctor.languages.base import (
    LanguageArg,
    LanguageAuditResult,
    LanguageEntity,
    LanguageIssue,
    compute_health_grade,
)
from docudoctor.scanner import CodeAnalysisVisitor


def _recommendation_for_issue(issue_type: str, entity_name: str) -> str:
    """Provide specific actionable recommendation for each detected defect."""
    if issue_type == "Missing Docstring":
        return f"Add a standard docstring explaining what '{entity_name}' does, its arguments, and returns."
    elif issue_type == "Missing Return Type":
        return f"Add a return type hint to '{entity_name}' (e.g. -> str, -> int, or -> None)."
    elif issue_type == "Missing Arg Type":
        return "Add explicit type annotations for parameters to improve IDE autocomplete and type safety."
    elif issue_type == "Mutable Default Arg":
        return "Use None as default (e.g. arg=None) and initialize the list/dict inside the function body."
    return "Refactor code to adhere to PEP-8 and PEP-257 standards."


def audit_python_code(code: str) -> LanguageAuditResult:
    """Audit Python code string using AST."""
    try:
        tree = ast.parse(code, filename="<input>")
    except Exception as e:
        raise ValueError(f"Syntax Error in Python code: {str(e)}")

    dummy_path = Path("editor.py")
    visitor = CodeAnalysisVisitor(dummy_path, code)
    visitor.visit(tree)

    total_funcs = len(visitor.functions)
    total_classes = len(visitor.classes)
    total_items = total_funcs + total_classes

    doc_funcs = sum(1 for f in visitor.functions if f.docstring and f.docstring.strip())
    doc_classes = sum(1 for c in visitor.classes if c.docstring and c.docstring.strip())
    typed_returns = sum(1 for f in visitor.functions if f.return_type)

    if total_items == 0:
        score = 100.0
    else:
        doc_ratio = (doc_funcs + doc_classes) / total_items
        type_ratio = (typed_returns / total_funcs) if total_funcs > 0 else 1.0
        weighted = (doc_ratio * 65.0) + (type_ratio * 35.0)
        penalties = sum(3.0 for issue in visitor.issues if str(issue.issue_type) == "Mutable Default Arg")
        score = max(0.0, min(100.0, weighted - penalties))

    grade, label, color = compute_health_grade(score)

    issues: list[LanguageIssue] = []
    for i in visitor.issues:
        iss_type_str = i.issue_type.value if hasattr(i.issue_type, "value") else str(i.issue_type)
        sev_str = i.severity.value if hasattr(i.severity, "value") else str(i.severity)
        can_fix = iss_type_str == "Missing Docstring" and i.entity_type in ("function", "method")
        issues.append(
            LanguageIssue(
                line=i.line_no,
                entity=i.entity_name,
                entity_type=i.entity_type,
                issue_type=iss_type_str,
                severity=sev_str,
                message=i.message,
                recommendation=_recommendation_for_issue(iss_type_str, i.entity_name),
                can_fix=can_fix,
            )
        )

    entities: list[LanguageEntity] = []
    for f in visitor.functions:
        args = [LanguageArg(name=a.name, type_name=a.type_annotation, default_val=a.default_repr) for a in f.args]
        entities.append(
            LanguageEntity(
                name=f.name,
                entity_type="method" if f.is_method else "function",
                line_start=f.line_start,
                line_end=f.line_end,
                return_type=f.return_type,
                args=args,
                docstring=f.docstring,
                raw_source=f.raw_source,
                has_mutable_default=f.has_mutable_default,
            )
        )

    for c in visitor.classes:
        entities.append(
            LanguageEntity(
                name=c.name,
                entity_type="class",
                line_start=c.line_start,
                line_end=c.line_end,
                return_type=None,
                args=[],
                docstring=c.docstring,
                raw_source="",
            )
        )

    return LanguageAuditResult(
        score=round(score, 1),
        grade=grade,
        label=label,
        color=color,
        total_functions=total_funcs,
        total_classes=total_classes,
        documented_functions=doc_funcs,
        typed_returns=typed_returns,
        issues=issues,
        entities=entities,
    )


def patch_python_code(
    code: str,
    style: DocstringStyle = DocstringStyle.GOOGLE,
    target_function: Optional[str] = None,
) -> Tuple[str, int]:
    """Patch missing docstrings into Python code."""
    from docudoctor.scanner import scan_file
    import tempfile

    # Save to temp file to reuse scanner
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tmp:
        tmp.write(code)
        tmp_path = Path(tmp.name)

    try:
        _, functions = scan_file(tmp_path)
        candidates = [f for f in functions if not f.docstring or not f.docstring.strip()]

        if target_function:
            candidates = [f for f in candidates if f.name == target_function]

        if not candidates:
            return code, 0

        lines = code.splitlines()
        candidates.sort(key=lambda f: f.line_start, reverse=True)

        patched_count = 0
        for func in candidates:
            def_start_idx = func.line_start - 1
            if def_start_idx >= len(lines):
                continue
            header_end_idx = _find_header_end_line(lines, def_start_idx)
            indent = _detect_body_indent(lines, header_end_idx)

            new_doc = generate_docstring(func, style=style, indent=indent)
            doc_lines = new_doc.splitlines()
            lines = lines[: header_end_idx + 1] + doc_lines + lines[header_end_idx + 1 :]
            patched_count += 1

        patched_code = "\n".join(lines) + ("\n" if code.endswith("\n") else "")
        return patched_code, patched_count
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
