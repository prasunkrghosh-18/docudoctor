"""AST-based code visitor and repository scanner for Python documentation."""

import ast
from pathlib import Path
from typing import List, Optional, Tuple

from docudoctor.models import (
    ClassMeta,
    CodeIssue,
    FileReport,
    FunctionArg,
    FunctionMeta,
    IssueType,
    ProjectReport,
    Severity,
)


class CodeAnalysisVisitor(ast.NodeVisitor):
    """Walks the Python AST to analyze docstrings, type annotations, and function signatures."""

    def __init__(self, file_path: Path, source_code: str):
        self.file_path = file_path
        self.source_code = source_code
        self.source_lines = source_code.splitlines()

        self.functions: List[FunctionMeta] = []
        self.classes: List[ClassMeta] = []
        self.issues: List[CodeIssue] = []

        self._current_class: Optional[str] = None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        docstring = ast.get_docstring(node)
        class_meta = ClassMeta(
            name=node.name,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            docstring=docstring,
        )
        self.classes.append(class_meta)

        if not docstring or not docstring.strip():
            self.issues.append(
                CodeIssue(
                    file_path=self.file_path,
                    line_no=node.lineno,
                    col_offset=node.col_offset,
                    entity_name=node.name,
                    entity_type="class",
                    issue_type=IssueType.MISSING_DOCSTRING,
                    message=f"Class '{node.name}' has no docstring.",
                    severity=Severity.ERROR,
                )
            )

        # Track class context for methods
        previous_class = self._current_class
        self._current_class = node.name
        self.generic_visit(node)
        self._current_class = previous_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._process_function(node, is_async=False)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._process_function(node, is_async=True)
        self.generic_visit(node)

    def _process_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_async: bool
    ) -> None:
        is_method = self._current_class is not None
        docstring = ast.get_docstring(node)

        # Skip private/internal magic methods other than __init__
        if node.name.startswith("__") and node.name.endswith("__") and node.name != "__init__":
            return

        # 1. Inspect Arguments and annotations
        args_list: List[FunctionArg] = []
        has_mutable_default = False

        # Match defaults from the right
        defaults_offset = len(node.args.args) - len(node.args.defaults)

        for idx, arg in enumerate(node.args.args):
            if is_method and idx == 0 and arg.arg in ("self", "cls"):
                continue  # Skip receiver arg

            annotation_str = ast.unparse(arg.annotation) if arg.annotation else None

            default_val = None
            if idx >= defaults_offset:
                def_node = node.args.defaults[idx - defaults_offset]
                default_val = ast.unparse(def_node)
                if isinstance(def_node, (ast.List, ast.Dict, ast.Set)):
                    has_mutable_default = True
                    self.issues.append(
                        CodeIssue(
                            file_path=self.file_path,
                            line_no=def_node.lineno,
                            col_offset=def_node.col_offset,
                            entity_name=node.name,
                            entity_type="method" if is_method else "function",
                            issue_type=IssueType.MUTABLE_DEFAULT_ARG,
                            message=f"Argument '{arg.arg}' has dangerous mutable default '{default_val}'.",
                            severity=Severity.WARNING,
                        )
                    )

            if not annotation_str:
                self.issues.append(
                    CodeIssue(
                        file_path=self.file_path,
                        line_no=arg.lineno,
                        col_offset=arg.col_offset,
                        entity_name=node.name,
                        entity_type="method" if is_method else "function",
                        issue_type=IssueType.MISSING_ARG_TYPE,
                        message=f"Parameter '{arg.arg}' in '{node.name}' lacks a type annotation.",
                        severity=Severity.INFO,
                    )
                )

            args_list.append(
                FunctionArg(
                    name=arg.arg,
                    type_annotation=annotation_str,
                    default_repr=default_val,
                )
            )

        # 2. Inspect Return Type
        return_type_str = ast.unparse(node.returns) if node.returns else None
        if not return_type_str and node.name != "__init__":
            self.issues.append(
                CodeIssue(
                    file_path=self.file_path,
                    line_no=node.lineno,
                    col_offset=node.col_offset,
                    entity_name=node.name,
                    entity_type="method" if is_method else "function",
                    issue_type=IssueType.MISSING_RETURN_TYPE,
                    message=f"Function '{node.name}' has no return type annotation.",
                    severity=Severity.WARNING,
                )
            )

        # 3. Inspect Docstring
        if not docstring or not docstring.strip():
            severity = Severity.ERROR if not node.name.startswith("_") else Severity.INFO
            self.issues.append(
                CodeIssue(
                    file_path=self.file_path,
                    line_no=node.lineno,
                    col_offset=node.col_offset,
                    entity_name=node.name,
                    entity_type="method" if is_method else "function",
                    issue_type=IssueType.MISSING_DOCSTRING,
                    message=f"{'Method' if is_method else 'Function'} '{node.name}' has no docstring.",
                    severity=severity,
                )
            )

        # Extract Raw Source Slice
        start_line = node.lineno - 1
        end_line = node.end_lineno or node.lineno
        raw_source = "\n".join(self.source_lines[start_line:end_line])

        self.functions.append(
            FunctionMeta(
                name=node.name,
                line_start=node.lineno,
                line_end=end_line,
                is_async=is_async,
                is_method=is_method,
                docstring=docstring,
                args=args_list,
                return_type=return_type_str,
                raw_source=raw_source,
                has_mutable_default=has_mutable_default,
            )
        )


def scan_file(file_path: Path) -> Tuple[FileReport, List[FunctionMeta]]:
    """Scan an individual Python file and return its health report and metadata."""
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
    except (SyntaxError, UnicodeDecodeError) as e:
        report = FileReport(
            file_path=file_path,
            issues=[
                CodeIssue(
                    file_path=file_path,
                    line_no=getattr(e, "lineno", 1) or 1,
                    col_offset=getattr(e, "offset", 0) or 0,
                    entity_name="<file>",
                    entity_type="file",
                    issue_type=IssueType.MISSING_DOCSTRING,
                    message=f"Failed to parse Python syntax: {e}",
                    severity=Severity.ERROR,
                )
            ],
        )
        return report, []

    visitor = CodeAnalysisVisitor(file_path, source)
    visitor.visit(tree)

    documented_funcs = sum(1 for f in visitor.functions if f.docstring and f.docstring.strip())
    documented_classes = sum(1 for c in visitor.classes if c.docstring and c.docstring.strip())
    typed_returns = sum(1 for f in visitor.functions if f.return_type)

    report = FileReport(
        file_path=file_path,
        total_functions=len(visitor.functions),
        total_classes=len(visitor.classes),
        documented_functions=documented_funcs,
        documented_classes=documented_classes,
        typed_returns=typed_returns,
        issues=visitor.issues,
    )
    return report, visitor.functions


def scan_path(target_path: Path) -> Tuple[ProjectReport, List[Tuple[Path, List[FunctionMeta]]]]:
    """Scan a directory or file and aggregate the full project report."""
    target = target_path.resolve()
    py_files: List[Path] = []

    if target.is_file() and target.suffix == ".py":
        py_files.append(target)
    elif target.is_dir():
        # Exclude hidden directories, virtual environments, build artifacts
        for p in target.rglob("*.py"):
            parts = p.parts
            if any(part.startswith(".") or part in ("venv", "env", "build", "dist", "__pycache__") for part in parts):
                continue
            py_files.append(p)

    file_reports: List[FileReport] = []
    functions_map: List[Tuple[Path, List[FunctionMeta]]] = []

    for file_p in py_files:
        report, funcs = scan_file(file_p)
        file_reports.append(report)
        functions_map.append((file_p, funcs))

    return ProjectReport(file_reports=file_reports), functions_map
