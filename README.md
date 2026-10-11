# ⚕ DocuDoctor

<p align="center">
  <b>AST-powered Python documentation auditor, health scorecard, and AI auto-docstring engine.</b>
</p>

<p align="center">
  <a href="https://github.com/prasunkrghosh-18/docudoctor/actions"><img src="https://github.com/prasunkrghosh-18/docudoctor/actions/workflows/ci.yml/badge.svg" alt="CI Status"></a>
  <img src="https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue" alt="Python Versions">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/code%20style-Google-purple" alt="Google Style">
  <img src="https://img.shields.io/badge/UI-Rich%20TUI-cyan" alt="Rich TUI">
</p>

---

## ⚡ Overview

**DocuDoctor** inspects Python source code using Abstract Syntax Trees (`ast`), flags missing docstrings and type annotations, calculates a **Documentation Health Score (0-100)**, and can automatically generate and safely inject Google-style docstrings into your codebase.

### Key Features:
- 🩺 **AST-Powered Inspection**: Never relies on brittle regex. Parses real Python syntax trees to detect undocumented functions, missing return types, and dangerous mutable default arguments (`def f(items=[])`).
- 🎨 **Rich Terminal UI**: Displays a clean health scorecard, progress meters, and color-coded issue tables.
- 🩹 **Interactive Auto-Fix**: Automatically generates Google-style docstrings and displays a colorized git-style diff preview before applying changes.
- 🤖 **Local AI & Offline Ready**: Integrates seamlessly with local LLMs (via **Ollama**) or runs offline with smart AST template synthesis.
- 🛡️ **CI/CD Enforcer**: Use `--fail-under <score>` in GitHub Actions to prevent undocumented pull requests from merging.

---

## 🚀 Quickstart

### Installation

```bash
git clone https://github.com/prasunkrghosh-18/docudoctor.git
cd docudoctor
pip install -e .
```

### 1. Audit Codebase & Health Scorecard

```bash
# Scan a directory or single file
docudoctor scan ./src

# Enforce quality in CI/CD pipeline (fails if health score < 80%)
docudoctor scan ./src --fail-under 80
```

### 2. Auto-Generate Missing Docstrings

```bash
# Preview proposed docstring fixes (dry-run)
docudoctor fix ./src/utils.py --dry-run

# Interactively apply docstrings
docudoctor fix ./src/utils.py

# Auto-generate using a local LLM via Ollama
docudoctor fix ./src/utils.py --ai --model llama3:latest
```

---

## 📸 Terminal UI Preview

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│  [+] DOCUDOCTOR  |  AST Code Health & Docstring Engine                      │
└──────────────────────────────────────────────────────────────────── v0.1.0 ─┘

  Doc Health                 Audit Overview
┌──────────────────────┐   ┌──────────────────────────────────────────────────┐
│                      │   │  Progress: [################----] 80.0%          │
│   Grade B            │   │                                                  │
│   80.0/100           │   │  * Files Scanned:       1                        │
│   [HEALTHY]          │   │  * Functions / Methods: 4 (3/4 documented)       │
│                      │   │  * Return Type Hints:   1/4 (25.0% typed)        │
└──────────────────────┘   └──────────────────────────────────────────────────┘

Detected Documentation & Typing Defects
┌───────┬────────────────────┬──────────┬────────────────────┬────────────────┐
│ Sev   │ Location           │ Type     │ Target             │ Issue          │
├───────┼────────────────────┼──────────┼────────────────────┼────────────────┤
│ [ERR] │ messy.py:8         │ method   │ charge             │ Method has no  │
│       │                    │          │                    │ docstring.     │
│ [WRN] │ messy.py:8         │ method   │ charge             │ Has dangerous  │
│       │                    │          │                    │ default '[]'.  │
└───────┴────────────────────┴──────────┴────────────────────┴────────────────┘
```

---

## 🧪 Testing

Run unit tests via `pytest`:

```bash
pytest -v
```

---

## 🛠️ Project Architecture

```
docudoctor/
├── src/
│   └── docudoctor/
│       ├── cli.py            # Typer CLI interface (scan, fix, version)
│       ├── scanner.py        # AST visitor & syntax analysis
│       ├── models.py         # Data models & health scoring logic
│       ├── doctor/
│       │   ├── generator.py  # Docstring engine (AST template + Ollama)
│       │   └── patcher.py    # Safe code injection & indent alignment
│       └── ui/
│           ├── console.py    # Console themes & cross-platform UTF-8 handling
│           ├── dashboard.py  # Rich scorecard & issue tables
│           └── diff_view.py  # Syntax-highlighted git diffs
├── tests/                    # Pytest test suite
├── examples/                 # Sample files for demonstrations
└── .github/workflows/        # Automated CI workflow
```

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.
