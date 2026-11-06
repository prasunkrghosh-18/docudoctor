"""Cyclomatic complexity and code maintainability index calculation."""

import ast
import math
import re
from typing import Dict, List, Tuple


class ComplexityVisitor(ast.NodeVisitor):
    """AST visitor to compute cyclomatic complexity for a Python function."""

    def __init__(self):
        self.complexity = 1  # Base complexity

    def visit_If(self, node: ast.If) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        # Each 'and' or 'or' adds a decision path
        self.complexity += max(1, len(node.values) - 1)
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        self.complexity += 1 + len(node.ifs)
        self.generic_visit(node)


def calculate_function_complexity(node: ast.AST) -> int:
    """Calculate cyclomatic complexity of a Python function AST node."""
    visitor = ComplexityVisitor()
    # Visit children of the function (skip function def node itself)
    for child in ast.iter_child_nodes(node):
        visitor.visit(child)
    return visitor.complexity


def calculate_text_complexity(code_snippet: str) -> int:
    """Heuristic cyclomatic complexity for C, C++, and Java functions."""
    complexity = 1
    patterns = [
        r"\bif\b",
        r"\belse\s+if\b",
        r"\bfor\b",
        r"\bwhile\b",
        r"\bcatch\b",
        r"\bcase\b",
        r"&&",
        r"\|\|",
        r"\?",
    ]
    for pattern in patterns:
        complexity += len(re.findall(pattern, code_snippet))
    return max(1, complexity)


def calculate_maintainability_index(total_loc: int, avg_complexity: float, total_issues: int) -> Tuple[float, str]:
    """
    Computes Maintainability Index (0-100) and grade letter.
    Formula balances volume (lines of code), cyclomatic complexity, and defect density.
    """
    if total_loc <= 0:
        return 100.0, "A"

    # Base score 100 with penalties for complexity and issues
    loc_factor = min(30.0, math.log(max(1, total_loc), 2) * 3.5)
    complexity_factor = min(40.0, avg_complexity * 3.8)
    issue_penalty = min(30.0, total_issues * 2.5)

    raw_mi = 100.0 - loc_factor - complexity_factor - issue_penalty
    mi_score = max(0.0, min(100.0, round(raw_mi, 1)))

    if mi_score >= 80:
        grade = "A"
    elif mi_score >= 65:
        grade = "B"
    elif mi_score >= 50:
        grade = "C"
    else:
        grade = "D"

    return mi_score, grade
