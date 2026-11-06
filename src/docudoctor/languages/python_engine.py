"""Python language adapter wrapping AST visitor, docstring generator, complexity analyzer, and healer."""

import ast
from pathlib import Path
from typing import Optional, Tuple

from docudoctor.complexity import calculate_function_complexity, calculate_maintainability_index
from docudoctor.doctor.generator import DocstringStyle
from docudoctor.doctor.healer import heal_python_code
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
    elif issue_type == "High Complexity":
        return "Refactor complex branching, deeply nested loops, or exception handlers into smaller helper functions."
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

    # Map AST function nodes for complexity analysis
    func_ast_map = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_ast_map[node.name] = node

    total_funcs = len(visitor.functions)
    total_classes = len(visitor.classes)
    total_items = total_funcs + total_classes

    doc_funcs = sum(1 for f in visitor.functions if f.docstring and f.docstring.strip())
    doc_classes = sum(1 for c in visitor.classes if c.docstring and c.docstring.strip())
    typed_returns = sum(1 for f in visitor.functions if f.return_type)

    # Complexity calculation
    complexities = []
    for f in visitor.functions:
        node = func_ast_map.get(f.name)
        comp = calculate_function_complexity(node) if node else 1
        complexities.append(comp)

    avg_complexity = round(sum(complexities) / len(complexities), 1) if complexities else 1.0
    total_loc = len([line for line in code.splitlines() if line.strip() and not line.strip().startswith("#")])
    mi_score, mi_grade = calculate_maintainability_index(total_loc, avg_complexity, len(visitor.issues))

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
        can_fix = (
            (iss_type_str == "Missing Docstring" and i.entity_type in ("function", "method"))
            or iss_type_str in ("Mutable Default Arg", "Missing Return Type")
        )
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

    # Check for high complexity functions (> 10 is high cyclomatic complexity)
    for idx, f in enumerate(visitor.functions):
        comp = complexities[idx] if idx < len(complexities) else 1
        if comp > 10:
            issues.append(
                LanguageIssue(
                    line=f.line_start,
                    entity=f.name,
                    entity_type="method" if f.is_method else "function",
                    issue_type="High Complexity",
                    severity="WARNING",
                    message=f"Function '{f.name}' has high cyclomatic complexity ({comp} > 10).",
                    recommendation=_recommendation_for_issue("High Complexity", f.name),
                    can_fix=False,
                )
            )

    entities: list[LanguageEntity] = []
    for idx, f in enumerate(visitor.functions):
        comp = complexities[idx] if idx < len(complexities) else 1
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
                complexity=comp,
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
        avg_complexity=avg_complexity,
        maintainability_index=mi_score,
        maintainability_grade=mi_grade,
    )


def patch_python_code(
    code: str,
    style: DocstringStyle = DocstringStyle.GOOGLE,
    target_function: Optional[str] = None,
) -> Tuple[str, int]:
    """Patch missing docstrings, mutable defaults, and return type hints into Python code."""
    return heal_python_code(code, style=style, target_entity=target_function)

