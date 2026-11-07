"""Tests for the complexity estimator and style analyzer modules."""

import pytest
from docudoctor.complexity_estimator import analyse_complexity
from docudoctor.style_analyzer import analyze_code_style


# ──────────────────────────────────────────────────────────────
# Complexity Estimator Tests
# ──────────────────────────────────────────────────────────────

def test_complexity_constant_time():
    code = """def add(a: int, b: int) -> int:
    return a + b
"""
    result = analyse_complexity(code, "python")
    assert len(result.functions) == 1
    assert result.functions[0].time_complexity == "O(1)"
    assert result.functions[0].space_complexity == "O(1)"
    assert result.overall_risk == "low"


def test_complexity_linear_time():
    code = """def find_max(items):
    best = None
    for item in items:
        if best is None or item > best:
            best = item
    return best
"""
    result = analyse_complexity(code, "python")
    assert len(result.functions) == 1
    assert result.functions[0].time_complexity == "O(n)"


def test_complexity_quadratic_nested_loops():
    code = """def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(n - i - 1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr
"""
    result = analyse_complexity(code, "python")
    assert len(result.functions) == 1
    assert result.functions[0].time_complexity == "O(n²)"
    assert result.functions[0].risk in ("high", "critical")


def test_complexity_sorting():
    code = """def rank_items(items):
    return sorted(items)
"""
    result = analyse_complexity(code, "python")
    assert len(result.functions) == 1
    assert result.functions[0].time_complexity == "O(n log n)"


def test_complexity_space_allocation():
    code = """def copy_list(items):
    result = []
    for item in items:
        result.append(item)
    return result
"""
    result = analyse_complexity(code, "python")
    assert len(result.functions) == 1
    assert result.functions[0].space_complexity == "O(n)"


def test_complexity_multiple_functions():
    code = """def linear_search(arr, target):
    for x in arr:
        if x == target:
            return True
    return False

def bubble_sort(arr):
    for i in range(len(arr)):
        for j in range(len(arr)-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
"""
    result = analyse_complexity(code, "python")
    assert len(result.functions) == 2
    # Overall should reflect worst case (bubble sort = O(n²))
    assert result.overall_time == "O(n²)"


def test_complexity_empty_code():
    code = "x = 42"
    result = analyse_complexity(code, "python")
    assert result.functions == []
    assert result.overall_time == "O(1)"


def test_complexity_syntax_error():
    code = "def broken(:"
    result = analyse_complexity(code, "python")
    assert isinstance(result.summary, str)
    assert result.functions == []


def test_complexity_c_code():
    c_code = """int find_max(int arr[], int n) {
    int max = arr[0];
    for (int i = 1; i < n; i++) {
        if (arr[i] > max) max = arr[i];
    }
    return max;
}"""
    result = analyse_complexity(c_code, "c")
    assert len(result.functions) >= 1
    fn = result.functions[0]
    assert fn.name == "find_max"
    assert fn.time_complexity in ("O(n)", "O(n²)")  # heuristic


def test_complexity_overall_risk_field():
    code = """def recurse(n):
    if n <= 0:
        return
    recurse(n - 1)
    recurse(n - 1)
"""
    result = analyse_complexity(code, "python")
    assert result.overall_risk in ("high", "critical")


# ──────────────────────────────────────────────────────────────
# Style Analyzer Tests
# ──────────────────────────────────────────────────────────────

def test_style_clean_python():
    code = """def calculate_tax(price: float, rate: float) -> float:
    return price * rate
"""
    report = analyze_code_style(code, "python")
    assert report.style_score >= 90.0
    assert report.style_grade == "A"
    assert report.style_label == "Excellent"


def test_style_bad_function_name():
    code = """def CalculateDiscount(price):
    return price * 0.1
"""
    report = analyze_code_style(code, "python")
    assert any(i.code == "S201" for i in report.issues)
    assert report.style_score < 100.0


def test_style_mutable_magic_number():
    code = """def process(items):
    LIMIT = 9999
    return items[:LIMIT]
"""
    report = analyze_code_style(code, "python")
    # 9999 is a magic number
    assert any(i.code == "S401" for i in report.issues)


def test_style_long_line():
    code = "def foo():\n    x = 'a' * 200  # " + "x" * 100 + "\n    return x\n"
    report = analyze_code_style(code, "python")
    assert any(i.code == "S101" for i in report.issues)


def test_style_class_naming():
    code = """class paymentGateway:
    pass
"""
    report = analyze_code_style(code, "python")
    assert any(i.code == "S202" for i in report.issues)


def test_style_breakdown_dict():
    code = """def foo():\n    pass\n"""
    report = analyze_code_style(code, "python")
    assert isinstance(report.breakdown, dict)
    assert "naming" in report.breakdown
    assert "structure" in report.breakdown
    assert "formatting" in report.breakdown


def test_style_c_code():
    c_code = """int AddNumbers(int a, int b) {
    return a + b;
}"""
    report = analyze_code_style(c_code, "c")
    assert isinstance(report.style_score, float)
    assert report.style_grade in ("A", "B", "C", "D")


def test_style_java_code():
    java_code = """public class payment_service {
    public int calculate_total(int a, int b) {
        return a + b;
    }
}"""
    report = analyze_code_style(java_code, "java")
    assert isinstance(report.style_score, float)
    # Class name 'payment_service' fails PascalCase
    assert any(i.code == "S202" for i in report.issues)


def test_style_grade_ranges():
    # Clean code should get A
    clean = "def add(a: int, b: int) -> int:\n    return a + b\n"
    r = analyze_code_style(clean, "python")
    assert r.style_grade == "A"
    assert r.style_score >= 85.0
