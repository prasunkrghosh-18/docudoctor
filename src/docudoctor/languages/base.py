"""Base classes and types for multi-language documentation analysis and patching."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class Language(str, Enum):
    """Supported programming languages."""
    PYTHON = "python"
    C = "c"
    CPP = "cpp"
    JAVA = "java"

    @classmethod
    def from_filename(cls, filename: str) -> "Language":
        """Detect language from filename extension."""
        lower = filename.lower()
        if lower.endswith(".py"):
            return cls.PYTHON
        elif lower.endswith(".java"):
            return cls.JAVA
        elif lower.endswith((".cpp", ".cxx", ".cc", ".hpp", ".hxx")):
            return cls.CPP
        elif lower.endswith((".c", ".h")):
            return cls.C
        return cls.PYTHON


@dataclass
class LanguageArg:
    name: str
    type_name: Optional[str] = None
    default_val: Optional[str] = None


@dataclass
class LanguageEntity:
    name: str
    entity_type: str  # "function", "method", "class", "interface"
    line_start: int
    line_end: int
    return_type: Optional[str]
    args: List[LanguageArg]
    docstring: Optional[str]
    raw_source: str
    indent: str = ""
    visibility: str = "public"
    has_mutable_default: bool = False


@dataclass
class LanguageIssue:
    line: int
    entity: str
    entity_type: str
    issue_type: str
    severity: str
    message: str
    recommendation: str
    can_fix: bool = True


@dataclass
class LanguageAuditResult:
    score: float
    grade: str
    label: str
    color: str
    total_functions: int
    total_classes: int
    documented_functions: int
    typed_returns: int
    issues: List[LanguageIssue]
    entities: List[LanguageEntity] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "grade": self.grade,
            "label": self.label,
            "color": self.color,
            "total_functions": self.total_functions,
            "total_classes": self.total_classes,
            "documented_functions": self.documented_functions,
            "typed_returns": self.typed_returns,
            "issues": [
                {
                    "line": i.line,
                    "entity": i.entity,
                    "entity_type": i.entity_type,
                    "issue_type": i.issue_type,
                    "severity": i.severity,
                    "message": i.message,
                    "recommendation": i.recommendation,
                    "can_fix": i.can_fix,
                }
                for i in self.issues
            ],
        }


def compute_health_grade(score: float) -> Tuple[str, str, str]:
    """Return (Grade, Label, HexColor) based on score."""
    if score >= 90:
        return "A", "EXCELLENT", "#10b981"
    elif score >= 75:
        return "B", "HEALTHY", "#06b6d4"
    elif score >= 50:
        return "C", "FAIR", "#eab308"
    elif score >= 30:
        return "D", "NEEDS WORK", "#f97316"
    return "F", "CRITICAL", "#ef4444"
