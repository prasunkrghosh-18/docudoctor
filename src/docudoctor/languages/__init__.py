"""Unified multi-language documentation auditor and patcher interface."""

from typing import Optional, Tuple

from docudoctor.doctor.generator import DocstringStyle
from docudoctor.languages.base import (
    Language,
    LanguageAuditResult,
    LanguageEntity,
    LanguageIssue,
    compute_health_grade,
)
from docudoctor.languages.c_engine import audit_c_code, patch_c_code
from docudoctor.languages.cpp_engine import audit_cpp_code, patch_cpp_code
from docudoctor.languages.java_engine import audit_java_code, patch_java_code
from docudoctor.languages.python_engine import audit_python_code, patch_python_code


def audit_code_by_language(code: str, language: Language = Language.PYTHON) -> LanguageAuditResult:
    """Audit code for documentation and typing health according to language rules."""
    if language == Language.C:
        return audit_c_code(code)
    elif language == Language.CPP:
        return audit_cpp_code(code)
    elif language == Language.JAVA:
        return audit_java_code(code)
    else:
        return audit_python_code(code)


def patch_code_by_language(
    code: str,
    language: Language = Language.PYTHON,
    style: str = "google",
    target: Optional[str] = None,
) -> Tuple[str, int]:
    """Patch missing documentation into code matching the language's doc convention."""
    if language == Language.C:
        return patch_c_code(code, target_function=target)
    elif language == Language.CPP:
        return patch_cpp_code(code, target_entity=target)
    elif language == Language.JAVA:
        return patch_java_code(code, target_entity=target)
    else:
        doc_style = DocstringStyle.GOOGLE
        try:
            doc_style = DocstringStyle(style.lower())
        except ValueError:
            pass
        return patch_python_code(code, style=doc_style, target_function=target)
