"""Unit tests for the Super Smart AI Engine and Hybrid AST Guardrails."""

import pytest
from docudoctor.ai_engine import (
    format_docstring_from_ai_data,
    get_effective_api_key,
    patch_code_with_smart_ai,
    ai_deep_code_review,
)
from docudoctor.web import (
    AIReviewRequest,
    FixRequest,
    api_ai_review,
    api_fix,
    index,
)


def test_format_docstring_ast_guardrails():
    """Verify that hallucinated parameters from AI are strictly stripped by AST guardrails."""
    ai_data = {
        "summary": "Computes weighted subtotal for order items.",
        "extended": "Multiplies items by regional tax rate and handles exempt lines.",
        "parameters": {
            "items": "List of floating point item prices.",
            "tax_rate": "Effective local sales tax percentage.",
            "fake_hallucinated_param": "This should NEVER appear in the output docstring!",
        },
        "returns": "Total gross amount payable.",
        "raises": ["ValueError: if tax_rate < 0"],
    }

    real_args = ["items", "tax_rate"]
    google_doc = format_docstring_from_ai_data(ai_data, real_args, style="google")
    assert "fake_hallucinated_param" not in google_doc
    assert "items: List of floating point item prices." in google_doc
    assert "tax_rate: Effective local sales tax percentage." in google_doc
    assert "Computes weighted subtotal for order items." in google_doc
    assert "Raises:" in google_doc

    numpy_doc = format_docstring_from_ai_data(ai_data, real_args, style="numpy")
    assert "fake_hallucinated_param" not in numpy_doc
    assert "Parameters" in numpy_doc
    assert "tax_rate" in numpy_doc

    sphinx_doc = format_docstring_from_ai_data(ai_data, real_args, style="sphinx")
    assert "fake_hallucinated_param" not in sphinx_doc
    assert ":param items:" in sphinx_doc

    doxygen_doc = format_docstring_from_ai_data(ai_data, real_args, style="doxygen")
    assert "fake_hallucinated_param" not in doxygen_doc
    assert "@param tax_rate" in doxygen_doc

    javadoc_doc = format_docstring_from_ai_data(ai_data, real_args, style="javadoc")
    assert "fake_hallucinated_param" not in javadoc_doc
    assert "* @param items" in javadoc_doc


def test_smart_patching_without_api_key_gracefully_falls_back():
    """When no API key is provided, system synthesizes with Gemini Flash Engine."""
    code = """def add_tags(item: str, tags=[]):
    return tags
"""
    patched, count, msg = patch_code_with_smart_ai(code, language="python", api_key=None)
    assert count >= 1
    # Total healer still fixed the mutable default
    assert "tags=None" in patched
    assert "Gemini Flash Engine" in msg


def test_ai_deep_code_review_without_key():
    """Review returns intelligent semantic review without blocking static error."""
    code = "def foo(): return 42"
    result = ai_deep_code_review(code, language="python", api_key=None)
    assert result["available"] is True
    assert "overall_assessment" in result
    assert len(result["best_practices"]) > 0


def test_web_api_ai_review_endpoint():
    """Test POST /api/ai-review endpoint."""
    code = "def calculate_discount(price: float) -> float:\n    return price * 0.9"
    req = AIReviewRequest(code=code, language="python", api_key=None)
    res = api_ai_review(req)
    assert "available" in res
    assert "overall_assessment" in res


def test_web_api_fix_with_use_ai_flag():
    """Test POST /api/fix with use_ai flag."""
    code = "def multiply(a: int, b: int) -> int:\n    return a * b"
    req = FixRequest(code=code, language="python", use_ai=True, api_key=None)
    res = api_fix(req)
    assert "patched_code" in res
    assert "message" in res


def test_ui_has_super_smart_ai_elements():
    """Verify Gemini AI elements and review studio are present in the UI."""
    html = index()
    assert "tabBtnAiReview" in html
    assert "tabPaneAiReview" in html
    assert "runAiReviewBtn" in html
    assert "/api/ai-review" in html


def test_generate_smart_local_review_detects_nested_loops_and_mutable_defaults():
    """Verify that local AST review identifies O(n^2) loops and mutable defaults."""
    from docudoctor.ai_engine import generate_smart_local_review

    code = """def bad_perf(items, cache=[]):
    for a in items:
        for b in items:
            pass
    return cache
"""
    res = generate_smart_local_review(code, language="python")
    assert res["available"] is True
    assert "DocuDoctor Smart Semantic Engine" in res["model_used"]
    assert any("O(n²)" in opt["title"] for opt in res["optimizations"])
    assert any("Mutable Default" in bug["title"] for bug in res["bug_risks"])
    assert res["cleanliness_score"] > 0


def test_get_effective_api_key_cleans_quotes_and_whitespace():
    """Verify quotes and whitespace from cloud dashboard environment variables are cleaned."""
    assert get_effective_api_key(' "AIzaSyTestKey123" ') == "AIzaSyTestKey123"
    assert get_effective_api_key(" 'AIzaSyTestKey456' ") == "AIzaSyTestKey456"


