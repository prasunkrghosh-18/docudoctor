"""Unit tests for complexity analysis and markdown reporter."""

import ast
from docudoctor.complexity import (
    calculate_function_complexity,
    calculate_maintainability_index,
    calculate_text_complexity,
)
from docudoctor.languages.base import LanguageAuditResult, LanguageIssue
from docudoctor.reporter import generate_markdown_report


def test_python_complexity_calculator():
    code = """def sample(x: int):
    if x > 10:
        for i in range(x):
            if i % 2 == 0:
                print(i)
    elif x < 0:
        return -1
    return 0
"""
    tree = ast.parse(code)
    func_node = tree.body[0]
    complexity = calculate_function_complexity(func_node)
    # Base 1 + if + for + if + elif = 5
    assert complexity >= 4


def test_text_complexity_for_c_and_java():
    snippet = """
    if (a > 0 && b > 0) {
        for (int i = 0; i < a; i++) {
            if (i == 2) break;
        }
    } else if (a == -1) {
        return 0;
    }
    """
    comp = calculate_text_complexity(snippet)
    assert comp >= 4


def test_maintainability_index():
    score, grade = calculate_maintainability_index(total_loc=50, avg_complexity=2.0, total_issues=1)
    assert 0.0 <= score <= 100.0
    assert grade in ("A", "B", "C", "D")


def test_markdown_report_generation():
    res = LanguageAuditResult(
        score=92.5,
        grade="A",
        label="EXCELLENT",
        color="#10b981",
        total_functions=5,
        total_classes=1,
        documented_functions=5,
        typed_returns=4,
        avg_complexity=1.8,
        maintainability_index=88.5,
        maintainability_grade="A",
        issues=[],
    )
    report = generate_markdown_report(res, filename="payment.py", language="python")
    assert "# 🩺 DocuDoctor Code Health & Audit Report" in report
    assert "92.5%" in report
    assert "Grade A" in report
    assert "payment.py" in report
    assert "Maintainability Index" in report
