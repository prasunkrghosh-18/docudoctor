"""Java language parser, Javadoc documentation auditor, and code patcher."""

import re
from typing import List, Optional, Tuple

from docudoctor.complexity import calculate_maintainability_index, calculate_text_complexity
from docudoctor.languages.base import (
    LanguageArg,
    LanguageAuditResult,
    LanguageEntity,
    LanguageIssue,
    compute_health_grade,
)
from docudoctor.languages.c_engine import _find_preceding_doc


def _split_java_args(arg_str: str) -> List[LanguageArg]:
    """Parse comma-separated Java parameter declarations."""
    arg_str = arg_str.strip()
    if not arg_str:
        return []

    args: List[LanguageArg] = []
    # Split by comma outside generic brackets
    raw_parts: List[str] = []
    current: List[str] = []
    bracket_depth = 0

    for char in arg_str:
        if char == "<":
            bracket_depth += 1
        elif char == ">":
            bracket_depth -= 1

        if char == "," and bracket_depth == 0:
            raw_parts.append("".join(current).strip())
            current = []
        else:
            current.append(char)

    if current:
        raw_parts.append("".join(current).strip())

    for part in raw_parts:
        # Match parameter name (last token) and type (everything before)
        match = re.search(r"^(.*?)\s+([a-zA-Z_][a-zA-Z0-9_]*)(?:\[\s*\])?$", part)
        if match:
            type_part = match.group(1).strip()
            name_part = match.group(2).strip()
            args.append(LanguageArg(name=name_part, type_name=type_part))
        else:
            args.append(LanguageArg(name=part, type_name=None))

    return args


def parse_java_code(code: str) -> List[LanguageEntity]:
    """Parse Java classes, interfaces, and methods along with Javadoc comments."""
    lines = code.splitlines()
    entities: List[LanguageEntity] = []

    # 1. Match Classes & Interfaces
    class_pattern = re.compile(
        r"^[ \t]*(?:(?:public|protected|private|abstract|final|static)\s+)*"
        r"(class|interface|enum|record)\s+"
        r"([a-zA-Z_][a-zA-Z0-9_]*)"
        r"(?:<[^>]+>)?(?:\s+(?:extends|implements)\s+[^{]+)?\s*\{",
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
                entity_type="class" if entity_kind != "interface" else "interface",
                line_start=line_no,
                line_end=line_no,
                return_type=None,
                args=[],
                docstring=doc,
                raw_source=match.group(0),
                indent=indent,
            )
        )

    # 2. Match Java Methods
    keywords = {"if", "while", "for", "switch", "catch", "synchronized", "return", "new"}

    method_pattern = re.compile(
        r"^[ \t]*(?:@\w+(?:\([^)]*\))?\s*)*"
        r"((?:(?:public|protected|private|static|final|abstract|synchronized|native|default)\s+)+)"
        r"([a-zA-Z0-9_<>\[\], \t]+?)\s+"
        r"([a-zA-Z_][a-zA-Z0-9_]*)\s*"
        r"\(([^;{]*?)\)\s*"
        r"(?:throws\s+[^{;]+)?\s*(?:\{|;)",
        re.MULTILINE,
    )

    for match in method_pattern.finditer(code):
        modifiers = match.group(1).strip()
        ret_type = match.group(2).strip()
        method_name = match.group(3).strip()
        arg_str = match.group(4).strip()

        if method_name in keywords:
            continue

        start_char = match.start()
        line_no = code[:start_char].count("\n") + 1
        line_idx = line_no - 1

        raw_line = lines[line_idx] if line_idx < len(lines) else ""
        indent = raw_line[: len(raw_line) - len(raw_line.lstrip())]

        doc, _ = _find_preceding_doc(lines, line_idx)
        args = _split_java_args(arg_str)

        visibility = "public"
        if "private" in modifiers:
            visibility = "private"
        elif "protected" in modifiers:
            visibility = "protected"

        entities.append(
            LanguageEntity(
                name=method_name,
                entity_type="method",
                line_start=line_no,
                line_end=line_no,
                return_type=ret_type,
                args=args,
                docstring=doc,
                raw_source=match.group(0),
                indent=indent,
                visibility=visibility,
            )
        )

    return entities


def audit_java_code(code: str) -> LanguageAuditResult:
    """Audit Java code for Javadoc documentation, class docs, and tag completeness."""
    entities = parse_java_code(code)
    issues: List[LanguageIssue] = []

    classes = [e for e in entities if e.entity_type in ("class", "interface")]
    methods = [e for e in entities if e.entity_type == "method"]

    total_classes = len(classes)
    total_funcs = len(methods)
    doc_classes = sum(1 for c in classes if c.docstring and c.docstring.strip())
    doc_funcs = sum(1 for m in methods if m.docstring and m.docstring.strip())
    typed_returns = sum(1 for m in methods if m.return_type and m.return_type != "void")

    # Audit Classes
    for cls in classes:
        if not cls.docstring or not cls.docstring.strip():
            issues.append(
                LanguageIssue(
                    line=cls.line_start,
                    entity=cls.name,
                    entity_type=cls.entity_type,
                    issue_type="Missing Javadoc",
                    severity="ERROR",
                    message=f"Java {cls.entity_type} '{cls.name}' has no Javadoc comment.",
                    recommendation=f"Add a /** ... */ Javadoc description above '{cls.name}'.",
                    can_fix=True,
                )
            )

    # Audit Methods
    for m in methods:
        doc = m.docstring
        if not doc or not doc.strip():
            severity = "ERROR" if m.visibility in ("public", "protected") else "INFO"
            issues.append(
                LanguageIssue(
                    line=m.line_start,
                    entity=m.name,
                    entity_type="method",
                    issue_type="Missing Javadoc",
                    severity=severity,
                    message=f"{m.visibility.capitalize()} method '{m.name}' has no Javadoc comment.",
                    recommendation=f"Add a /** ... */ Javadoc comment above method '{m.name}'.",
                    can_fix=True,
                )
            )
        else:
            # Check @param tags
            for arg in m.args:
                if f"@param {arg.name}" not in doc:
                    issues.append(
                        LanguageIssue(
                            line=m.line_start,
                            entity=m.name,
                            entity_type="method",
                            issue_type="Missing @param",
                            severity="WARNING",
                            message=f"Parameter '{arg.name}' is missing '@param' documentation tag.",
                            recommendation=f"Add '@param {arg.name} Description...' to the Javadoc.",
                            can_fix=False,
                        )
                    )

            # Check @return tag
            if m.return_type and m.return_type != "void":
                if "@return" not in doc:
                    issues.append(
                        LanguageIssue(
                            line=m.line_start,
                            entity=m.name,
                            entity_type="method",
                            issue_type="Missing @return",
                            severity="WARNING",
                            message=f"Return value of type '{m.return_type}' is missing '@return' tag.",
                            recommendation="Add '@return Description of return value' to the Javadoc.",
                            can_fix=False,
                        )
                    )

    # Complexity & Maintainability calculation
    complexities = [calculate_text_complexity(m.raw_source or "") for m in methods]
    avg_complexity = round(sum(complexities) / len(complexities), 1) if complexities else 1.0
    for idx, m in enumerate(methods):
        if idx < len(complexities):
            m.complexity = complexities[idx]
        if m.complexity > 10:
            issues.append(
                LanguageIssue(
                    line=m.line_start,
                    entity=m.name,
                    entity_type="method",
                    issue_type="High Complexity",
                    severity="WARNING",
                    message=f"Method '{m.name}' has high cyclomatic complexity ({m.complexity} > 10).",
                    recommendation="Decompose logic into smaller modular methods.",
                    can_fix=False,
                )
            )

    total_loc = len([l for l in code.splitlines() if l.strip()])
    mi_score, mi_grade = calculate_maintainability_index(total_loc, avg_complexity, len(issues))

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
        avg_complexity=avg_complexity,
        maintainability_index=mi_score,
        maintainability_grade=mi_grade,
    )


def generate_java_javadoc(entity: LanguageEntity) -> str:
    """Generate professional Javadoc comment for a Java class or method."""
    readable_name = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", entity.name).replace("_", " ").strip()
    if entity.entity_type in ("class", "interface"):
        summary = f"{entity.name} representation."
    else:
        summary = f"Performs {readable_name.lower()} operation."

    lines = [
        f"{entity.indent}/**",
        f"{entity.indent} * {summary}",
    ]

    if entity.args:
        lines.append(f"{entity.indent} *")
        for arg in entity.args:
            readable_arg = re.sub(r"([A-Z])", r" \1", arg.name).strip().lower()
            lines.append(f"{entity.indent} * @param {arg.name} the {readable_arg} parameter")

    if entity.return_type and entity.return_type != "void":
        lines.append(f"{entity.indent} *")
        lines.append(f"{entity.indent} * @return the computed {entity.return_type} result")

    lines.append(f"{entity.indent} */")
    return "\n".join(lines)


def patch_java_code(
    code: str, target_entity: Optional[str] = None
) -> Tuple[str, int]:
    """Patch missing Javadoc comments into Java code."""
    entities = parse_java_code(code)
    candidates = [e for e in entities if not e.docstring or not e.docstring.strip()]

    if target_entity:
        candidates = [e for e in candidates if e.name == target_entity]

    if not candidates:
        return code, 0

    lines = code.splitlines()
    candidates.sort(key=lambda e: e.line_start, reverse=True)

    patched_count = 0
    for item in candidates:
        line_idx = item.line_start - 1
        if line_idx >= len(lines):
            continue

        javadoc_comment = generate_java_javadoc(item)
        doc_lines = javadoc_comment.splitlines()

        lines = lines[:line_idx] + doc_lines + lines[line_idx:]
        patched_count += 1

    patched_code = "\n".join(lines) + ("\n" if code.endswith("\n") else "")
    return patched_code, patched_count
