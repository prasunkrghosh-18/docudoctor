"""FastAPI Web Application for DocuDoctor with interactive web interface."""

import ast
import difflib
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from docudoctor.doctor.generator import DocstringStyle, generate_docstring
from docudoctor.doctor.patcher import _detect_body_indent, _find_header_end_line
from docudoctor.scanner import CodeAnalysisVisitor

app = FastAPI(title="DocuDoctor Web", version="0.1.0")


class AuditRequest(BaseModel):
    code: str


class FixRequest(BaseModel):
    code: str
    style: DocstringStyle = DocstringStyle.GOOGLE


def _audit_code_string(source_code: str):
    """Audit raw python code string directly."""
    try:
        tree = ast.parse(source_code, filename="<input>")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Syntax Error in Python code: {str(e)}")

    dummy_path = Path("editor.py")
    visitor = CodeAnalysisVisitor(dummy_path, source_code)
    visitor.visit(tree)

    total_funcs = len(visitor.functions)
    total_classes = len(visitor.classes)
    total_items = total_funcs + total_classes

    doc_funcs = sum(1 for f in visitor.functions if f.docstring and f.docstring.strip())
    doc_classes = sum(1 for c in visitor.classes if c.docstring and c.docstring.strip())
    typed_returns = sum(1 for f in visitor.functions if f.return_type)

    if total_items == 0:
        score = 100.0
    else:
        doc_ratio = (doc_funcs + doc_classes) / total_items
        type_ratio = (typed_returns / total_funcs) if total_funcs > 0 else 1.0
        weighted = (doc_ratio * 65.0) + (type_ratio * 35.0)
        penalties = sum(3.0 for issue in visitor.issues if issue.issue_type == "Mutable Default Arg")
        score = max(0.0, min(100.0, weighted - penalties))

    if score >= 90:
        grade, label, color = "A", "EXCELLENT", "#10b981"
    elif score >= 75:
        grade, label, color = "B", "HEALTHY", "#06b6d4"
    elif score >= 50:
        grade, label, color = "C", "FAIR", "#eab308"
    elif score >= 30:
        grade, label, color = "D", "NEEDS WORK", "#f97316"
    else:
        grade, label, color = "F", "CRITICAL", "#ef4444"

    issues_data = [
        {
            "line": i.line_no,
            "entity": i.entity_name,
            "entity_type": i.entity_type,
            "issue_type": i.issue_type.value if hasattr(i.issue_type, "value") else str(i.issue_type),
            "severity": i.severity.value if hasattr(i.severity, "value") else str(i.severity),
            "message": i.message,
        }
        for i in visitor.issues
    ]

    return {
        "score": round(score, 1),
        "grade": grade,
        "label": label,
        "color": color,
        "total_functions": total_funcs,
        "total_classes": total_classes,
        "documented_functions": doc_funcs,
        "typed_returns": typed_returns,
        "issues": issues_data,
        "functions_meta": visitor.functions,
    }


@app.post("/api/audit")
def api_audit(req: AuditRequest):
    """Audit Python code and return health metrics and issue breakdown."""
    data = _audit_code_string(req.code)
    data.pop("functions_meta", None)
    return data


@app.post("/api/fix")
def api_fix(req: FixRequest):
    """Generate docstrings according to selected style and return patched code with diff."""
    data = _audit_code_string(req.code)
    functions = data.get("functions_meta", [])

    candidates = [f for f in functions if not f.docstring or not f.docstring.strip()]
    if not candidates:
        return {
            "patched_code": req.code,
            "diff": "",
            "patched_count": 0,
            "message": "Code is already fully documented!",
        }

    lines = req.code.splitlines()
    candidates.sort(key=lambda f: f.line_start, reverse=True)

    for func in candidates:
        def_start_idx = func.line_start - 1
        if def_start_idx >= len(lines):
            continue
        header_end_idx = _find_header_end_line(lines, def_start_idx)
        indent = _detect_body_indent(lines, header_end_idx)

        new_doc = generate_docstring(func, style=req.style, indent=indent)
        doc_lines = new_doc.splitlines()
        lines = lines[: header_end_idx + 1] + doc_lines + lines[header_end_idx + 1 :]

    patched_code = "\n".join(lines) + ("\n" if req.code.endswith("\n") else "")

    # Calculate unified diff
    orig_lines = req.code.splitlines(keepends=True)
    mod_lines = patched_code.splitlines(keepends=True)
    diff = list(
        difflib.unified_diff(
            orig_lines, mod_lines, fromfile="a/source.py", tofile="b/source.py", lineterm="\n"
        )
    )

    return {
        "patched_code": patched_code,
        "diff": "".join(diff),
        "patched_count": len(candidates),
        "message": f"Successfully injected {len(candidates)} docstrings ({req.style.value} style)!",
    }


@app.get("/", response_class=HTMLResponse)
def index():
    """Serves the interactive DocuDoctor single-page web app."""
    return HTML_CONTENT


HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DocuDoctor - AST Code Health & Docstring Engine</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css"/>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-python.min.js"></script>
  <style>
    body { font-family: 'Inter', sans-serif; background-color: #0b0f19; color: #e2e8f0; }
    pre, code, textarea { font-family: 'Fira Code', monospace; }
    .glass { background: rgba(17, 24, 39, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08); }
    .glow-cyan { box-shadow: 0 0 25px rgba(6, 182, 212, 0.25); }
  </style>
</head>
<body class="min-h-screen flex flex-col">

  <!-- Header -->
  <header class="border-b border-gray-800 bg-gray-950/80 sticky top-0 z-50 backdrop-blur-md">
    <div class="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <span class="text-2xl">⚕</span>
        <div>
          <span class="font-bold text-xl tracking-tight text-cyan-400">DOCU</span><span class="font-bold text-xl tracking-tight text-fuchsia-400">DOCTOR</span>
          <span class="ml-2 text-xs text-gray-400 hidden sm:inline">AST Code Health & Auto-Docstring Engine</span>
        </div>
      </div>
      <div class="flex items-center space-x-4">
        <a href="https://github.com/prasunkrghosh-18/docudoctor" target="_blank" class="flex items-center space-x-2 text-sm text-gray-300 hover:text-white bg-gray-800/80 hover:bg-gray-700 px-3 py-1.5 rounded-lg border border-gray-700 transition">
          <svg class="w-4 h-4 fill-current" viewBox="0 0 24 24"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/></svg>
          <span>GitHub</span>
        </a>
      </div>
    </div>
  </header>

  <!-- Main Container -->
  <main class="max-w-7xl mx-auto px-6 py-8 flex-1 w-full flex flex-col gap-8">

    <!-- Top Action Bar -->
    <div class="flex flex-wrap items-center justify-between gap-4 glass p-4 rounded-xl">
      <div class="flex items-center space-x-3">
        <button onclick="loadSample()" class="text-xs bg-gray-800 hover:bg-gray-700 text-gray-200 px-3 py-1.5 rounded-md border border-gray-700 transition">
          📂 Load Sample Code
        </button>
        <button onclick="clearEditor()" class="text-xs text-gray-400 hover:text-white px-2 py-1 transition">
          Clear
        </button>
      </div>

      <div class="flex items-center space-x-4">
        <div class="flex items-center space-x-2">
          <label class="text-xs text-gray-400">Docstring Style:</label>
          <select id="docStyle" class="bg-gray-900 border border-gray-700 text-xs rounded-md px-2.5 py-1.5 text-cyan-400 focus:outline-none focus:border-cyan-500">
            <option value="google">Google Style</option>
            <option value="numpy">NumPy Style</option>
            <option value="sphinx">Sphinx Style</option>
          </select>
        </div>

        <button onclick="auditCode()" class="bg-cyan-600 hover:bg-cyan-500 text-white font-medium text-xs px-4 py-2 rounded-lg transition flex items-center space-x-1.5 shadow-lg shadow-cyan-950">
          <span>🔍</span><span>Audit Code</span>
        </button>

        <button onclick="fixCode()" class="bg-gradient-to-r from-fuchsia-600 to-indigo-600 hover:from-fuchsia-500 hover:to-indigo-500 text-white font-medium text-xs px-4 py-2 rounded-lg transition flex items-center space-x-1.5 shadow-lg shadow-fuchsia-950">
          <span>✨</span><span>Auto-Generate Docs</span>
        </button>
      </div>
    </div>

    <!-- Workspace Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1">

      <!-- Left: Code Editor -->
      <div class="lg:col-span-7 flex flex-col glass rounded-xl overflow-hidden min-h-[460px]">
        <div class="bg-gray-900/90 border-b border-gray-800 px-4 py-2.5 flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <div class="w-3 h-3 rounded-full bg-red-500/80"></div>
            <div class="w-3 h-3 rounded-full bg-yellow-500/80"></div>
            <div class="w-3 h-3 rounded-full bg-green-500/80"></div>
            <span class="text-xs text-gray-400 ml-2 font-mono">python_source.py</span>
          </div>
          <span class="text-xs text-gray-500">Type or paste Python code</span>
        </div>
        <textarea id="codeEditor" class="w-full flex-1 bg-gray-950/70 text-gray-100 p-4 text-sm leading-relaxed focus:outline-none resize-none font-mono selection:bg-cyan-900" spellcheck="false" placeholder="# Paste your Python code here..."></textarea>
      </div>

      <!-- Right: Health Dashboard & Issues -->
      <div class="lg:col-span-5 flex flex-col gap-6">

        <!-- Scorecard Card -->
        <div class="glass p-6 rounded-xl flex items-center justify-between relative overflow-hidden">
          <div>
            <span class="text-xs uppercase tracking-wider text-gray-400 font-semibold">Doc Health Score</span>
            <div class="flex items-baseline space-x-3 mt-1">
              <span id="scoreVal" class="text-5xl font-extrabold text-cyan-400">--</span>
              <span id="scoreMax" class="text-sm text-gray-500">/ 100</span>
            </div>
            <div id="gradeBadge" class="mt-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-gray-800 text-gray-300">
              Awaiting Audit
            </div>
          </div>

          <!-- Circular Metric Graphic -->
          <div class="relative w-24 h-24 flex items-center justify-center">
            <svg class="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
              <path class="text-gray-800" stroke-width="3.5" stroke="currentColor" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"/>
              <path id="circleProgress" class="text-cyan-400 transition-all duration-700 ease-out" stroke-dasharray="0, 100" stroke-width="3.5" stroke-linecap="round" stroke="currentColor" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"/>
            </svg>
            <span id="gradeLetter" class="absolute text-2xl font-black text-white">?</span>
          </div>
        </div>

        <!-- Metrics Grid -->
        <div class="grid grid-cols-3 gap-3">
          <div class="glass p-3 rounded-lg text-center">
            <span class="text-xs text-gray-400">Functions</span>
            <p id="statFuncs" class="text-lg font-bold text-gray-200 mt-0.5">--</p>
          </div>
          <div class="glass p-3 rounded-lg text-center">
            <span class="text-xs text-gray-400">Documented</span>
            <p id="statDocs" class="text-lg font-bold text-emerald-400 mt-0.5">--</p>
          </div>
          <div class="glass p-3 rounded-lg text-center">
            <span class="text-xs text-gray-400">Typed Returns</span>
            <p id="statTyped" class="text-lg font-bold text-fuchsia-400 mt-0.5">--</p>
          </div>
        </div>

        <!-- Issue List -->
        <div class="glass rounded-xl flex-1 flex flex-col overflow-hidden max-h-[320px]">
          <div class="px-4 py-3 border-b border-gray-800 flex items-center justify-between bg-gray-900/60">
            <span class="text-xs font-semibold text-gray-300">Detected Issues</span>
            <span id="issueCountBadge" class="text-xs bg-gray-800 text-gray-400 px-2 py-0.5 rounded-full">0 issues</span>
          </div>
          <div id="issuesContainer" class="p-3 overflow-y-auto space-y-2 flex-1 text-xs">
            <p class="text-gray-500 text-center py-8">Click <b>Audit Code</b> to inspect your Python code.</p>
          </div>
        </div>

      </div>
    </div>

    <!-- Proposed Diff Output (Visible after Fix) -->
    <div id="diffSection" class="glass rounded-xl overflow-hidden hidden">
      <div class="bg-gray-900 px-4 py-3 border-b border-gray-800 flex items-center justify-between">
        <span class="text-xs font-semibold text-cyan-400">Proposed Patch & Diff Preview</span>
        <button onclick="copyPatchedCode()" class="text-xs bg-gray-800 hover:bg-gray-700 text-gray-300 px-3 py-1 rounded transition">
          📋 Copy Patched Code
        </button>
      </div>
      <div class="p-4 bg-gray-950 overflow-x-auto">
        <pre id="diffOutput" class="text-xs leading-relaxed font-mono whitespace-pre text-gray-300"></pre>
      </div>
    </div>

  </main>

  <script>
    const SAMPLE_CODE = `class PaymentGateway:
    def __init__(self, api_key: str, sandbox: bool = False):
        self.api_key = api_key
        self.sandbox = sandbox

    def charge(self, amount, currency="USD", metadata=[]):
        total = amount * 1.05
        return {"status": "success", "charged": total}

def calculate_discount(price: float, discount_percent: float):
    discount = price * (discount_percent / 100.0)
    return round(price - discount, 2)

async def send_invoice(user_id: int, invoice_id: str, tags=[]):
    return True`;

    let lastPatchedCode = "";

    function loadSample() {
      document.getElementById('codeEditor').value = SAMPLE_CODE;
      auditCode();
    }

    function clearEditor() {
      document.getElementById('codeEditor').value = "";
      document.getElementById('scoreVal').innerText = "--";
      document.getElementById('gradeLetter').innerText = "?";
      document.getElementById('gradeBadge').innerText = "Awaiting Audit";
      document.getElementById('circleProgress').setAttribute('stroke-dasharray', '0, 100');
      document.getElementById('statFuncs').innerText = "--";
      document.getElementById('statDocs').innerText = "--";
      document.getElementById('statTyped').innerText = "--";
      document.getElementById('issueCountBadge').innerText = "0 issues";
      document.getElementById('issuesContainer').innerHTML = `<p class="text-gray-500 text-center py-8">Click <b>Audit Code</b> to inspect your Python code.</p>`;
      document.getElementById('diffSection').classList.add('hidden');
    }

    async function auditCode() {
      const code = document.getElementById('codeEditor').value;
      if (!code.trim()) return alert("Please enter Python code first!");

      try {
        const res = await fetch('/api/audit', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ code })
        });
        const data = await res.json();
        if (!res.ok) return alert(data.detail || "Audit failed.");

        renderDashboard(data);
      } catch (err) {
        alert("Error auditing code: " + err.message);
      }
    }

    function renderDashboard(data) {
      document.getElementById('scoreVal').innerText = data.score;
      document.getElementById('gradeLetter').innerText = data.grade;
      document.getElementById('gradeLetter').style.color = data.color;

      const badge = document.getElementById('gradeBadge');
      badge.innerText = data.label + ` (Grade ${data.grade})`;
      badge.style.color = data.color;
      badge.style.backgroundColor = `${data.color}20`;

      document.getElementById('circleProgress').setAttribute('stroke-dasharray', `${data.score}, 100`);
      document.getElementById('circleProgress').style.color = data.color;

      document.getElementById('statFuncs').innerText = data.total_functions;
      document.getElementById('statDocs').innerText = `${data.documented_functions}/${data.total_functions}`;
      document.getElementById('statTyped').innerText = `${data.typed_returns}/${data.total_functions}`;
      document.getElementById('issueCountBadge').innerText = `${data.issues.length} issues`;

      const container = document.getElementById('issuesContainer');
      if (data.issues.length === 0) {
        container.innerHTML = `<div class="p-3 text-center text-emerald-400 font-medium">✨ All functions are fully documented and typed!</div>`;
        return;
      }

      container.innerHTML = data.issues.map(iss => {
        let badgeColor = iss.severity === "ERROR" ? "bg-red-900/60 text-red-300" : (iss.severity === "WARNING" ? "bg-amber-900/60 text-amber-300" : "bg-cyan-900/60 text-cyan-300");
        return `
          <div class="p-2.5 rounded bg-gray-900/70 border border-gray-800 flex items-start space-x-2">
            <span class="px-1.5 py-0.5 rounded text-[10px] font-bold ${badgeColor}">L${iss.line}</span>
            <div class="flex-1">
              <div class="flex items-center space-x-1 font-semibold text-gray-200">
                <span class="text-cyan-400">${iss.entity}</span>
                <span class="text-gray-500 font-normal">(${iss.entity_type})</span>
              </div>
              <p class="text-gray-400 mt-0.5">${iss.message}</p>
            </div>
          </div>
        `;
      }).join('');
    }

    async function fixCode() {
      const code = document.getElementById('codeEditor').value;
      if (!code.trim()) return alert("Please enter Python code first!");
      const style = document.getElementById('docStyle').value;

      try {
        const res = await fetch('/api/fix', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ code, style })
        });
        const data = await res.json();
        if (!res.ok) return alert(data.detail || "Fix failed.");

        lastPatchedCode = data.patched_code;
        document.getElementById('codeEditor').value = data.patched_code;

        // Render Diff
        const diffSection = document.getElementById('diffSection');
        diffSection.classList.remove('hidden');

        const diffEl = document.getElementById('diffOutput');
        diffEl.innerHTML = data.diff.split('\\n').map(line => {
          if (line.startsWith('+')) return `<span class="text-emerald-400">${escapeHtml(line)}</span>`;
          if (line.startsWith('-')) return `<span class="text-red-400">${escapeHtml(line)}</span>`;
          if (line.startsWith('@')) return `<span class="text-cyan-400">${escapeHtml(line)}</span>`;
          return `<span class="text-gray-500">${escapeHtml(line)}</span>`;
        }).join('\\n');

        // Re-audit with updated code
        auditCode();
      } catch (err) {
        alert("Error generating docstrings: " + err.message);
      }
    }

    function copyPatchedCode() {
      if (!lastPatchedCode) return alert("No patched code available.");
      navigator.clipboard.writeText(lastPatchedCode).then(() => {
        alert("Copied patched Python code to clipboard!");
      });
    }

    function escapeHtml(text) {
      return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    // Auto-load sample on first visit
    window.addEventListener('DOMContentLoaded', loadSample);
  </script>
</body>
</html>
"""
