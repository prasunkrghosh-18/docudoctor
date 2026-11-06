"""C language parser, Doxygen documentation auditor, and code patcher."""

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


def _split_c_args(arg_str: str) -> List[LanguageArg]:
    """Parse comma-separated C parameter declarations."""
    arg_str = arg_str.strip()
    if not arg_str or arg_str == "void":
        return []

    args: List[LanguageArg] = []
    # Split by comma (outside nested parens)
    raw_parts = [p.strip() for p in arg_str.split(",") if p.strip()]

    for part in raw_parts:
        # Match type and parameter name: e.g. "const char* name", "int count", "double* values[]"
        match = re.search(r"^(.*?)\s*([a-zA-Z_][a-zA-Z0-9_]*)(?:\[\s*\])?$", part)
        if match:
            type_part = match.group(1).strip()
            name_part = match.group(2).strip()
            args.append(LanguageArg(name=name_part, type_name=type_part or None))
        else:
            args.append(LanguageArg(name=part, type_name=None))

    return args


def _find_preceding_doc(lines: List[str], target_line_idx: int) -> Tuple[Optional[str], int]:
    """
    Search backwards from target_line_idx to find a preceding comment block (/** ... */ or ///).
    Returns: (doc_string, start_line_idx)
    """
    idx = target_line_idx - 1
    # Skip empty lines
    while idx >= 0 and not lines[idx].strip():
        idx -= 1

    if idx < 0:
        return None, target_line_idx

    end_idx = idx
    # Check for multi-line block comment closing */
    if lines[end_idx].strip().endswith("*/"):
        start_idx = end_idx
        while start_idx >= 0 and "/*" not in lines[start_idx]:
            start_idx -= 1
        if start_idx >= 0 and "/*" in lines[start_idx]:
            doc_text = "\n".join(lines[start_idx : end_idx + 1])
            return doc_text, start_idx

    # Check for single-line /// comments
    if lines[end_idx].strip().startswith("///"):
        start_idx = end_idx
        while start_idx - 1 >= 0 and lines[start_idx - 1].strip().startswith("///"):
            start_idx -= 1
        doc_text = "\n".join(lines[start_idx : end_idx + 1])
        return doc_text, start_idx

    return None, target_line_idx


def parse_c_code(code: str) -> List[LanguageEntity]:
    """Parse C functions and their doc comments."""
    lines = code.splitlines()
    entities: List[LanguageEntity] = []

    # C function regex:
    # return_type function_name(arg_list) {
    # Ignore control keywords like if, while, for, switch, catch
    keywords = {"if", "while", "for", "switch", "catch", "return", "sizeof"}

    # Pattern looks for: return_type func_name ( args ) {
    func_pattern = re.compile(
        r"^[ \t]*((?:(?:const|static|inline|extern|unsigned|signed|volatile|struct|enum)\s+)*"
        r"[a-zA-Z_][a-zA-Z0-9_* \t]+?)\s+"
        r"([a-zA-Z_][a-zA-Z0-9_]*)\s*"
        r"\(([^;{]*?)\)\s*\{",
        re.MULTILINE,
    )

    for match in func_pattern.finditer(code):
        ret_type = match.group(1).strip()
        func_name = match.group(2).strip()
        arg_str = match.group(3).strip()

        if func_name in keywords:
            continue

        # Calculate line number
        start_char = match.start()
        line_no = code[:start_char].count("\n") + 1
        line_idx = line_no - 1

        # Detect line indent
        raw_line = lines[line_idx] if line_idx < len(lines) else ""
        indent = raw_line[: len(raw_line) - len(raw_line.lstrip())]

        # Extract preceding doc comment
        doc, _ = _find_preceding_doc(lines, line_idx)

        # Parse args
        args = _split_c_args(arg_str)

        entities.append(
            LanguageEntity(
                name=func_name,
                entity_type="function",
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


def audit_c_code(code: str) -> LanguageAuditResult:
    """Audit C code for documentation coverage, Doxygen compliance, and parameter tags."""
    entities = parse_c_code(code)
    issues: List[LanguageIssue] = []

    total_funcs = len(entities)
    doc_funcs = 0
    typed_returns = 0

    for func in entities:
        if func.return_type and func.return_type != "void":
            typed_returns += 1

        doc = func.docstring
        if not doc or not doc.strip():
            issues.append(
                LanguageIssue(
                    line=func.line_start,
                    entity=func.name,
                    entity_type="function",
                    issue_type="Missing Docstring",
                    severity="ERROR",
                    message=f"Function '{func.name}' has no Doxygen documentation comment.",
                    recommendation=f"Add a /** @brief ... */ Doxygen comment above '{func.name}'.",
                    can_fix=True,
                )
            )
        else:
            doc_funcs += 1
            # Check Doxygen @param coverage
            for arg in func.args:
                if f"@param {arg.name}" not in doc and f"\\param {arg.name}" not in doc:
                    issues.append(
                        LanguageIssue(
                            line=func.line_start,
                            entity=func.name,
                            entity_type="function",
                            issue_type="Missing Arg Doc",
                            severity="WARNING",
                            message=f"Parameter '{arg.name}' is not documented in Doxygen comment.",
                            recommendation=f"Add '@param {arg.name} Description...' to the Doxygen comment.",
                            can_fix=False,
                        )
                    )

            # Check @return coverage for non-void returns
            if func.return_type and func.return_type != "void":
                if "@return" not in doc and "\\return" not in doc:
                    issues.append(
                        LanguageIssue(
                            line=func.line_start,
                            entity=func.name,
                            entity_type="function",
                            issue_type="Missing Return Doc",
                            severity="WARNING",
                            message=f"Return value of type '{func.return_type}' is missing '@return' tag.",
                            recommendation="Add '@return Description of return value' to the Doxygen comment.",
                            can_fix=False,
                        )
                    )

    # Complexity & Maintainability calculation
    complexities = [calculate_text_complexity(e.raw_source or "") for e in entities]
    avg_complexity = round(sum(complexities) / len(complexities), 1) if complexities else 1.0
    for idx, e in enumerate(entities):
        if idx < len(complexities):
            e.complexity = complexities[idx]
        if e.complexity > 10:
            issues.append(
                LanguageIssue(
                    line=e.line_start,
                    entity=e.name,
                    entity_type="function",
                    issue_type="High Complexity",
                    severity="WARNING",
                    message=f"Function '{e.name}' has high cyclomatic complexity ({e.complexity} > 10).",
                    recommendation="Decompose logic into smaller modular functions.",
                    can_fix=False,
                )
            )

    total_loc = len([l for l in code.splitlines() if l.strip()])
    mi_score, mi_grade = calculate_maintainability_index(total_loc, avg_complexity, len(issues))

    if total_funcs == 0:
        score = 100.0
    else:
        doc_ratio = doc_funcs / total_funcs
        score = max(0.0, min(100.0, doc_ratio * 100.0 - (len(issues) * 2.0)))

    grade, label, color = compute_health_grade(score)

    return LanguageAuditResult(
        score=round(score, 1),
        grade=grade,
        label=label,
        color=color,
        total_functions=total_funcs,
        total_classes=0,
        documented_functions=doc_funcs,
        typed_returns=typed_returns,
        issues=issues,
        entities=entities,
        avg_complexity=avg_complexity,
        maintainability_index=mi_score,
        maintainability_grade=mi_grade,
    )


def generate_c_doxygen(func: LanguageEntity) -> str:
    """Generate professional Doxygen doc comment for a C function."""
    readable_name = func.name.replace("_", " ").strip().capitalize()
    lines = [
        f"{func.indent}/**",
        f"{func.indent} * @brief {readable_name}.",
    ]

    if func.args:
        lines.append(f"{func.indent} *")
        for arg in func.args:
            lines.append(f"{func.indent} * @param {arg.name} The {arg.name.replace('_', ' ')} parameter.")

    if func.return_type and func.return_type != "void":
        lines.append(f"{func.indent} *")
        lines.append(f"{func.indent} * @return {func.return_type} The computed result.")

    lines.append(f"{func.indent} */")
    return "\n".join(lines)


def patch_c_code(
    code: str, target_function: Optional[str] = None
) -> Tuple[str, int]:
    """Patch missing Doxygen docstrings into C code."""
    entities = parse_c_code(code)
    candidates = [f for f in entities if not f.docstring or not f.docstring.strip()]

    if target_function:
        candidates = [f for f in candidates if f.name == target_function]

    if not candidates:
        return code, 0

    lines = code.splitlines()
    # Sort descending by start line to keep line indices stable
    candidates.sort(key=lambda f: f.line_start, reverse=True)

    patched_count = 0
    for func in candidates:
        line_idx = func.line_start - 1
        if line_idx >= len(lines):
            continue

        doxygen_comment = generate_c_doxygen(func)
        doc_lines = doxygen_comment.splitlines()

        # Insert Doxygen block directly above the function line
        lines = lines[:line_idx] + doc_lines + lines[line_idx:]
        patched_count += 1

    patched_code = "\n".join(lines) + ("\n" if code.endswith("\n") else "")
    return patched_code, patched_count
