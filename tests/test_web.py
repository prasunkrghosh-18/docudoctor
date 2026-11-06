"""Unit tests for FastAPI web endpoints."""

from docudoctor.web import (
    AuditRequest,
    FixRequest,
    ReportRequest,
    api_audit,
    api_fix,
    api_report,
    index,
)


def test_web_index_loads():
    html = index()
    assert "DocuDoctor" in html
    assert "Multi-Language" in html
    assert "Python" in html
    assert "Java" in html


def test_api_audit_python():
    code = """def greet(name: str) -> str:
    return f"Hello {name}"
"""
    req = AuditRequest(code=code, language="python")
    data = api_audit(req)
    assert "score" in data
    assert "grade" in data
    assert data["total_functions"] == 1
    assert data["typed_returns"] == 1
    assert len(data["issues"]) > 0
    assert "recommendation" in data["issues"][0]


def test_api_audit_c():
    c_code = """
int add(int a, int b) {
    return a + b;
}
"""
    req = AuditRequest(code=c_code, language="c")
    data = api_audit(req)
    assert data["total_functions"] == 1
    assert data["documented_functions"] == 0
    assert data["score"] == 0.0


def test_api_fix_c_endpoint():
    c_code = """
int add(int a, int b) {
    return a + b;
}
"""
    req = FixRequest(code=c_code, language="c")
    data = api_fix(req)
    assert data["patched_count"] == 1
    assert "@brief Add." in data["patched_code"]
    assert "@param a" in data["patched_code"]
    assert "diff" in data


def test_api_fix_java_endpoint():
    java_code = """
public class Calc {
    public int multiply(int x, int y) {
        return x * y;
    }
}
"""
    req = FixRequest(code=java_code, language="java")
    data = api_fix(req)
    assert data["patched_count"] == 2  # class + method
    assert "/**" in data["patched_code"]
    assert "* Calc representation." in data["patched_code"]
    assert "* @param x" in data["patched_code"]


def test_api_fix_python_specific_function():
    code = """def foo():
    return 1

def bar():
    return 2
"""
    req = FixRequest(code=code, language="python", style="google", target="bar")
    data = api_fix(req)
    assert data["patched_count"] >= 1
    assert '"""Bar.' in data["patched_code"]
    assert '"""Foo.' not in data["patched_code"]


def test_api_audit_maintainability_and_complexity():
    code = """def complex_decision(a: int, b: int) -> bool:
    if a > 0 and b > 0:
        for i in range(a):
            if i % 2 == 0:
                return True
    return False
"""
    req = AuditRequest(code=code, language="python")
    data = api_audit(req)
    assert "maintainability_index" in data
    assert "avg_complexity" in data
    assert "maintainability_grade" in data
    assert data["avg_complexity"] > 1.0


def test_api_report_endpoint():
    code = """def hello() -> str:
    return "world"
"""
    req = ReportRequest(code=code, language="python", filename="test.py")
    res = api_report(req)
    assert "report" in res
    assert "# 🩺 DocuDoctor Code Health & Audit Report" in res["report"]
    assert "Executive Summary" in res["report"]
    assert "test.py" in res["report"]


def test_total_healer_mutable_default():
    code = """def add_item(item: str, tags=[]):
    return tags
"""
    req = FixRequest(code=code, language="python")
    data = api_fix(req)
    assert "tags=None" in data["patched_code"]
    assert "if tags is None:" in data["patched_code"]
    assert "tags = []" in data["patched_code"]


def test_total_healer_type_inference():
    code = """def is_active():
    return True
"""
    req = FixRequest(code=code, language="python")
    data = api_fix(req)
    assert "def is_active() -> bool:" in data["patched_code"]
    assert '"""Is active.' in data["patched_code"]

