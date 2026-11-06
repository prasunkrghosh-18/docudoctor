"""Total Healer engine: AST-level repair for docstrings, mutable defaults, and type hints."""

import ast
import re
from typing import List, Optional, Set, Tuple

from docudoctor.doctor.generator import DocstringStyle, generate_docstring
from docudoctor.doctor.patcher import _detect_body_indent, _find_header_end_line


def infer_return_type(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> Optional[str]:
    """Analyze return statements in function body to infer standard type annotation."""
    if func_node.returns is not None:
        return None  # Already has annotation

    if func_node.name == "__init__":
        return "None"

    return_types: Set[str] = set()

    # Collect return nodes that directly belong to this function (not inner functions)
    for node in func_node.body:
        for sub in ast.walk(node):
            if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                break  # Don't traverse nested functions
            if isinstance(sub, ast.Return):
                if sub.value is None:
                    return_types.add("None")
                elif isinstance(sub.value, ast.Constant):
                    val = sub.value.value
                    if isinstance(val, bool):
                        return_types.add("bool")
                    elif isinstance(val, int):
                        return_types.add("int")
                    elif isinstance(val, float):
                        return_types.add("float")
                    elif isinstance(val, str):
                        return_types.add("str")
                    elif val is None:
                        return_types.add("None")
                elif isinstance(sub.value, ast.Dict):
                    return_types.add("dict")
                elif isinstance(sub.value, ast.List):
                    return_types.add("list")
                elif isinstance(sub.value, ast.Set):
                    return_types.add("set")
                elif isinstance(sub.value, ast.Tuple):
                    return_types.add("tuple")
                elif isinstance(sub.value, ast.Call):
                    func_id = getattr(sub.value.func, "id", "")
                    if func_id in ("int", "str", "float", "bool", "list", "dict", "set", "tuple"):
                        return_types.add(func_id)
                    elif func_id == "len":
                        return_types.add("int")
                    elif func_id == "round":
                        return_types.add("float")

    if len(return_types) == 1:
        return next(iter(return_types))
    return None


def heal_python_code(
    code: str,
    style: DocstringStyle = DocstringStyle.GOOGLE,
    target_entity: Optional[str] = None,
    gemini_api_key: Optional[str] = None,
) -> Tuple[str, int]:
    """
    Comprehensive healing pass on Python code:
    1. Replaces dangerous mutable defaults (e.g. tags=[]) with None and body initialization.
    2. Infers and injects return type hints (e.g. -> bool, -> dict).
    3. Generates and injects missing docstrings.
    """
    try:
        tree = ast.parse(code)
    except Exception:
        # If syntax error, return unchanged
        return code, 0

    lines = code.splitlines()
    patches_applied = 0

    # Collect function nodes
    functions: List[ast.FunctionDef | ast.AsyncFunctionDef] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if target_entity and node.name != target_entity:
                continue
            functions.append(node)

    # Sort in reverse order by line so earlier line edits don't offset later line numbers
    functions.sort(key=lambda n: n.lineno, reverse=True)

    for func_node in functions:
        def_start_idx = func_node.lineno - 1
        if def_start_idx >= len(lines):
            continue

        header_end_idx = _find_header_end_line(lines, def_start_idx)
        indent = _detect_body_indent(lines, header_end_idx)

        # 1. Detect Mutable Defaults
        defaults_offset = len(func_node.args.args) - len(func_node.args.defaults)
        mutable_inits: List[str] = []

        for idx, arg in enumerate(func_node.args.args):
            if idx >= defaults_offset:
                def_node = func_node.args.defaults[idx - defaults_offset]
                if isinstance(def_node, (ast.List, ast.Dict, ast.Set)):
                    init_val = "[]" if isinstance(def_node, ast.List) else ("{}" if isinstance(def_node, ast.Dict) else "set()")
                    mutable_inits.append(f"{indent}if {arg.arg} is None:\n{indent}    {arg.arg} = {init_val}")

                    # Replace '= []' or '= {}' with '= None' in definition header
                    header_line = lines[def_start_idx]
                    pattern = rf"({arg.arg}\s*=\s*)(\[[^\]]*\]|\{{[^\}}]*\}}|set\(\))"
                    if re.search(pattern, header_line):
                        lines[def_start_idx] = re.sub(pattern, rf"\g<1>None", header_line)
                        patches_applied += 1

        # 2. Infer Return Type Hint
        inferred_return = infer_return_type(func_node)
        if inferred_return and func_node.returns is None:
            # Add ' -> <type>' before the trailing ':'
            header_end_line = lines[header_end_idx]
            colon_match = re.search(r":\s*$", header_end_line)
            if colon_match:
                lines[header_end_idx] = header_end_line[:colon_match.start()] + f" -> {inferred_return}:"
                patches_applied += 1

        # 3. Inject Missing Docstring
        existing_doc = ast.get_docstring(func_node)
        insert_lines: List[str] = []

        if not existing_doc or not existing_doc.strip():
            # Build FunctionMeta-like mock for generator
            from docudoctor.models import FunctionArg, FunctionMeta
            args_meta = [
                FunctionArg(
                    name=a.arg,
                    type_annotation=ast.unparse(a.annotation) if a.annotation else None,
                    default_repr="None" if any(a.arg in init for init in mutable_inits) else (ast.unparse(func_node.args.defaults[i - defaults_offset]) if i >= defaults_offset else None)
                )
                for i, a in enumerate(func_node.args.args)
                if not (a.arg in ("self", "cls") and i == 0)
            ]
            func_meta = FunctionMeta(
                name=func_node.name,
                line_start=func_node.lineno,
                line_end=func_node.end_lineno or func_node.lineno,
                is_async=isinstance(func_node, ast.AsyncFunctionDef),
                is_method=False,
                docstring=None,
                args=args_meta,
                return_type=inferred_return or (ast.unparse(func_node.returns) if func_node.returns else None),
                raw_source="",
            )

            doc_text = generate_docstring(func_meta, style=style, indent=indent)
            insert_lines.extend(doc_text.splitlines())
            patches_applied += 1

        # Add any mutable default initializations
        if mutable_inits:
            for init_code in mutable_inits:
                insert_lines.extend(init_code.splitlines())

        if insert_lines:
            lines = lines[:header_end_idx + 1] + insert_lines + lines[header_end_idx + 1:]

    patched_code = "\n".join(lines) + ("\n" if code.endswith("\n") else "")
    return patched_code, patches_applied
