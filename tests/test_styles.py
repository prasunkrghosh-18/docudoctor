"""Unit tests for multi-style docstring generation (Google, NumPy, Sphinx)."""

from docudoctor.doctor.generator import (
    DocstringStyle,
    generate_docstring,
    generate_google_docstring,
    generate_numpy_docstring,
    generate_sphinx_docstring,
)
from docudoctor.models import FunctionArg, FunctionMeta


def _create_dummy_func() -> FunctionMeta:
    return FunctionMeta(
        name="calculate_tax",
        line_start=1,
        line_end=5,
        is_async=False,
        is_method=False,
        docstring=None,
        args=[
            FunctionArg(name="amount", type_annotation="float"),
            FunctionArg(name="rate", type_annotation="float", default_repr="0.05"),
        ],
        return_type="float",
        raw_source="def calculate_tax(amount: float, rate: float = 0.05) -> float:\n    return amount * rate\n",
    )


def test_google_style_format():
    func = _create_dummy_func()
    doc = generate_google_docstring(func)
    assert '"""Calculate tax.' in doc
    assert "Args:" in doc
    assert "amount (float):" in doc
    assert "rate (float):" in doc
    assert "Defaults to 0.05." in doc
    assert "Returns:" in doc
    assert "float: The result of calculate tax." in doc


def test_numpy_style_format():
    func = _create_dummy_func()
    doc = generate_numpy_docstring(func)
    assert '"""Calculate tax.' in doc
    assert "Parameters" in doc
    assert "----------" in doc
    assert "amount : float" in doc
    assert "rate : float" in doc
    assert "default: 0.05" in doc
    assert "Returns" in doc
    assert "-------" in doc
    assert "float" in doc


def test_sphinx_style_format():
    func = _create_dummy_func()
    doc = generate_sphinx_docstring(func)
    assert '"""Calculate tax.' in doc
    assert ":param amount:" in doc
    assert ":type amount: float" in doc
    assert ":param rate:" in doc
    assert "(default: 0.05)" in doc
    assert ":return:" in doc
    assert ":rtype: float" in doc


def test_generate_docstring_style_selector():
    func = _create_dummy_func()
    numpy_doc = generate_docstring(func, style=DocstringStyle.NUMPY)
    assert "Parameters" in numpy_doc

    sphinx_doc = generate_docstring(func, style=DocstringStyle.SPHINX)
    assert ":param amount:" in sphinx_doc
