"""Docstring generation engine supporting Google, NumPy, Sphinx styles and AI."""

from enum import Enum
from typing import Optional
import httpx

from docudoctor.models import FunctionMeta


class DocstringStyle(str, Enum):
    """Supported documentation conventions."""
    GOOGLE = "google"
    NUMPY = "numpy"
    SPHINX = "sphinx"


def _clean_summary(func: FunctionMeta) -> str:
    """Generate a readable summary line for a function."""
    readable_name = func.name.replace("_", " ").strip().capitalize()
    if func.name == "__init__":
        return "Initialize a new instance."
    return f"{readable_name}."


def generate_google_docstring(func: FunctionMeta, indent: str = "    ") -> str:
    """Generate a clean Google-style docstring."""
    lines = [f'"""{_clean_summary(func)}']

    if func.args:
        lines.append("")
        lines.append("Args:")
        for arg in func.args:
            type_str = f" ({arg.type_annotation})" if arg.type_annotation else ""
            default_str = f" Defaults to {arg.default_repr}." if arg.default_repr else ""
            lines.append(f"    {arg.name}{type_str}: The {arg.name.replace('_', ' ')} parameter.{default_str}")

    if func.return_type and func.return_type != "None":
        lines.append("")
        lines.append("Returns:")
        lines.append(f"    {func.return_type}: The result of {func.name.replace('_', ' ')}.")

    lines.append('"""')
    return "\n".join(f"{indent}{line}" if line else "" for line in lines)


def generate_numpy_docstring(func: FunctionMeta, indent: str = "    ") -> str:
    """Generate a clean NumPy-style docstring."""
    lines = [f'"""{_clean_summary(func)}']

    if func.args:
        lines.append("")
        lines.append("Parameters")
        lines.append("----------")
        for arg in func.args:
            type_part = f" : {arg.type_annotation}" if arg.type_annotation else ""
            lines.append(f"{arg.name}{type_part}")
            default_str = f" (default: {arg.default_repr})" if arg.default_repr else ""
            lines.append(f"    The {arg.name.replace('_', ' ')} value.{default_str}")

    if func.return_type and func.return_type != "None":
        lines.append("")
        lines.append("Returns")
        lines.append("-------")
        lines.append(f"{func.return_type}")
        lines.append(f"    The computed {func.name.replace('_', ' ')} result.")

    lines.append('"""')
    return "\n".join(f"{indent}{line}" if line else "" for line in lines)


def generate_sphinx_docstring(func: FunctionMeta, indent: str = "    ") -> str:
    """Generate a clean Sphinx / reStructuredText docstring."""
    lines = [f'"""{_clean_summary(func)}', ""]

    for arg in func.args:
        default_str = f" (default: {arg.default_repr})" if arg.default_repr else ""
        lines.append(f":param {arg.name}: The {arg.name.replace('_', ' ')} parameter.{default_str}")
        if arg.type_annotation:
            lines.append(f":type {arg.name}: {arg.type_annotation}")

    if func.return_type and func.return_type != "None":
        lines.append(f":return: The result of {func.name.replace('_', ' ')}.")
        lines.append(f":rtype: {func.return_type}")

    lines.append('"""')
    return "\n".join(f"{indent}{line}" if line else "" for line in lines)


def query_ollama_for_docstring(
    func: FunctionMeta,
    style: DocstringStyle = DocstringStyle.GOOGLE,
    model: str = "llama3:latest",
    ollama_url: str = "http://localhost:11434/api/generate",
    indent: str = "    ",
) -> Optional[str]:
    """Ask a local Ollama instance to generate a docstring adhering to chosen style."""
    prompt = f"""You are a professional Python documentation expert.
Generate strictly a {style.value.upper()}-style Python docstring (enclosed in triple quotes) for the following Python function.
Do NOT include the function signature, markdown code fences, or any other explanations.
Return strictly the triple-quoted docstring.

Function source code:
{func.raw_source}
"""

    try:
        response = httpx.post(
            ollama_url,
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=8.0,
        )
        if response.status_code == 200:
            result = response.json().get("response", "").strip()
            if result.startswith("```python"):
                result = result[len("```python"):].strip()
            if result.startswith("```"):
                result = result[3:].strip()
            if result.endswith("```"):
                result = result[:-3].strip()

            if result.startswith('"""') and result.endswith('"""'):
                doc_lines = result.splitlines()
                return "\n".join(f"{indent}{line}" if line else "" for line in doc_lines)
    except Exception:
        pass

    return None


def generate_docstring(
    func: FunctionMeta,
    style: DocstringStyle = DocstringStyle.GOOGLE,
    use_ai: bool = False,
    ai_model: str = "llama3:latest",
    indent: str = "    ",
) -> str:
    """Generate docstring using selected style, with optional AI generation."""
    if use_ai:
        ai_result = query_ollama_for_docstring(func, style=style, model=ai_model, indent=indent)
        if ai_result:
            return ai_result

    if style == DocstringStyle.NUMPY:
        return generate_numpy_docstring(func, indent=indent)
    elif style == DocstringStyle.SPHINX:
        return generate_sphinx_docstring(func, indent=indent)
    else:
        return generate_google_docstring(func, indent=indent)
