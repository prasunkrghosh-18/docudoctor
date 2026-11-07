"""Space & Time Complexity Estimator for multi-language code.

Uses AST analysis (Python) and heuristic regex patterns (C/C++/Java) to
estimate Big-O time and space complexity for each function/method.

This is a heuristic estimator — not a formal proof — but it correctly
identifies common patterns (loops, recursion, sorting, hashing, etc.)
that dominate the complexity class of real-world code.
"""

import ast
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class FunctionComplexity:
    """Complexity estimate for a single function."""

    name: str
    line: int
    time_complexity: str        # e.g. "O(n²)"
    space_complexity: str       # e.g. "O(n)"
    time_reason: str            # human-readable explanation
    space_reason: str
    risk: str                   # "low" | "medium" | "high" | "critical"


@dataclass
class ComplexityAnalysis:
    """Full complexity analysis result for a code snippet."""

    functions: List[FunctionComplexity] = field(default_factory=list)
    overall_time: str = "O(1)"
    overall_space: str = "O(1)"
    overall_risk: str = "low"
    summary: str = ""


# ──────────────────────────────────────────────────────────────
# Big-O risk classification
# ──────────────────────────────────────────────────────────────

_COMPLEXITY_ORDER = ["O(1)", "O(log n)", "O(n)", "O(n log n)", "O(n²)", "O(n³)", "O(2ⁿ)", "O(n!)"]
_RISK_MAP = {
    "O(1)": "low",
    "O(log n)": "low",
    "O(n)": "low",
    "O(n log n)": "medium",
    "O(n²)": "high",
    "O(n³)": "critical",
    "O(2ⁿ)": "critical",
    "O(n!)": "critical",
}


def _rank(bigo: str) -> int:
    try:
        return _COMPLEXITY_ORDER.index(bigo)
    except ValueError:
        return 2  # default O(n)


def _worst(*bigos: str) -> str:
    return max(bigos, key=_rank)


# ──────────────────────────────────────────────────────────────
# Python AST-based analyser
# ──────────────────────────────────────────────────────────────

def _count_nested_loops(node: ast.AST) -> int:
    """Count maximum loop nesting depth in an AST node."""
    if isinstance(node, (ast.For, ast.While, ast.AsyncFor)):
        # Count nesting in body
        inner = max((_count_nested_loops(child) for child in ast.walk(node)
                     if child is not node and isinstance(child, (ast.For, ast.While, ast.AsyncFor))),
                    default=0)
        return 1 + inner
    return max((_count_nested_loops(child) for child in ast.iter_child_nodes(node)), default=0)


def _has_recursion(func_node: ast.AST, func_name: str) -> bool:
    """Check if a function calls itself (direct recursion)."""
    for node in ast.walk(func_node):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == func_name:
                return True
            if isinstance(node.func, ast.Attribute) and node.func.attr == func_name:
                return True
    return False


def _uses_sorting(func_node: ast.AST) -> bool:
    """Check for .sort(), sorted(), heapq, bisect calls."""
    for node in ast.walk(func_node):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr in ('sort', 'sorted', 'heappush', 'heappop', 'nlargest', 'nsmallest'):
                return True
            if isinstance(node.func, ast.Name) and node.func.id in ('sorted', 'heapify'):
                return True
    return False


def _uses_hashing(func_node: ast.AST) -> bool:
    """Check for dict / set usage implying hash table (O(1) lookup)."""
    for node in ast.walk(func_node):
        if isinstance(node, (ast.Dict, ast.Set, ast.DictComp, ast.SetComp)):
            return True
    return False


def _space_uses_collections(func_node: ast.AST) -> bool:
    """Check if function allocates list/dict/set proportional to input."""
    for node in ast.walk(func_node):
        if isinstance(node, (ast.List, ast.Dict, ast.Set, ast.ListComp, ast.DictComp, ast.SetComp)):
            return True
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in ('list', 'dict', 'set', 'tuple', 'copy', 'deepcopy', 'sorted'):
                return True
    return False


def _analyse_python_function(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> FunctionComplexity:
    """Estimate time and space complexity for a single Python function."""
    name = func_node.name

    # Nesting depth → time complexity
    nest = _count_nested_loops(func_node)
    is_recursive = _has_recursion(func_node, name)
    uses_sort = _uses_sorting(func_node)
    uses_hash = _uses_hashing(func_node)
    uses_space = _space_uses_collections(func_node)

    # ── Time complexity ──────────────────────────────────────
    if is_recursive:
        # Rough heuristic: if there's also a loop → O(n²), else O(2ⁿ) for naive recursion
        if nest >= 1:
            time_c = "O(n²)"
            time_r = "Recursive function with loop(s) — likely O(n²) or O(n log n) depending on recursion depth."
        else:
            time_c = "O(2ⁿ)"
            time_r = "Direct recursion without memoisation — exponential in worst case. Consider memoisation or DP."
    elif nest == 0:
        if uses_sort:
            time_c = "O(n log n)"
            time_r = "No explicit loops, but uses sorting (sort/sorted) — O(n log n)."
        else:
            time_c = "O(1)"
            time_r = "No loops or recursion detected — constant time."
    elif nest == 1:
        if uses_sort:
            time_c = "O(n log n)"
            time_r = "Single loop with an internal sort call — O(n log n)."
        else:
            time_c = "O(n)"
            time_r = "Single loop iterating over input — linear time."
    elif nest == 2:
        time_c = "O(n²)"
        time_r = "Two nested loops — quadratic time. Watch for large input sizes."
    elif nest == 3:
        time_c = "O(n³)"
        time_r = "Three levels of nested loops — cubic time. High risk for performance."
    else:
        time_c = "O(n³)"
        time_r = f"{nest}-level nested loops detected — polynomial time, consider optimisation."

    # ── Space complexity ─────────────────────────────────────
    if uses_space:
        space_c = "O(n)"
        space_r = "Allocates list/dict/set proportional to input — linear space."
    elif is_recursive:
        space_c = "O(n)"
        space_r = "Recursion uses call-stack space proportional to depth — O(n) space."
    else:
        space_c = "O(1)"
        space_r = "No significant data structure allocations — constant auxiliary space."

    risk = _RISK_MAP.get(time_c, "medium")
    return FunctionComplexity(
        name=name, line=func_node.lineno,
        time_complexity=time_c, space_complexity=space_c,
        time_reason=time_r, space_reason=space_r, risk=risk
    )


def _analyse_python(code: str) -> ComplexityAnalysis:
    """Full complexity analysis for a Python snippet."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return ComplexityAnalysis(summary="Syntax error — could not parse code.")

    results: List[FunctionComplexity] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Only top-level and class methods (not nested helpers)
            results.append(_analyse_python_function(node))

    if not results:
        return ComplexityAnalysis(summary="No functions found to analyse.")

    worst_time = max((r.time_complexity for r in results), key=_rank)
    worst_space = max((r.space_complexity for r in results), key=_rank)
    worst_risk = _RISK_MAP.get(worst_time, "low")
    fn_summary = f"Analysed {len(results)} function(s). Worst-case: {worst_time} time, {worst_space} space."

    return ComplexityAnalysis(
        functions=results,
        overall_time=worst_time,
        overall_space=worst_space,
        overall_risk=worst_risk,
        summary=fn_summary,
    )


# ──────────────────────────────────────────────────────────────
# C / C++ / Java heuristic analyser
# ──────────────────────────────────────────────────────────────

_LOOP_RE = re.compile(r'\b(for|while|do)\b')
_SORT_RE = re.compile(r'\b(sort|qsort|std::sort|Collections\.sort|Arrays\.sort|heapify)\b')
_RECUR_RE = re.compile(r'(\w+)\s*\(')   # will match function calls; we check if name == func name
_ALLOC_RE = re.compile(r'\b(malloc|calloc|realloc|new\s+\w|push_back|ArrayList|HashMap|HashSet|vector)\b')


def _analyse_c_java_function(name: str, body: str) -> FunctionComplexity:
    """Heuristic complexity estimate for a C/C++/Java function body."""
    # Count loop nesting (simple heuristic: count opening braces inside loop blocks)
    loop_count = len(_LOOP_RE.findall(body))
    # Nesting: look for loops inside loops
    # Very rough — count lines that have both a loop keyword and an enclosing loop
    loop_lines = [i for i, ln in enumerate(body.splitlines()) if _LOOP_RE.search(ln)]
    nest_depth = 1 if loop_count >= 1 else 0
    # If there are ≥2 loops and at least one is indented more → assume nesting
    if loop_count >= 2:
        indents = [len(body.splitlines()[i]) - len(body.splitlines()[i].lstrip()) for i in loop_lines if i < len(body.splitlines())]
        if len(set(indents)) > 1:
            nest_depth = 2

    is_sort = bool(_SORT_RE.search(body))
    is_alloc = bool(_ALLOC_RE.search(body))
    # Simple recursion check: does the function body call itself?
    call_pattern = re.compile(rf'\b{re.escape(name)}\s*\(')
    is_recursive = bool(call_pattern.search(body))

    if is_recursive:
        time_c = "O(2ⁿ)"
        time_r = "Direct recursive call detected — exponential worst case without memoisation."
    elif nest_depth >= 2:
        time_c = "O(n²)"
        time_r = "Nested loop structure detected — quadratic time complexity."
    elif loop_count == 1 and is_sort:
        time_c = "O(n log n)"
        time_r = "Single loop with a sort call — O(n log n)."
    elif is_sort:
        time_c = "O(n log n)"
        time_r = "Sort call detected — O(n log n)."
    elif loop_count == 1:
        time_c = "O(n)"
        time_r = "Single loop iterating over input — linear time."
    elif loop_count == 0:
        time_c = "O(1)"
        time_r = "No loops or recursion — constant time."
    else:
        time_c = "O(n²)"
        time_r = f"{loop_count} loops detected — likely quadratic."

    space_c = "O(n)" if is_alloc else "O(1)"
    space_r = ("Dynamic memory allocation detected — O(n) space." if is_alloc
                else "No dynamic allocation — constant auxiliary space.")

    risk = _RISK_MAP.get(time_c, "medium")
    return FunctionComplexity(name=name, line=1, time_complexity=time_c,
                               space_complexity=space_c, time_reason=time_r,
                               space_reason=space_r, risk=risk)


def _analyse_c_java(code: str, language: str = "c") -> ComplexityAnalysis:
    """Heuristic complexity analysis for C/C++/Java code."""
    # Extract function-like blocks using a simple brace-matching strategy
    fn_re = re.compile(
        r'(?:(?:public|private|protected|static|virtual|inline|extern|double|int|void|float|'
        r'bool|char|auto|long|short|unsigned|const|std::\w+|String|List|Map|boolean)\s+)+'
        r'(\w+)\s*\([^)]*\)\s*(?:const\s*)?\{',
        re.MULTILINE
    )
    results: List[FunctionComplexity] = []

    for m in fn_re.finditer(code):
        fn_name = m.group(1)
        if fn_name in ('if', 'for', 'while', 'switch', 'catch'):
            continue
        # Extract body by counting braces
        start = m.end() - 1  # position of opening {
        depth = 0
        body_chars = []
        for ch in code[start:]:
            body_chars.append(ch)
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    break
        body = ''.join(body_chars)
        fc = _analyse_c_java_function(fn_name, body)
        fc.line = code[:m.start()].count('\n') + 1
        results.append(fc)

    if not results:
        return ComplexityAnalysis(summary="No functions detected for complexity analysis.")

    worst_time = max((r.time_complexity for r in results), key=_rank)
    worst_space = max((r.space_complexity for r in results), key=_rank)
    worst_risk = _RISK_MAP.get(worst_time, "low")
    fn_summary = f"Analysed {len(results)} function(s). Worst-case: {worst_time} time, {worst_space} space."

    return ComplexityAnalysis(
        functions=results,
        overall_time=worst_time,
        overall_space=worst_space,
        overall_risk=worst_risk,
        summary=fn_summary,
    )


# ──────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────

def analyse_complexity(code: str, language: str = "python") -> ComplexityAnalysis:
    """Estimate time and space complexity for each function in the given code.

    Args:
        code: Source code string.
        language: One of 'python', 'c', 'cpp', 'java'.

    Returns:
        ComplexityAnalysis with per-function Big-O estimates and overall worst case.
    """
    lang = language.lower()
    if lang == "python":
        return _analyse_python(code)
    else:
        return _analyse_c_java(code, language=lang)
