"""Docstring generation engine supporting both AI (Ollama/LLMs) and offline AST templates."""

import json
from typing import Optional
import httpx

from docudoctor.models import FunctionMeta


def generate_template_docstring(func: FunctionMeta, indent: str = "    ") -> str:
    """Generate a clean Google-style docstring using AST function metadata."""
    # Convert function_name_with_underscores into a readable sentence
    readable_name = func.name.replace("_", " ").strip().capitalize()
    if func.name == "__init__":
        summary = "Initialize a new instance."
    else:
        summary = f"{readable_name}."

    lines = [f'"""{summary}']

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

    # Apply indentation to all lines
    indented = "\n".join(f"{indent}{line}" if line else "" for line in lines)
    return indented


def query_ollama_for_docstring(
    func: FunctionMeta,
    model: str = "llama3:latest",
    ollama_url: str = "http://localhost:11434/api/generate",
    indent: str = "    ",
) -> Optional[str]:
    """Attempt to ask a local Ollama instance to generate a high-quality docstring."""
    prompt = f"""You are a professional Python documentation expert.
Generate ONLY a Google-style Python docstring (enclosed in triple quotes) for the following Python function.
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
            # Clean possible markdown ticks
            if result.startswith("```python"):
                result = result[len("```python"):].strip()
            if result.startswith("```"):
                result = result[3:].strip()
            if result.endswith("```"):
                result = result[:-3].strip()

            if result.startswith('"""') and result.endswith('"""'):
                doc_lines = result.splitlines()
                return "\n".join(f"{indent}{l}" if l else "" for l in doc_lines)
    except Exception:
        # Graceful fallback if Ollama isn't active or times out
        pass

    return None


def generate_docstring(
    func: FunctionMeta,
    use_ai: bool = False,
    ai_model: str = "llama3:latest",
    indent: str = "    ",
) -> str:
    """Entrypoint to generate docstring via AI or fallback template."""
    if use_ai:
        ai_result = query_ollama_for_docstring(func, model=ai_model, indent=indent)
        if ai_result:
            return ai_result

    return generate_template_docstring(func, indent=indent)
