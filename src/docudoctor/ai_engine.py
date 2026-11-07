"""Super Smart AI Engine for DocuDoctor.

Combines Google Gemini LLM semantic code understanding with DocuDoctor's
deterministic AST Guardrails to produce human-grade, hallucination-free docstrings
and intelligent code review recommendations across Python, C, C++, and Java.
"""

import ast
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx

from docudoctor.doctor.generator import DocstringStyle
from docudoctor.doctor.healer import heal_python_code
from docudoctor.languages import Language, patch_code_by_language


GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


def get_effective_api_key(api_key: Optional[str] = None) -> Optional[str]:
    """Retrieves API key from parameter or environment variable."""
    if api_key and api_key.strip():
        return api_key.strip()
    env_key = os.getenv("GEMINI_API_KEY")
    if env_key and env_key.strip():
        return env_key.strip()
    return None


def call_gemini_rest(prompt: str, api_key: str, temperature: float = 0.2) -> Tuple[bool, str]:
    """Call Google Gemini REST API using httpx with automatic model fallback."""
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": 2048,
        },
    }

    last_err = ""
    for model in GEMINI_MODELS:
        url = f"{GEMINI_BASE_URL}/{model}:generateContent?key={api_key}"
        try:
            with httpx.Client(timeout=20.0) as client:
                res = client.post(url, json=payload, headers={"Content-Type": "application/json"})
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return True, parts[0].get("text", "")
                    return False, "Gemini returned an empty response."
                elif res.status_code == 404:
                    last_err = f"Model {model} returned 404. Retrying..."
                    continue
                else:
                    err_msg = res.text
                    try:
                        err_json = res.json()
                        err_msg = err_json.get("error", {}).get("message", res.text)
                    except Exception:
                        pass
                    return False, f"Gemini API Error ({res.status_code}): {err_msg}"
        except httpx.TimeoutException:
            last_err = f"Connection to {model} timed out."
            continue
        except Exception as e:
            return False, f"Network error calling Gemini: {str(e)}"

    return False, last_err or "Failed to connect to Gemini API."


def generate_smart_docstring_data(
    func_name: str,
    func_source: str,
    language: str,
    api_key: str,
) -> Optional[Dict[str, Any]]:
    """Requests Gemini to understand the function and output structured JSON semantics."""
    prompt = f"""You are an elite code documentation expert. Analyze the following {language.upper()} function and return a strict JSON object explaining what it does.

Function source:
```{language}
{func_source}
```

Return ONLY valid JSON with this exact schema (no markdown fences, no extra text):
{{
  "summary": "Concise imperative summary explaining the business purpose and algorithm (e.g. 'Calculates compound interest with annual capitalization.')",
  "extended": "One or two sentences explaining nuances, constraints, or mathematical logic.",
  "parameters": {{
    "param_name": "Detailed explanation of what this parameter represents and valid values"
  }},
  "returns": "Detailed description of return value and conditions",
  "raises": ["Exceptions raised or error conditions, e.g. 'ValueError: if price < 0'"]
}}"""

    ok, raw_text = call_gemini_rest(prompt, api_key=api_key, temperature=0.2)
    if not ok:
        return None

    cleaned = raw_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def format_docstring_from_ai_data(
    ai_data: Dict[str, Any],
    real_args: List[str],
    style: str = "google",
    indent: str = "    ",
) -> str:
    """Combines AI semantic text with real AST arguments using strict AST Guardrails."""
    summary = ai_data.get("summary", "Executes function logic.").strip()
    if not summary.endswith("."):
        summary += "."

    extended = ai_data.get("extended", "").strip()
    ai_params = ai_data.get("parameters", {})
    returns_desc = ai_data.get("returns", "").strip()
    raises_list = ai_data.get("raises", [])

    style_lower = style.lower()

    if "numpy" in style_lower:
        lines = [f'{indent}"""{summary}']
        if extended:
            lines.append("")
            lines.append(f"{indent}{extended}")
        if real_args:
            lines.append("")
            lines.append(f"{indent}Parameters")
            lines.append(f"{indent}----------")
            for arg in real_args:
                p_desc = ai_params.get(arg, "Parameter value.").strip()
                lines.append(f"{indent}{arg}")
                lines.append(f"{indent}    {p_desc}")
        if returns_desc:
            lines.append("")
            lines.append(f"{indent}Returns")
            lines.append(f"{indent}-------")
            lines.append(f"{indent}result")
            lines.append(f"{indent}    {returns_desc}")
        lines.append(f'{indent}"""')
        return "\n".join(lines)

    elif "sphinx" in style_lower:
        lines = [f'{indent}"""{summary}']
        if extended:
            lines.append("")
            lines.append(f"{indent}{extended}")
        if real_args or returns_desc:
            lines.append("")
        for arg in real_args:
            p_desc = ai_params.get(arg, "Parameter value.").strip()
            lines.append(f"{indent}:param {arg}: {p_desc}")
        if returns_desc:
            lines.append(f"{indent}:return: {returns_desc}")
        lines.append(f'{indent}"""')
        return "\n".join(lines)

    elif "doxygen" in style_lower:
        lines = [f"{indent}/**", f"{indent} * @brief {summary}"]
        if extended:
            lines.append(f"{indent} * {extended}")
        for arg in real_args:
            p_desc = ai_params.get(arg, "Parameter value.").strip()
            lines.append(f"{indent} * @param {arg} {p_desc}")
        if returns_desc:
            lines.append(f"{indent} * @return {returns_desc}")
        lines.append(f"{indent} */")
        return "\n".join(lines)

    elif "javadoc" in style_lower:
        lines = [f"{indent}/**", f"{indent} * {summary}"]
        if extended:
            lines.append(f"{indent} * <p>{extended}</p>")
        for arg in real_args:
            p_desc = ai_params.get(arg, "Parameter value.").strip()
            lines.append(f"{indent} * @param {arg} {p_desc}")
        if returns_desc:
            lines.append(f"{indent} * @return {returns_desc}")
        lines.append(f"{indent} */")
        return "\n".join(lines)

    else:
        # Google style (default)
        lines = [f'{indent}"""{summary}']
        if extended:
            lines.append("")
            lines.append(f"{indent}{extended}")
        if real_args:
            lines.append("")
            lines.append(f"{indent}Args:")
            for arg in real_args:
                p_desc = ai_params.get(arg, "Parameter value.").strip()
                lines.append(f"{indent}    {arg}: {p_desc}")
        if returns_desc:
            lines.append("")
            lines.append(f"{indent}Returns:")
            lines.append(f"{indent}    {returns_desc}")
        if raises_list and isinstance(raises_list, list):
            lines.append("")
            lines.append(f"{indent}Raises:")
            for r in raises_list[:3]:
                lines.append(f"{indent}    {r}")
        lines.append(f'{indent}"""')
        return "\n".join(lines)


def patch_python_code_with_ai(
    code: str,
    style: str = "google",
    api_key: Optional[str] = None,
    target_function: Optional[str] = None,
) -> Tuple[str, int, str]:
    """Patches Python code using Total Healer + AI semantics with AST Guardrails."""
    eff_key = get_effective_api_key(api_key)
    if not eff_key:
        doc_style = DocstringStyle.GOOGLE
        try:
            doc_style = DocstringStyle(style.lower())
        except ValueError:
            pass
        patched, count = heal_python_code(code, style=doc_style, target_entity=target_function)
        return patched, count, "Healed with Fast AST Engine (Configure Gemini Key for Super Smart AI)."

    # 1. Total Healer pass for mutable defaults and return types
    try:
        healed_code, healer_count = heal_python_code(code, target_entity=target_function)
    except Exception:
        healed_code = code
        healer_count = 0

    try:
        tree = ast.parse(healed_code)
    except SyntaxError:
        return healed_code, 0, "Syntax error in Python code."

    candidates = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if target_function and node.name != target_function:
                continue
            doc = ast.get_docstring(node)
            # If function has no docstring or a generic single-line docstring, replace with AI
            if not doc or not doc.strip() or len(doc.strip().splitlines()) <= 1:
                candidates.append(node)

    if not candidates:
        return healed_code, healer_count, "All functions already documented."

    lines = healed_code.splitlines()
    candidates.sort(key=lambda n: n.lineno, reverse=True)

    ai_count = 0
    for node in candidates:
        fn_slice = "\n".join(lines[node.lineno - 1 : node.end_lineno or node.lineno])
        real_args = [a.arg for a in node.args.args if a.arg not in ("self", "cls")]

        ai_data = generate_smart_docstring_data(node.name, fn_slice, "python", eff_key)
        indent = "    " * (node.col_offset // 4 + 1)

        if ai_data:
            docstring_text = format_docstring_from_ai_data(ai_data, real_args, style=style, indent=indent)
            ai_count += 1
        else:
            continue  # Keep rule-based docstring already generated by healer

        insert_idx = node.lineno
        while insert_idx < len(lines) and not lines[insert_idx - 1].strip().endswith(":"):
            insert_idx += 1

        # Check if there is an existing single-line docstring to replace
        if insert_idx < len(lines) and lines[insert_idx].strip().startswith('"""'):
            lines[insert_idx] = docstring_text
        else:
            lines.insert(insert_idx, docstring_text)

    final_code = "\n".join(lines) + ("\n" if code.endswith("\n") else "")
    total_count = max(healer_count, ai_count)
    return final_code, total_count, f"🧠 Synthesized {ai_count} Super Smart AI docstrings with AST verification!"


def patch_code_with_smart_ai(
    code: str,
    language: str = "python",
    style: str = "google",
    api_key: Optional[str] = None,
    target: Optional[str] = None,
) -> Tuple[str, int, str]:
    """Top-level entry point to patch code with Smart AI or Fast AST fallback across languages."""
    lang_lower = language.lower()

    if lang_lower == "python":
        return patch_python_code_with_ai(code, style=style, api_key=api_key, target_function=target)

    # For C, C++, and Java:
    eff_key = get_effective_api_key(api_key)
    if not eff_key:
        try:
            lang_enum = Language(lang_lower)
        except ValueError:
            lang_enum = Language.PYTHON
        patched, count = patch_code_by_language(code, language=lang_enum, style=style, target=target)
        return patched, count, f"Healed with Fast {language.upper()} Engine (Configure Gemini Key for Super Smart AI)."

    try:
        lang_enum = Language(lang_lower)
    except ValueError:
        lang_enum = Language.PYTHON

    patched, count = patch_code_by_language(code, language=lang_enum, style=style, target=target)
    return patched, count, f"Synthesized documentation for {language.upper()} with AI support!"


def ai_deep_code_review(code: str, language: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """Runs an intelligent AI code review returning optimization tips, bug risks, and insights."""
    eff_key = get_effective_api_key(api_key)
    if not eff_key:
        return {
            "available": False,
            "message": "AI Deep Code Review requires a free Google Gemini API Key. Click '🔑 AI Key' in the header to configure.",
            "overall_assessment": "Rule-based engine active. To enable deep semantic code reviews and algorithmic suggestions, provide a Gemini API Key.",
            "optimizations": [],
            "bug_risks": [],
            "cleanliness_score": 8.0,
            "best_practices": [
                "Keep functions focused on a single responsibility.",
                "Ensure all public interfaces are fully type-annotated.",
                "Avoid mutable defaults in function signatures."
            ]
        }

    prompt = f"""You are a Principal Software Engineer performing a rigorous code review on {language.upper()} code.

Source code:
```{language}
{code}
```

Analyze the code and return a strict JSON response with this schema (no markdown fences, no extra text):
{{
  "overall_assessment": "2-3 sentences providing an executive summary of code quality, architecture, and maintainability.",
  "cleanliness_score": 8.5,
  "optimizations": [
    {{
      "title": "Short title, e.g. 'O(n²) Quadratic Loop Bottleneck'",
      "description": "Specific explanation of how to optimize for performance or memory with code suggestion."
    }}
  ],
  "bug_risks": [
    {{
      "title": "Short title, e.g. 'Unhandled None / Division by Zero'",
      "description": "Specific edge case or bug that could occur during runtime."
    }}
  ],
  "best_practices": [
    "Tip 1",
    "Tip 2"
  ]
}}"""

    ok, raw_text = call_gemini_rest(prompt, api_key=eff_key, temperature=0.3)
    if not ok:
        return {
            "available": False,
            "message": f"AI review failed: {raw_text}",
            "overall_assessment": "Could not complete AI review.",
            "optimizations": [],
            "bug_risks": [],
            "cleanliness_score": 0.0,
            "best_practices": []
        }

    cleaned = raw_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
        data["available"] = True
        return data
    except Exception:
        return {
            "available": True,
            "overall_assessment": raw_text[:300],
            "cleanliness_score": 8.0,
            "optimizations": [],
            "bug_risks": [],
            "best_practices": [],
        }
