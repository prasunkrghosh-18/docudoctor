"""Code Style Analyzer — rates naming conventions, structure, and formatting quality.

The term for this is 'Code Style' or 'Code Linting'. It measures how well code
adheres to language best practices for naming, structure, and readability.
"""

import ast
import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class StyleIssue:
    """A single style violation found in the code."""

    line: int
    code: str           # e.g. "S001"
    message: str
    severity: str       # "error" | "warning" | "info"
    category: str       # "naming" | "structure" | "formatting" | "complexity"


@dataclass
class StyleReport:
    """Complete style analysis result for a snippet."""

    style_score: float            # 0–100
    style_grade: str              # A/B/C/D
    style_label: str              # "Excellent" / "Good" etc.
    issues: List[StyleIssue] = field(default_factory=list)
    breakdown: Dict[str, int] = field(default_factory=dict)


# ──────────────────────────────────────────────────────────────
# Python style checker
# ──────────────────────────────────────────────────────────────

_SNAKE_CASE = re.compile(r'^[a-z_][a-z0-9_]*$')
_PASCAL_CASE = re.compile(r'^[A-Z][a-zA-Z0-9]*$')
_UPPER_SNAKE = re.compile(r'^[A-Z][A-Z0-9_]*$')
_TRAILING_WS = re.compile(r'[ \t]+$', re.MULTILINE)
_LONG_LINE_LIMIT = 88          # Black/PEP8-E501 tolerance
_MAX_FUNC_LINES = 50
_MAX_ARGS = 6


def _check_python_style(code: str) -> StyleReport:
    """Analyse Python code for style issues."""
    issues: List[StyleIssue] = []
    lines = code.splitlines()

    # ── Line-level checks ──────────────────────────────────────
    for lineno, line in enumerate(lines, 1):
        # Long lines
        if len(line) > _LONG_LINE_LIMIT:
            issues.append(StyleIssue(
                line=lineno, code="S101",
                message=f"Line too long ({len(line)} > {_LONG_LINE_LIMIT} chars). PEP 8 recommends ≤ {_LONG_LINE_LIMIT} characters.",
                severity="warning", category="formatting"
            ))
        # Trailing whitespace
        if re.search(r'[ \t]+$', line):
            issues.append(StyleIssue(
                line=lineno, code="S102",
                message="Trailing whitespace detected.",
                severity="info", category="formatting"
            ))
        # Tabs vs spaces
        if '\t' in line and not code.startswith('\t'):
            issues.append(StyleIssue(
                line=lineno, code="S103",
                message="Mixed tabs and spaces for indentation.",
                severity="error", category="formatting"
            ))

    # ── AST checks ─────────────────────────────────────────────
    try:
        tree = ast.parse(code)
    except SyntaxError:
        # Cannot go deeper without valid AST
        return _build_report(issues)

    for node in ast.walk(tree):
        # Function naming
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = node.name
            if not name.startswith('_') and not _SNAKE_CASE.match(name):
                issues.append(StyleIssue(
                    line=node.lineno, code="S201",
                    message=f"Function '{name}' should use snake_case naming (PEP 8).",
                    severity="warning", category="naming"
                ))
            # Too many arguments
            arg_count = len([a for a in node.args.args if a.arg not in ('self', 'cls')])
            if arg_count > _MAX_ARGS:
                issues.append(StyleIssue(
                    line=node.lineno, code="S301",
                    message=f"Function '{name}' has {arg_count} parameters (> {_MAX_ARGS}). Consider refactoring.",
                    severity="warning", category="structure"
                ))
            # Function too long
            func_len = (node.end_lineno or node.lineno) - node.lineno + 1
            if func_len > _MAX_FUNC_LINES:
                issues.append(StyleIssue(
                    line=node.lineno, code="S302",
                    message=f"Function '{name}' is {func_len} lines long (> {_MAX_FUNC_LINES}). Consider splitting it.",
                    severity="warning", category="structure"
                ))
            # Magic numbers inside function body
            for child in ast.walk(node):
                if isinstance(child, ast.Constant) and isinstance(child.value, (int, float)):
                    if child.value not in (0, 1, -1, 2, 100, True, False) and not isinstance(child.value, bool):
                        issues.append(StyleIssue(
                            line=getattr(child, 'lineno', node.lineno), code="S401",
                            message=f"Magic number '{child.value}' in '{name}'. Use a named constant instead.",
                            severity="info", category="structure"
                        ))
                        break  # Only flag once per function

        # Class naming
        elif isinstance(node, ast.ClassDef):
            if not _PASCAL_CASE.match(node.name):
                issues.append(StyleIssue(
                    line=node.lineno, code="S202",
                    message=f"Class '{node.name}' should use PascalCase naming (PEP 8).",
                    severity="warning", category="naming"
                ))

        # Module-level constant naming
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    nm = target.id
                    if nm.isupper() and not _UPPER_SNAKE.match(nm):
                        issues.append(StyleIssue(
                            line=node.lineno, code="S203",
                            message=f"Constant '{nm}' should use UPPER_SNAKE_CASE naming.",
                            severity="info", category="naming"
                        ))

    return _build_report(issues)


def _build_report(issues: List[StyleIssue]) -> StyleReport:
    """Convert a list of issues into a StyleReport with score."""
    # Penalty weights
    penalty = sum(
        10 if i.severity == "error"
        else 5 if i.severity == "warning"
        else 2
        for i in issues
    )
    score = max(0.0, min(100.0, round(100.0 - penalty, 1)))

    if score >= 85:
        grade, label = "A", "Excellent"
    elif score >= 70:
        grade, label = "B", "Good"
    elif score >= 55:
        grade, label = "C", "Fair"
    else:
        grade, label = "D", "Needs Work"

    breakdown = {
        "naming": sum(1 for i in issues if i.category == "naming"),
        "structure": sum(1 for i in issues if i.category == "structure"),
        "formatting": sum(1 for i in issues if i.category == "formatting"),
        "complexity": sum(1 for i in issues if i.category == "complexity"),
    }
    return StyleReport(style_score=score, style_grade=grade,
                       style_label=label, issues=issues, breakdown=breakdown)


# ──────────────────────────────────────────────────────────────
# C / C++ / Java style checker (regex-based heuristic)
# ──────────────────────────────────────────────────────────────

_C_SNAKE = re.compile(r'^[a-z_][a-z0-9_]*$')
_JAVA_CAMEL = re.compile(r'^[a-z][a-zA-Z0-9]*$')
_JAVA_PASCAL = re.compile(r'^[A-Z][a-zA-Z0-9]*$')


def _check_c_style(code: str, lang: str = "c") -> StyleReport:
    """Heuristic style check for C/C++."""
    issues: List[StyleIssue] = []
    lines = code.splitlines()

    for lineno, line in enumerate(lines, 1):
        # Long lines
        if len(line) > _LONG_LINE_LIMIT:
            issues.append(StyleIssue(
                line=lineno, code="S101",
                message=f"Line too long ({len(line)} chars).",
                severity="warning", category="formatting"
            ))
        # Trailing whitespace
        if re.search(r'[ \t]+$', line):
            issues.append(StyleIssue(
                line=lineno, code="S102",
                message="Trailing whitespace.",
                severity="info", category="formatting"
            ))
        # C-style function naming: should be snake_case
        m = re.match(r'^\s*(?:int|void|double|float|char\s*\*?|bool|auto|std::\w+)\s+(\w+)\s*\(', line)
        if m:
            fn = m.group(1)
            if fn not in ('main',) and not _C_SNAKE.match(fn):
                issues.append(StyleIssue(
                    line=lineno, code="S201",
                    message=f"Function '{fn}' should use snake_case naming (C/C++ convention).",
                    severity="warning", category="naming"
                ))
        # Magic numbers
        nums = re.findall(r'\b(\d+)\b', line)
        for n in nums:
            if int(n) not in (0, 1, 2, 100):
                issues.append(StyleIssue(
                    line=lineno, code="S401",
                    message=f"Magic number '{n}' on line {lineno}. Use a named constant.",
                    severity="info", category="structure"
                ))
                break  # Once per line

    return _build_report(issues)


def _check_java_style(code: str) -> StyleReport:
    """Heuristic style check for Java."""
    issues: List[StyleIssue] = []
    lines = code.splitlines()

    for lineno, line in enumerate(lines, 1):
        if len(line) > _LONG_LINE_LIMIT:
            issues.append(StyleIssue(
                line=lineno, code="S101",
                message=f"Line too long ({len(line)} chars). Java convention recommends ≤ 100.",
                severity="warning", category="formatting"
            ))
        # Method naming: should be camelCase
        m = re.match(
            r'^\s*(?:public|private|protected|static|\s)*\s*(?:\w+(?:<[^>]+>)?)\s+(\w+)\s*\(',
            line
        )
        if m:
            fn = m.group(1)
            if fn not in ('main',) and not _JAVA_CAMEL.match(fn) and not _JAVA_PASCAL.match(fn):
                issues.append(StyleIssue(
                    line=lineno, code="S201",
                    message=f"Method '{fn}' should use camelCase naming (Java convention).",
                    severity="warning", category="naming"
                ))
        # Class naming: should be PascalCase
        cm = re.match(r'^\s*(?:public\s+)?class\s+(\w+)', line)
        if cm and not _JAVA_PASCAL.match(cm.group(1)):
            issues.append(StyleIssue(
                line=lineno, code="S202",
                message=f"Class '{cm.group(1)}' should use PascalCase naming.",
                severity="warning", category="naming"
            ))

    return _build_report(issues)


# ──────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────

def analyze_code_style(code: str, language: str = "python") -> StyleReport:
    """Analyze code style for any supported language and return a StyleReport.

    Args:
        code: Source code string.
        language: One of 'python', 'c', 'cpp', 'java'.

    Returns:
        StyleReport with style_score (0-100), grade, label, and issue list.
    """
    lang = language.lower()
    if lang == "python":
        return _check_python_style(code)
    elif lang in ("c", "cpp"):
        return _check_c_style(code, lang=lang)
    elif lang == "java":
        return _check_java_style(code)
    return _check_python_style(code)
