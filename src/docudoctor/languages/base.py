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
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    GO = "go"
    RUST = "rust"
    CSHARP = "csharp"
    PHP = "php"
    RUBY = "ruby"
    SWIFT = "swift"
    KOTLIN = "kotlin"
    DART = "dart"
    SCALA = "scala"
    R = "r"
    SQL = "sql"
    BASH = "bash"
    POWERSHELL = "powershell"
    PERL = "perl"
    LUA = "lua"
    HASKELL = "haskell"
    ELIXIR = "elixir"
    JULIA = "julia"
    SOLIDITY = "solidity"
    OBJC = "objc"
    GROOVY = "groovy"
    MATLAB = "matlab"
    HTML = "html"
    CSS = "css"
    YAML = "yaml"
    JSON = "json"

    @classmethod
    def from_filename(cls, filename: str) -> "Language":
        """Detect language from filename extension."""
        lower = filename.lower()
        ext_map = {
            (".py", ".pyw"): cls.PYTHON,
            (".java",): cls.JAVA,
            (".cpp", ".cxx", ".cc", ".hpp", ".hxx"): cls.CPP,
            (".c", ".h"): cls.C,
            (".js", ".mjs", ".cjs", ".jsx"): cls.JAVASCRIPT,
            (".ts", ".tsx", ".mts", ".cts"): cls.TYPESCRIPT,
            (".go",): cls.GO,
            (".rs",): cls.RUST,
            (".cs",): cls.CSHARP,
            (".php", ".phtml"): cls.PHP,
            (".rb", ".rake"): cls.RUBY,
            (".swift",): cls.SWIFT,
            (".kt", ".kts"): cls.KOTLIN,
            (".dart",): cls.DART,
            (".scala", ".sc"): cls.SCALA,
            (".r",): cls.R,
            (".sql",): cls.SQL,
            (".sh", ".bash", ".zsh"): cls.BASH,
            (".ps1", ".psm1", ".psd1"): cls.POWERSHELL,
            (".pl", ".pm"): cls.PERL,
            (".lua",): cls.LUA,
            (".hs",): cls.HASKELL,
            (".ex", ".exs"): cls.ELIXIR,
            (".jl",): cls.JULIA,
            (".sol",): cls.SOLIDITY,
            (".m", ".mm"): cls.OBJC,
            (".groovy", ".gradle"): cls.GROOVY,
            (".html", ".htm"): cls.HTML,
            (".css", ".scss", ".sass", ".less"): cls.CSS,
            (".yml", ".yaml"): cls.YAML,
            (".json",): cls.JSON,
        }
        for exts, lang in ext_map.items():
            if lower.endswith(exts):
                return lang
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
    complexity: int = 1


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
    avg_complexity: float = 1.0
    maintainability_index: float = 100.0
    maintainability_grade: str = "A"

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
            "avg_complexity": self.avg_complexity,
            "maintainability_index": self.maintainability_index,
            "maintainability_grade": self.maintainability_grade,
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
            "entities": [
                {
                    "name": e.name,
                    "entity_type": e.entity_type,
                    "line_start": e.line_start,
                    "complexity": e.complexity,
                    "has_doc": bool(e.docstring and e.docstring.strip()),
                    "return_type": e.return_type,
                }
                for e in self.entities
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
