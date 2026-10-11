"""Data models representing AST analysis, issues, and health scores."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional


class Severity(str, Enum):
    """Severity of a detected code documentation issue."""
    ERROR = "ERROR"      # Critical: public API completely undocumented
    WARNING = "WARNING"  # Moderate: missing type hints or out-of-sync parameters
    INFO = "INFO"        # Minor: style suggestions or private helpers


class IssueType(str, Enum):
    """Categorized code issues detected by AST visitor."""
    MISSING_DOCSTRING = "Missing Docstring"
    MISSING_RETURN_TYPE = "Missing Return Type"
    MISSING_ARG_TYPE = "Missing Arg Type"
    MUTABLE_DEFAULT_ARG = "Mutable Default Arg"
    EMPTY_DOCSTRING = "Empty Docstring"


@dataclass
class CodeIssue:
    """Represents a specific documentation or typing defect found in code."""
    file_path: Path
    line_no: int
    col_offset: int
    entity_name: str
    entity_type: str  # "function", "class", "method"
    issue_type: IssueType
    message: str
    severity: Severity = Severity.WARNING


@dataclass
class FunctionArg:
    """Metadata for a function parameter."""
    name: str
    type_annotation: Optional[str] = None
    default_repr: Optional[str] = None


@dataclass
class FunctionMeta:
    """Extracted metadata for a function or method from AST."""
    name: str
    line_start: int
    line_end: int
    is_async: bool
    is_method: bool
    docstring: Optional[str]
    args: List[FunctionArg]
    return_type: Optional[str]
    raw_source: str
    has_mutable_default: bool = False


@dataclass
class ClassMeta:
    """Extracted metadata for a class from AST."""
    name: str
    line_start: int
    line_end: int
    docstring: Optional[str]
    methods: List[FunctionMeta] = field(default_factory=list)


@dataclass
class FileReport:
    """Summary of documentation health for a single Python file."""
    file_path: Path
    total_functions: int = 0
    total_classes: int = 0
    documented_functions: int = 0
    documented_classes: int = 0
    typed_returns: int = 0
    issues: List[CodeIssue] = field(default_factory=list)

    @property
    def score(self) -> float:
        """Calculate a 0 - 100 health score."""
        total_items = self.total_functions + self.total_classes
        if total_items == 0:
            return 100.0

        # Weighted calculation:
        # Docstrings account for 60%, Return types account for 40%
        doc_ratio = (self.documented_functions + self.documented_classes) / total_items
        type_ratio = (self.typed_returns / self.total_functions) if self.total_functions > 0 else 1.0

        weighted = (doc_ratio * 65.0) + (type_ratio * 35.0)
        # Deduct penalties for warnings/errors (e.g., mutable defaults)
        penalties = sum(3.0 for issue in self.issues if issue.issue_type == IssueType.MUTABLE_DEFAULT_ARG)
        return max(0.0, min(100.0, weighted - penalties))


@dataclass
class ProjectReport:
    """Overall project-wide documentation health report."""
    file_reports: List[FileReport] = field(default_factory=list)

    @property
    def total_files(self) -> int:
        return len(self.file_reports)

    @property
    def total_functions(self) -> int:
        return sum(f.total_functions for f in self.file_reports)

    @property
    def total_classes(self) -> int:
        return sum(f.total_classes for f in self.file_reports)

    @property
    def total_issues(self) -> int:
        return sum(len(f.issues) for f in self.file_reports)

    @property
    def overall_score(self) -> float:
        if not self.file_reports:
            return 100.0
        scores = [f.score for f in self.file_reports]
        return round(sum(scores) / len(scores), 1)
