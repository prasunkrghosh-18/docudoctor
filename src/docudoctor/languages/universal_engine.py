"""Universal polyglot documentation auditor and patcher for modern languages."""

import math
import re
from typing import Dict, List, Optional, Tuple

from docudoctor.languages.base import (
    Language,
    LanguageArg,
    LanguageAuditResult,
    LanguageEntity,
    LanguageIssue,
    compute_health_grade,
)

# Per-language declarative configuration:
#   fn_patterns: list of regexes capturing function/method name in group('name'), optional args in group('args'), optional ret in group('ret')
#   cls_patterns: list of regexes capturing class/struct/interface/module name in group('name')
#   doc_style: 'jsdoc' | 'triple_slash' | 'xml_slash' | 'go_slash' | 'hash' | 'lua' | 'sql' | 'haskell' | 'elixir' | 'html' | 'css' | 'data'
_SKIP_NAMES = frozenset({
    "if", "else", "for", "while", "switch", "catch", "match", "loop",
    "return", "sizeof", "typeof", "new", "delete", "throw", "await", "yield",
})

_JS_TS_FN = [
    re.compile(r'^[ \t]*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s*\*?\s*(?P<name>[A-Za-z_$][\w$]*)\s*(?:<[^>]+>)?\s*\((?P<args>[^)]*)\)(?:\s*:\s*(?P<ret>[^{\n]+))?\s*\{', re.MULTILINE),
    re.compile(r'^[ \t]*(?:export\s+)?(?:const|let|var)\s+(?P<name>[A-Za-z_$][\w$]*)\s*(?::\s*[^=]+)?=\s*(?:async\s+)?\((?P<args>[^)]*)\)(?:\s*:\s*(?P<ret>[^=>\n]+))?\s*=>', re.MULTILINE),
    re.compile(r'^[ \t]*(?:public|private|protected|static|async|override|readonly|\s)*\b(?P<name>[A-Za-z_$][\w$]*)\s*(?:<[^>]+>)?\s*\((?P<args>[^)]*)\)(?:\s*:\s*(?P<ret>[^{\n]+))?\s*\{', re.MULTILINE),
]
_JS_TS_CLS = [
    re.compile(r'^[ \t]*(?:export\s+)?(?:default\s+)?(?:abstract\s+)?(?:class|interface|type|enum)\s+(?P<name>[A-Za-z_$][\w$]*)', re.MULTILINE),
]

_LANG_SPECS: Dict[Language, Dict] = {
    Language.JAVASCRIPT: {"fn": _JS_TS_FN, "cls": _JS_TS_CLS, "doc": "jsdoc"},
    Language.TYPESCRIPT: {"fn": _JS_TS_FN, "cls": _JS_TS_CLS, "doc": "jsdoc"},
    Language.GO: {
        "fn": [re.compile(r'^[ \t]*func\s+(?:\([^)]+\)\s+)?(?P<name>[A-Za-z_]\w*)\s*(?:\[[^\]]+\])?\s*\((?P<args>[^)]*)\)\s*(?P<ret>[^{\n]*)?\{', re.MULTILINE)],
        "cls": [re.compile(r'^[ \t]*type\s+(?P<name>[A-Za-z_]\w*)\s+(?:struct|interface)\b', re.MULTILINE)],
        "doc": "go_slash",
    },
    Language.RUST: {
        "fn": [re.compile(r'^[ \t]*(?:pub(?:\([^)]+\))?\s+)?(?:async\s+)?(?:unsafe\s+)?(?:const\s+)?fn\s+(?P<name>[A-Za-z_]\w*)\s*(?:<[^>]+>)?\s*\((?P<args>[^)]*)\)(?:\s*->\s*(?P<ret>[^{\n]+))?', re.MULTILINE)],
        "cls": [re.compile(r'^[ \t]*(?:pub(?:\([^)]+\))?\s+)?(?:struct|enum|trait|mod)\s+(?P<name>[A-Za-z_]\w*)', re.MULTILINE)],
        "doc": "triple_slash",
    },
    Language.CSHARP: {
        "fn": [re.compile(r'^[ \t]*(?:public|private|protected|internal|static|virtual|override|abstract|async|sealed|\s)+(?P<ret>[\w<>\[\]?,.]+)\s+(?P<name>[A-Za-z_]\w*)\s*(?:<[^>]+>)?\s*\((?P<args>[^)]*)\)', re.MULTILINE)],
        "cls": [re.compile(r'^[ \t]*(?:public|private|protected|internal|abstract|sealed|static|partial|\s)*(?:class|interface|struct|record|enum)\s+(?P<name>[A-Za-z_]\w*)', re.MULTILINE)],
        "doc": "xml_slash",
    },
    Language.PHP: {
        "fn": [re.compile(r'^[ \t]*(?:public|private|protected|static|final|abstract|\s)*function\s+&?(?P<name>[A-Za-z_]\w*)\s*\((?P<args>[^)]*)\)(?:\s*:\s*(?P<ret>[^{\n]+))?', re.MULTILINE)],
        "cls": [re.compile(r'^[ \t]*(?:abstract\s+|final\s+)?(?:class|interface|trait|enum)\s+(?P<name>[A-Za-z_]\w*)', re.MULTILINE)],
        "doc": "jsdoc",
    },
    Language.RUBY: {
        "fn": [re.compile(r'^[ \t]*def\s+(?:self\.)?(?P<name>[A-Za-z_]\w*[!?=]?)(?:\s*\((?P<args>[^)]*)\))?', re.MULTILINE)],
        "cls": [re.compile(r'^[ \t]*(?:class|module)\s+(?P<name>[A-Za-z_][\w:]*)', re.MULTILINE)],
        "doc": "hash",
    },
    Language.SWIFT: {
        "fn": [re.compile(r'^[ \t]*(?:public|private|internal|fileprivate|open|static|class|override|mutating|\s)*func\s+(?P<name>[A-Za-z_]\w*)\s*(?:<[^>]+>)?\s*\((?P<args>[^)]*)\)(?:\s*(?:async|throws|rethrows))*\s*(?:->\s*(?P<ret>[^{\n]+))?', re.MULTILINE)],
        "cls": [re.compile(r'^[ \t]*(?:public|private|internal|fileprivate|open|final|\s)*(?:class|struct|protocol|enum|actor)\s+(?P<name>[A-Za-z_]\w*)', re.MULTILINE)],
        "doc": "triple_slash",
    },
    Language.KOTLIN: {
        "fn": [re.compile(r'^[ \t]*(?:public|private|protected|internal|override|suspend|inline|open|\s)*fun\s+(?:<[^>]+>\s*)?(?P<name>[A-Za-z_]\w*)\s*\((?P<args>[^)]*)\)(?:\s*:\s*(?P<ret>[^{\n=]+))?', re.MULTILINE)],
        "cls": [re.compile(r'^[ \t]*(?:data\s+|sealed\s+|open\s+|abstract\s+|enum\s+)?(?:class|interface|object)\s+(?P<name>[A-Za-z_]\w*)', re.MULTILINE)],
        "doc": "jsdoc",
    },
    Language.DART: {
        "fn": [re.compile(r'^[ \t]*(?:static\s+)?(?:Future<[^>]+>|Stream<[^>]+>|void|int|double|bool|String|dynamic|var|[\w<>?]+)\s+(?P<name>[A-Za-z_]\w*)\s*\((?P<args>[^)]*)\)\s*(?:async\s*)?(?:\{|=>)', re.MULTILINE)],
        "cls": [re.compile(r'^[ \t]*(?:abstract\s+)?(?:class|mixin|enum|extension)\s+(?P<name>[A-Za-z_]\w*)', re.MULTILINE)],
        "doc": "triple_slash",
    },
    Language.SCALA: {
        "fn": [re.compile(r'^[ \t]*(?:private|protected|override|final|\s)*def\s+(?P<name>[A-Za-z_]\w*)(?:\[[^\]]+\])?\s*\((?P<args>[^)]*)\)(?:\s*:\s*(?P<ret>[^=\n{]+))?', re.MULTILINE)],
        "cls": [re.compile(r'^[ \t]*(?:case\s+|sealed\s+|abstract\s+)?(?:class|object|trait)\s+(?P<name>[A-Za-z_]\w*)', re.MULTILINE)],
        "doc": "jsdoc",
    },
    Language.R: {
        "fn": [re.compile(r'^[ \t]*(?P<name>[A-Za-z_.][\w.]*)\s*(?:<-|=)\s*function\s*\((?P<args>[^)]*)\)', re.MULTILINE)],
        "cls": [],
        "doc": "hash",
    },
    Language.SQL: {
        "fn": [re.compile(r'^[ \t]*CREATE\s+(?:OR\s+REPLACE\s+)?(?:FUNCTION|PROCEDURE)\s+(?P<name>[\w."`]+)\s*\((?P<args>[^)]*)\)', re.MULTILINE | re.IGNORECASE)],
        "cls": [re.compile(r'^[ \t]*CREATE\s+(?:OR\s+REPLACE\s+)?(?:TABLE|VIEW|INDEX)\s+(?:IF\s+NOT\s+EXISTS\s+)?(?P<name>[\w."`]+)', re.MULTILINE | re.IGNORECASE)],
        "doc": "sql",
    },
    Language.BASH: {
        "fn": [
            re.compile(r'^[ \t]*function\s+(?P<name>[A-Za-z_]\w*)\s*(?:\(\s*\))?\s*\{?', re.MULTILINE),
            re.compile(r'^[ \t]*(?P<name>[A-Za-z_]\w*)\s*\(\s*\)\s*\{', re.MULTILINE),
        ],
        "cls": [],
        "doc": "hash",
    },
    Language.POWERSHELL: {
        "fn": [re.compile(r'^[ \t]*(?:function|filter)\s+(?P<name>[A-Za-z_][\w-]*)\s*(?:\((?P<args>[^)]*)\))?', re.MULTILINE | re.IGNORECASE)],
        "cls": [re.compile(r'^[ \t]*class\s+(?P<name>[A-Za-z_]\w*)', re.MULTILINE | re.IGNORECASE)],
        "doc": "hash",
    },
    Language.PERL: {
        "fn": [re.compile(r'^[ \t]*sub\s+(?P<name>[A-Za-z_]\w*)', re.MULTILINE)],
        "cls": [re.compile(r'^[ \t]*package\s+(?P<name>[A-Za-z_][\w:]*)', re.MULTILINE)],
        "doc": "hash",
    },
    Language.LUA: {
        "fn": [re.compile(r'^[ \t]*(?:local\s+)?function\s+(?P<name>[A-Za-z_][\w.:]*)\s*\((?P<args>[^)]*)\)', re.MULTILINE)],
        "cls": [],
        "doc": "lua",
    },
    Language.HASKELL: {
        "fn": [re.compile(r'^(?P<name>[a-z_][\w\']*)\s*::\s*(?P<ret>.+)$', re.MULTILINE)],
        "cls": [re.compile(r'^(?:data|newtype|type|class)\s+(?P<name>[A-Z][\w\']*)', re.MULTILINE)],
        "doc": "haskell",
    },
    Language.ELIXIR: {
        "fn": [re.compile(r'^[ \t]*defp?\s+(?P<name>[a-z_]\w*[!?]?)\s*(?:\((?P<args>[^)]*)\))?', re.MULTILINE)],
        "cls": [re.compile(r'^[ \t]*defmodule\s+(?P<name>[A-Z][\w.]*)', re.MULTILINE)],
        "doc": "elixir",
    },
    Language.JULIA: {
        "fn": [re.compile(r'^[ \t]*function\s+(?P<name>[A-Za-z_]\w*!?\s*)(?:\((?P<args>[^)]*)\))?', re.MULTILINE)],
        "cls": [re.compile(r'^[ \t]*(?:mutable\s+)?struct\s+(?P<name>[A-Za-z_]\w*)', re.MULTILINE)],
        "doc": "hash",
    },
    Language.SOLIDITY: {
        "fn": [re.compile(r'^[ \t]*function\s+(?P<name>[A-Za-z_]\w*)\s*\((?P<args>[^)]*)\)', re.MULTILINE)],
        "cls": [re.compile(r'^[ \t]*(?:contract|interface|library|abstract\s+contract)\s+(?P<name>[A-Za-z_]\w*)', re.MULTILINE)],
        "doc": "jsdoc",
    },
    Language.OBJC: {
        "fn": [re.compile(r'^[ \t]*[-+]\s*\((?P<ret>[^)]+)\)\s*(?P<name>[A-Za-z_]\w*)', re.MULTILINE)],
        "cls": [re.compile(r'^[ \t]*@(?:interface|implementation|protocol)\s+(?P<name>[A-Za-z_]\w*)', re.MULTILINE)],
        "doc": "jsdoc",
    },
    Language.GROOVY: {
        "fn": [re.compile(r'^[ \t]*(?:def|void|int|String|boolean|public|private|static|\s)+\s+(?P<name>[A-Za-z_]\w*)\s*\((?P<args>[^)]*)\)', re.MULTILINE)],
        "cls": [re.compile(r'^[ \t]*(?:class|interface|trait)\s+(?P<name>[A-Za-z_]\w*)', re.MULTILINE)],
        "doc": "jsdoc",
    },
    Language.MATLAB: {
        "fn": [re.compile(r'^[ \t]*function\s+(?:(?:\[[^\]]+\]|\w+)\s*=\s*)?(?P<name>[A-Za-z_]\w*)\s*(?:\((?P<args>[^)]*)\))?', re.MULTILINE)],
        "cls": [re.compile(r'^[ \t]*classdef\s+(?P<name>[A-Za-z_]\w*)', re.MULTILINE)],
        "doc": "hash",
    },
    Language.HTML: {"fn": [], "cls": [], "doc": "html"},
    Language.CSS: {"fn": [], "cls": [], "doc": "css"},
    Language.YAML: {"fn": [], "cls": [], "doc": "data"},
    Language.JSON: {"fn": [], "cls": [], "doc": "data"},
}


def _parse_generic_args(raw_args: str) -> List[LanguageArg]:
    """Parse comma-separated argument names cleanly."""
    if not raw_args or not raw_args.strip():
        return []
    args: List[LanguageArg] = []
    for part in raw_args.split(","):
        cleaned = part.strip().split("=")[0].strip()
        if not cleaned or cleaned in ("self", "&self", "&mut self", "void", "..."):
            continue
        # Handle typed args like `x: int`, `int x`, `$x`, `mut x`
        tokens = [t for t in re.split(r'[:\s]+', cleaned) if t and t not in ("mut", "ref", "in", "out", "final", "val", "var")]
        if not tokens:
            continue
        # In `x: Type` (TS/Rust/Kotlin/Swift/Go-ish) vs `Type x` (C#/Dart/PHP)
        name = tokens[0] if ":" in cleaned else tokens[-1]
        name = re.sub(r'^[*&$]+', '', name).strip()
        if name and re.match(r'^[A-Za-z_]\w*$', name):
            args.append(LanguageArg(name=name))
    return args


def _has_preceding_doc(lines: List[str], line_idx: int, doc_style: str) -> Optional[str]:
    """Inspect lines immediately above `line_idx` (0-based) for documentation comments."""
    idx = line_idx - 1
    while idx >= 0 and not lines[idx].strip():
        idx -= 1
    if idx < 0:
        return None
    prev = lines[idx].strip()
    if doc_style in ("jsdoc", "css", "sql") and prev.endswith("*/"):
        return prev
    if doc_style in ("triple_slash", "xml_slash") and prev.startswith("///"):
        return prev
    if doc_style == "go_slash" and prev.startswith("//"):
        return prev
    if doc_style == "jsdoc" and prev.startswith("//"):
        return prev
    if doc_style == "hash" and (prev.startswith("#") or prev.startswith("%") or prev.startswith("#>")):
        return prev
    if doc_style == "lua" and prev.startswith("--"):
        return prev
    if doc_style == "sql" and prev.startswith("--"):
        return prev
    if doc_style == "haskell" and (prev.startswith("--") or prev.endswith("-}")):
        return prev
    if doc_style == "elixir" and ('@doc' in prev or '@moduledoc' in prev or prev.endswith('"""')):
        return prev
    return None


def _estimate_block_complexity(lines: List[str], start_idx: int) -> int:
    """Estimate cyclomatic complexity over the next ~40 lines of a block."""
    snippet = "\n".join(lines[start_idx: min(len(lines), start_idx + 40)])
    branches = len(re.findall(r'\b(?:if|else\s+if|elif|elsif|for|while|case|catch|when|&&|\|\|)\b', snippet))
    return 1 + branches


def _build_doc_comment(entity: LanguageEntity, doc_style: str) -> str:
    """Generate an idiomatic doc comment block for any language."""
    ind = entity.indent
    title = entity.name.replace("_", " ").strip().capitalize() or entity.name
    summary = f"{title} ({entity.entity_type})."

    if doc_style == "triple_slash":
        lines = [f"{ind}/// {summary}"]
        for a in entity.args:
            lines.append(f"{ind}/// * `{a.name}` - Input parameter.")
        if entity.return_type and entity.return_type.lower() not in ("void", "()", "none"):
            lines.append(f"{ind}/// Returns `{entity.return_type}`.")
        return "\n".join(lines) + "\n"

    if doc_style == "xml_slash":
        lines = [f"{ind}/// <summary>", f"{ind}/// {summary}", f"{ind}/// </summary>"]
        for a in entity.args:
            lines.append(f'{ind}/// <param name="{a.name}">Input parameter.</param>')
        if entity.return_type and entity.return_type.lower() != "void":
            lines.append(f"{ind}/// <returns>Computed result.</returns>")
        return "\n".join(lines) + "\n"

    if doc_style == "go_slash":
        return f"{ind}// {entity.name} {summary.lower()}\n"

    if doc_style == "hash":
        lines = [f"{ind}# {summary}"]
        for a in entity.args:
            lines.append(f"{ind}# @param {a.name} Input parameter.")
        return "\n".join(lines) + "\n"

    if doc_style == "lua":
        lines = [f"{ind}--- {summary}"]
        for a in entity.args:
            lines.append(f"{ind}-- @param {a.name} Input parameter.")
        return "\n".join(lines) + "\n"

    if doc_style in ("sql", "haskell"):
        prefix = "-- | " if doc_style == "haskell" else "-- "
        return f"{ind}{prefix}{summary}\n"

    if doc_style == "elixir":
        tag = "@moduledoc" if entity.entity_type == "class" else "@doc"
        return f'{ind}{tag} """\n{ind}{summary}\n{ind}"""\n'

    # Default JSDoc / KDoc / PHPDoc / ScalaDoc
    lines = [f"{ind}/**", f"{ind} * {summary}"]
    for a in entity.args:
        lines.append(f"{ind} * @param {a.name} Input parameter.")
    if entity.return_type and entity.return_type.lower() != "void":
        lines.append(f"{ind} * @returns Result value.")
    lines.append(f"{ind} */")
    return "\n".join(lines) + "\n"


def audit_universal_code(code: str, language: Language) -> LanguageAuditResult:
    """Audit any modern programming language for documentation and complexity health."""
    spec = _LANG_SPECS.get(language, {"fn": [], "cls": [], "doc": "jsdoc"})
    lines = code.splitlines()
    entities: List[LanguageEntity] = []
    seen_lines = set()

    # For markup/data languages (HTML, CSS, YAML, JSON), return a clean structural health report
    if spec["doc"] in ("html", "css", "data"):
        non_empty = len([l for l in lines if l.strip()])
        return LanguageAuditResult(
            score=100.0 if non_empty > 0 else 0.0,
            grade="A" if non_empty > 0 else "F",
            label="EXCELLENT" if non_empty > 0 else "CRITICAL",
            color="#10b981" if non_empty > 0 else "#ef4444",
            total_functions=0,
            total_classes=0,
            documented_functions=0,
            typed_returns=0,
            issues=[],
            entities=[],
            avg_complexity=1.0,
            maintainability_index=95.0,
            maintainability_grade="A",
        )

    for pattern in spec["cls"]:
        for m in pattern.finditer(code):
            line_no = code[:m.start()].count("\n") + 1
            if line_no in seen_lines:
                continue
            seen_lines.add(line_no)
            name = m.group("name")
            indent = re.match(r'^[ \t]*', lines[line_no - 1]).group(0) if line_no <= len(lines) else ""
            doc = _has_preceding_doc(lines, line_no - 1, spec["doc"])
            entities.append(LanguageEntity(
                name=name, entity_type="class", line_start=line_no, line_end=line_no,
                return_type=None, args=[], docstring=doc, raw_source=m.group(0), indent=indent,
            ))

    for pattern in spec["fn"]:
        for m in pattern.finditer(code):
            line_no = code[:m.start()].count("\n") + 1
            if line_no in seen_lines:
                continue
            name = m.group("name")
            if name in _SKIP_NAMES:
                continue
            seen_lines.add(line_no)
            gd = m.groupdict()
            args = _parse_generic_args(gd.get("args") or "")
            ret = (gd.get("ret") or "").strip() or None
            indent = re.match(r'^[ \t]*', lines[line_no - 1]).group(0) if line_no <= len(lines) else ""
            doc = _has_preceding_doc(lines, line_no - 1, spec["doc"])
            comp = _estimate_block_complexity(lines, line_no - 1)
            entities.append(LanguageEntity(
                name=name, entity_type="function", line_start=line_no, line_end=line_no,
                return_type=ret, args=args, docstring=doc, raw_source=m.group(0),
                indent=indent, complexity=comp,
            ))

    entities.sort(key=lambda e: e.line_start)
    issues: List[LanguageIssue] = []
    funcs = [e for e in entities if e.entity_type == "function"]
    classes = [e for e in entities if e.entity_type == "class"]

    doc_count = sum(1 for f in funcs if f.docstring)
    typed_count = sum(1 for f in funcs if f.return_type)

    for e in entities:
        if not e.docstring:
            issues.append(LanguageIssue(
                line=e.line_start,
                entity=e.name,
                entity_type=e.entity_type,
                issue_type="Missing Docstring",
                severity="ERROR" if e.entity_type == "function" else "WARNING",
                message=f"{e.entity_type.capitalize()} '{e.name}' is missing documentation comments.",
                recommendation=f"Add idiomatic {language.value.upper()} documentation above '{e.name}'.",
                can_fix=True,
            ))

    total = len(entities)
    documented_total = sum(1 for e in entities if e.docstring)
    score = round((documented_total / total) * 100.0, 1) if total > 0 else 100.0
    grade, label, color = compute_health_grade(score)
    avg_comp = round(sum(f.complexity for f in funcs) / len(funcs), 2) if funcs else 1.0
    loc = max(1, len([l for l in lines if l.strip()]))
    mi = round(max(0.0, min(100.0, 171 - 5.2 * math.log(max(1, loc * 5)) - 0.23 * avg_comp - 16.2 * math.log(loc))), 1)
    mi_grade = "A" if mi >= 85 else ("B" if mi >= 65 else ("C" if mi >= 45 else "D"))

    return LanguageAuditResult(
        score=score,
        grade=grade,
        label=label,
        color=color,
        total_functions=len(funcs),
        total_classes=len(classes),
        documented_functions=doc_count,
        typed_returns=typed_count,
        issues=issues,
        entities=entities,
        avg_complexity=avg_comp,
        maintainability_index=mi,
        maintainability_grade=mi_grade,
    )


def patch_universal_code(
    code: str,
    language: Language,
    target_entity: Optional[str] = None,
) -> Tuple[str, int]:
    """Insert idiomatic documentation comments into any supported language."""
    spec = _LANG_SPECS.get(language, {"doc": "jsdoc"})
    audit = audit_universal_code(code, language)
    targets = [
        e for e in audit.entities
        if not e.docstring and (target_entity is None or e.name == target_entity)
    ]
    if not targets:
        return code, 0

    lines = code.splitlines(keepends=True)
    # Insert bottom-up so line indices remain valid
    patched_count = 0
    for entity in sorted(targets, key=lambda e: e.line_start, reverse=True):
        idx = entity.line_start - 1
        if 0 <= idx <= len(lines):
            comment = _build_doc_comment(entity, spec["doc"])
            lines.insert(idx, comment)
            patched_count += 1

    return "".join(lines), patched_count
