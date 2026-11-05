"""C++ language parser, Doxygen documentation auditor, and code patcher."""

import re
from typing import List, Optional, Tuple

from docudoctor.languages.base import (
    LanguageArg,
    LanguageAuditResult,
    LanguageEntity,
    LanguageIssue,
    compute_health_grade,
)
from docudoctor.languages.c_engine import _find_preceding_doc, _split_c_args


def parse_cpp_code(code: str) -> List[LanguageEntity]:
    """Parse C++ classes, methods, and functions along with their doc comments."""
    lines = code.splitlines()
    entities: List[LanguageEntity] = []

    # 1. Match Classes / Structs
    class_pattern = re.compile(
        r"^[ \t]*(?:template\s*<[^>]+>\s*)?(class|struct)\s+([a-zA-Z_][a-zA-Z0-9_]*)"
        r"(?:\s*:\s*(?:public|protected|private)\s+[^{]+)?\s*\{",
        re.MULTILINE,
    )

    for match in class_pattern.finditer(code):
        entity_kind = match.group(1).strip()
        class_name = match.group(2).strip()

        start_char = match.start()
        line_no = code[:start_char].count("\n") + 1
        line_idx = line_no - 1

        raw_line = lines[line_idx] if line_idx < len(lines) else ""
        indent = raw_line[: len(raw_line) - len(raw_line.lstrip())]

        doc, _ = _find_preceding_doc(lines, line_idx)

        entities.append(
            LanguageEntity(
                name=class_name,
                entity_type="class",
                line_start=line_no,
                line_end=line_no,
                return_type=None,
                args=[],
                docstring=doc,
                raw_source=match.group(0),
                indent=indent,
            )
        )

    # 2. Match Functions & Methods
    keywords = {"if", "while", "for", "switch", "catch", "return", "sizeof", "new", "delete"}

    # Pattern looks for: [virtual/static/inline/template] type [Class::]name ( args ) [const] [override] [noexcept] {
    func_pattern = re.compile(
        r"^[ \t]*(?:template\s*<[^>]+>\s*)?"
        r"((?:(?:virtual|static|inline|explicit|constexpr|friend)\s+)*"
        r"[a-zA-Z0-9_:<>,*& \t]+?)\s+"
        r"((?:[a-zA-Z_][a-zA-Z0-9_]*::)?[a-zA-Z_~][a-zA-Z0-9_]*)\s*"
        r"\(([^;{]*?)\)\s*"
        r"(?:const\s*)?(?:override\s*)?(?:noexcept\s*)?(?:final\s*)?\{",
        re.MULTILINE,
    )

    for match in func_pattern.finditer(code):
        ret_type = match.group(1).strip()
        full_name = match.group(2).strip()
        arg_str = match.group(3).strip()

        clean_name = full_name.split("::")[-1]
        if clean_name in keywords:
            continue

        start_char = match.start()
        line_no = code[:start_char].count("\n") + 1
        line_idx = line_no - 1

        raw_line = lines[line_idx] if line_idx < len(lines) else ""
        indent = raw_line[: len(raw_line) - len(raw_line.lstrip())]

        doc, _ = _find_preceding_doc(lines, line_idx)
        args = _split_c_args(arg_str)

        is_method = "::" in full_name or (line_idx > 0 and len(indent) > 0)

        entities.append(
            LanguageEntity(
                name=full_name,
                entity_type="method" if is_method else "function",
                line_start=line_no,
                line_end=line_no,
                return_type=ret_type,
                args=args,
                docstring=doc,
                raw_source=match.group(0),
                indent=indent,
            )
        )

    return entities


def audit_cpp_code(code: str) -> LanguageAuditResult:
    """Audit C++ code for classes, methods, and Doxygen documentation."""
    entities = parse_cpp_code(code)
    issues: List[LanguageIssue] = []

    classes = [e for e in entities if e.entity_type == "class"]
    funcs = [e for e in entities if e.entity_type in ("function", "method")]

    total_classes = len(classes)
    total_funcs = len(funcs)
    doc_classes = sum(1 for c in classes if c.docstring and c.docstring.strip())
    doc_funcs = sum(1 for f in funcs if f.docstring and f.docstring.strip())
    typed_returns = sum(1 for f in funcs if f.return_type and f.return_type != "void")

    # Check Class Documentation
    for cls in classes:
        if not cls.docstring or not cls.docstring.strip():
            issues.append(
                LanguageIssue(
                    line=cls.line_start,
                    entity=cls.name,
                    entity_type="class",
                    issue_type="Missing Docstring",
                    severity="ERROR",
                    message=f"Class '{cls.name}' has no Doxygen documentation comment.",
                    recommendation=f"Add a /** @brief ... */ Doxygen comment above class '{cls.name}'.",
                    can_fix=True,
                )
            )

    # Check Function Documentation
    for func in funcs:
        doc = func.docstring
        if not doc or not doc.strip():
            issues.append(
                LanguageIssue(
                    line=func.line_start,
                    entity=func.name,
                    entity_type=func.entity_type,
                    issue_type="Missing Docstring",
                    severity="ERROR",
                    message=f"{func.entity_type.capitalize()} '{func.name}' has no Doxygen documentation comment.",
                    recommendation=f"Add a /** @brief ... */ Doxygen comment above '{func.name}'.",
                    can_fix=True,
                )
            )
        else:
            for arg in func.args:
                if f"@param {arg.name}" not in doc and f"\\param {arg.name}" not in doc:
                    issues.append(
                        LanguageIssue(
                            line=func.line_start,
                            entity=func.name,
                            entity_type=func.entity_type,
                            issue_type="Missing Arg Doc",
                            severity="WARNING",
                            message=f"Parameter '{arg.name}' is not documented in Doxygen comment.",
                            recommendation=f"Add '@param {arg.name} Description...' to the Doxygen comment.",
                            can_fix=False,
                        )
                    )

            if func.return_type and func.return_type != "void":
                if "@return" not in doc and "\\return" not in doc:
                    issues.append(
                        LanguageIssue(
                            line=func.line_start,
                            entity=func.name,
                            entity_type=func.entity_type,
                            issue_type="Missing Return Doc",
                            severity="WARNING",
                            message=f"Return value of type '{func.return_type}' is missing '@return' tag.",
                            recommendation="Add '@return Description of return value' to the Doxygen comment.",
                            can_fix=False,
                        )
                    )

    total_items = total_classes + total_funcs
    if total_items == 0:
        score = 100.0
    else:
        doc_ratio = (doc_classes + doc_funcs) / total_items
        score = max(0.0, min(100.0, doc_ratio * 100.0 - (len(issues) * 2.0)))

    grade, label, color = compute_health_grade(score)

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


def generate_cpp_doxygen(entity: LanguageEntity) -> str:
    """Generate Doxygen doc comment for a C++ class or method."""
    clean_name = entity.name.split("::")[-1]
    readable_name = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", clean_name).replace("_", " ").strip()
    if entity.entity_type == "class":
        summary = f"{clean_name} representation."
    else:
        summary = f"{readable_name.capitalize()}."

    lines = [
        f"{entity.indent}/**",
        f"{entity.indent} * @brief {summary}",
    ]

    if entity.args:
        lines.append(f"{entity.indent} *")
        for arg in entity.args:
            lines.append(f"{entity.indent} * @param {arg.name} The {arg.name.replace('_', ' ')} parameter.")

    if entity.return_type and entity.return_type != "void":
        lines.append(f"{entity.indent} *")
        lines.append(f"{entity.indent} * @return {entity.return_type} The computed result.")

    lines.append(f"{entity.indent} */")
    return "\n".join(lines)


def patch_cpp_code(
    code: str, target_entity: Optional[str] = None
) -> Tuple[str, int]:
    """Patch missing Doxygen docstrings into C++ code."""
    entities = parse_cpp_code(code)
    candidates = [e for e in entities if not e.docstring or not e.docstring.strip()]

    if target_entity:
        candidates = [e for e in candidates if e.name == target_entity or e.name.split("::")[-1] == target_entity]

    if not candidates:
        return code, 0

    lines = code.splitlines()
    candidates.sort(key=lambda e: e.line_start, reverse=True)

    patched_count = 0
    for item in candidates:
        line_idx = item.line_start - 1
        if line_idx >= len(lines):
            continue

        doxygen_comment = generate_cpp_doxygen(item)
        doc_lines = doxygen_comment.splitlines()

        lines = lines[:line_idx] + doc_lines + lines[line_idx:]
        patched_count += 1

    patched_code = "\n".join(lines) + ("\n" if code.endswith("\n") else "")
    return patched_code, patched_count
