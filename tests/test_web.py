"""Unit tests for FastAPI web endpoints."""

from fastapi.testclient import TestClient
from docudoctor.web import app

client = TestClient(app)


def test_web_index_loads():
    response = client.get("/")
    assert response.status_code == 200
    assert "DocuDoctor" in response.text
    assert "AST Code Health & Docstring Engine" in response.text


def test_api_audit_endpoint():
    code = """def greet(name: str) -> str:
    return f"Hello {name}"
"""
    response = client.post("/api/audit", json={"code": code})
    assert response.status_code == 200
    data = response.json()
    assert "score" in data
    assert "grade" in data
    assert data["total_functions"] == 1
    assert data["typed_returns"] == 1


def test_api_fix_endpoint():
    code = """def multiply(a: float, b: float) -> float:
    return a * b
"""
    response = client.post("/api/fix", json={"code": code, "style": "google"})
    assert response.status_code == 200
    data = response.json()
    assert data["patched_count"] == 1
    assert '"""Multiply.' in data["patched_code"]
    assert "diff" in data
