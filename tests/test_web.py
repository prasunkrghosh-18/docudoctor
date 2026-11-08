"""Unit tests for FastAPI web endpoints."""

from docudoctor.web import (
    AuditRequest,
    ComplexityRequest,
    FixRequest,
    ReportRequest,
    StyleRequest,
    api_audit,
    api_complexity,
    api_fix,
    api_report,
    api_style,
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


def test_theme_switcher_elements():
    html = index()
    assert 'id="themeBtn"' in html
    assert 'id="themeMenu"' in html
    assert 'id="themeOptSystem"' in html
    assert 'id="themeOptDark"' in html
    assert 'id="themeOptLight"' in html
    assert 'docudoctor_theme' in html
    assert 'prefers-color-scheme' in html


def test_api_complexity_python():
    code = """def find_dupes(items):
    result = []
    for i in range(len(items)):
        for j in range(i+1, len(items)):
            if items[i] == items[j]:
                result.append(items[i])
    return result
"""
    req = ComplexityRequest(code=code, language="python")
    data = api_complexity(req)
    assert "overall_time" in data
    assert "overall_space" in data
    assert "overall_risk" in data
    assert "functions" in data
    assert len(data["functions"]) >= 1
    fn = data["functions"][0]
    assert fn["name"] == "find_dupes"
    assert "n²" in fn["time_complexity"] or "n" in fn["time_complexity"]


def test_api_complexity_no_functions():
    code = "x = 1 + 2"
    req = ComplexityRequest(code=code, language="python")
    data = api_complexity(req)
    assert data["overall_time"] == "O(1)"
    assert data["functions"] == []


def test_api_style_clean_code():
    code = """def calculate_total(price: float, tax_rate: float) -> float:
    return round(price * (1.0 + tax_rate), 2)
"""
    req = StyleRequest(code=code, language="python")
    data = api_style(req)
    assert "style_score" in data
    assert "style_grade" in data
    assert "breakdown" in data
    assert "issues" in data
    assert data["style_score"] >= 80.0


def test_api_style_bad_naming():
    code = """def CalculateTotal(price, tax):
    MagicNum = 999
    return price + tax + MagicNum
"""
    req = StyleRequest(code=code, language="python")
    data = api_style(req)
    assert data["style_score"] < 100.0
    assert len(data["issues"]) > 0


def test_ui_has_complexity_and_style_panels():
    html = index()
    assert 'overallTimeBig' in html
    assert 'overallSpaceBig' in html
    assert 'complexityFnList' in html
    assert 'styleScoreVal' in html
    assert 'styleGradeBadge' in html
    assert 'styleScoreBar' in html
    assert 'styleNaming' in html
    assert 'styleStructure' in html
    assert 'styleIssueList' in html
    assert '/api/complexity' in html
    assert '/api/style' in html


def test_ui_tabbed_studio_inspector():
    html = index()
    assert 'tabBtnIssues' in html
    assert 'tabBtnComplexity' in html
    assert 'tabBtnStyle' in html
    assert 'tabBtnMetrics' in html
    assert 'tabPaneIssues' in html
    assert 'tabPaneComplexity' in html
    assert 'tabPaneStyle' in html
    assert 'tabPaneMetrics' in html
    assert 'switchRightTab' in html
    assert 'statFuncsQuick' in html
    assert 'statMiQuick' in html
    assert 'statComplexityQuick' in html
    assert 'statStyleQuick' in html


def test_ui_welcome_intro_overlay():
    """Verify cinematic welcome intro overlay, quantum audio engine, and studio transition."""
    html = index()
    assert 'welcomeIntroOverlay' in html
    assert 'Welcome to DocuDoctor' in html
    assert 'dismissWelcomeIntro' in html
    assert 'initWelcomeAnimation' in html
    assert "onLanguageChange('python', false)" in html
    assert 'mainWorkspaceApp' in html
    assert 'studio-revealed' in html
    assert 'welcome-exit-warp' in html
    assert 'codeEditorPanel' in html
    assert 'editor-scanline-active' in html
    assert 'playCinematicSweep' in html
    assert 'playQuantumChime' in html
    assert 'playSciFiTick' in html
    assert 'sfxToggleBtn' not in html
    assert 'DIAGNOSTICS' not in html
    assert 'CLICK ANYWHERE TO SKIP' not in html
    assert 'onclick="dismissWelcomeIntro()"' not in html

    # Verify no language chips or SFX controls in welcome overlay
    overlay_html = html.split('id="welcomeIntroOverlay"')[1].split('<!-- ════════════════════════ MAIN WORKSPACE WRAPPER')[0]
    assert '🐍 Python' not in overlay_html
    assert '⚡ C / C++' not in overlay_html
    assert '☕ Java' not in overlay_html
    assert '🧠 Gemini AI' not in overlay_html
    assert 'sfxToggleBtn' not in overlay_html
    assert 'DIAGNOSTICS' not in overlay_html





