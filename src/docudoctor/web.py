"""FastAPI Web Application for DocuDoctor with interactive multi-language web interface."""

import difflib
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from docudoctor.languages import (
    Language,
    audit_code_by_language,
    patch_code_by_language,
)
from docudoctor.reporter import generate_markdown_report

app = FastAPI(title="DocuDoctor Web", version="0.3.0")


class AuditRequest(BaseModel):
    code: str
    language: str = "python"


class FixRequest(BaseModel):
    code: str
    language: str = "python"
    style: str = "google"
    target: Optional[str] = None


class ReportRequest(BaseModel):
    code: str
    language: str = "python"
    filename: str = "main.py"


def _ext_for_lang(lang: Language) -> str:
    if lang == Language.C:
        return "c"
    elif lang == Language.CPP:
        return "cpp"
    elif lang == Language.JAVA:
        return "java"
    return "py"


@app.post("/api/audit")
def api_audit(req: AuditRequest):
    """Audit code for documentation and typing health according to language rules."""
    try:
        lang = Language(req.language.lower())
    except ValueError:
        lang = Language.PYTHON

    try:
        result = audit_code_by_language(req.code, language=lang)
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/fix")
def api_fix(req: FixRequest):
    """Patch missing documentation into code matching the language's doc convention."""
    try:
        lang = Language(req.language.lower())
    except ValueError:
        lang = Language.PYTHON

    try:
        patched_code, patched_count = patch_code_by_language(
            req.code, language=lang, style=req.style, target=req.target
        )

        ext = _ext_for_lang(lang)
        orig_lines = req.code.splitlines(keepends=True)
        mod_lines = patched_code.splitlines(keepends=True)
        diff = list(
            difflib.unified_diff(
                orig_lines,
                mod_lines,
                fromfile=f"a/code.{ext}",
                tofile=f"b/code.{ext}",
                lineterm="\n",
            )
        )

        return {
            "patched_code": patched_code,
            "diff": "".join(diff),
            "patched_count": patched_count,
            "message": f"Successfully injected {patched_count} docstring(s)!",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/report")
def api_report(req: ReportRequest):
    """Generate and return a comprehensive GitHub-flavored Markdown audit report."""
    try:
        lang = Language(req.language.lower())
    except ValueError:
        lang = Language.PYTHON

    try:
        result = audit_code_by_language(req.code, language=lang)
        report_md = generate_markdown_report(result, filename=req.filename, language=lang.value)
        return {
            "report": report_md,
            "filename": f"DOCUDOCTOR_REPORT_{req.filename.rsplit('.', 1)[0]}.md",
            "score": result.score,
            "grade": result.grade,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/", response_class=HTMLResponse)
def index():
    """Serves the interactive DocuDoctor single-page web app."""
    return HTML_CONTENT


HTML_CONTENT = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DocuDoctor • Multi-Language Code Health & Docstring Engine</title>
  <script>
    // Immediate Theme Initialization (Opens through System Default on first visit)
    (function() {
      var saved = localStorage.getItem('docudoctor_theme') || 'system';
      var isDark = true;
      if (saved === 'dark') {
        isDark = true;
      } else if (saved === 'light') {
        isDark = false;
      } else {
        isDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
      }
      if (isDark) {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }
    })();
  </script>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          fontFamily: {
            sans: ['Plus Jakarta Sans', 'sans-serif'],
            mono: ['Fira Code', 'monospace']
          },
          colors: {
            dark: {
              950: '#06080d',
              900: '#0b0f17',
              850: '#101622',
              800: '#161f30',
              750: '#1e293f',
              700: '#25344f'
            }
          }
        }
      }
    }
  </script>
  <style>
    body {
      background-color: #06080d;
      color: #e2e8f0;
      background-image: 
        radial-gradient(ellipse 80% 50% at 50% -20%, rgba(6, 182, 212, 0.15), transparent),
        radial-gradient(ellipse 60% 40% at 90% 20%, rgba(168, 85, 247, 0.12), transparent),
        radial-gradient(ellipse 50% 50% at 10% 80%, rgba(59, 130, 246, 0.08), transparent);
      background-attachment: fixed;
      transition: background-color 0.2s ease, color 0.2s ease;
    }
    .glass-panel {
      background: rgba(11, 15, 23, 0.75);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border: 1px solid rgba(255, 255, 255, 0.08);
      box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.7), inset 0 1px 0 0 rgba(255, 255, 255, 0.06);
    }
    .glass-card {
      background: rgba(16, 22, 34, 0.7);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(255, 255, 255, 0.07);
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05);
    }
    .glow-cyan {
      box-shadow: 0 0 30px -5px rgba(6, 182, 212, 0.4);
    }
    .glow-purple {
      box-shadow: 0 0 30px -5px rgba(168, 85, 247, 0.4);
    }
    @keyframes toastSlide {
      from { opacity: 0; transform: translateY(16px) scale(0.96); }
      to { opacity: 1; transform: translateY(0) scale(1); }
    }
    .animate-toast {
      animation: toastSlide 0.22s cubic-bezier(0.16, 1, 0.3, 1);
    }
    /* Custom scrollbars */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: rgba(0,0,0,0.2); }
    ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.14); border-radius: 9999px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.3); }

    /* ☀️ Light Mode Styles when html:not(.dark) */
    html:not(.dark) body {
      background-color: #f8fafc;
      color: #0f172a;
      background-image: 
        radial-gradient(ellipse 80% 50% at 50% -20%, rgba(6, 182, 212, 0.12), transparent),
        radial-gradient(ellipse 60% 40% at 90% 20%, rgba(168, 85, 247, 0.08), transparent),
        radial-gradient(ellipse 50% 50% at 10% 80%, rgba(59, 130, 246, 0.06), transparent);
    }
    html:not(.dark) header {
      background-color: rgba(255, 255, 255, 0.9) !important;
      border-color: rgba(226, 232, 240, 0.8) !important;
    }
    html:not(.dark) .glass-panel {
      background: rgba(255, 255, 255, 0.88);
      border-color: rgba(226, 232, 240, 0.9);
      box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.06), inset 0 1px 0 0 rgba(255, 255, 255, 0.9);
    }
    html:not(.dark) .glass-card {
      background: rgba(248, 250, 252, 0.9);
      border-color: rgba(226, 232, 240, 0.8);
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.9);
    }
    html:not(.dark) #gutter {
      background-color: rgba(248, 250, 252, 0.95) !important;
      color: #94a3b8 !important;
      border-color: #e2e8f0 !important;
    }
    html:not(.dark) #codeEditor {
      color: #0f172a !important;
    }
    html:not(.dark) .bg-dark-950,
    html:not(.dark) .bg-dark-950\/90,
    html:not(.dark) .bg-dark-950\/80,
    html:not(.dark) .bg-dark-950\/70,
    html:not(.dark) .bg-dark-950\/60 {
      background-color: rgba(248, 250, 252, 0.95) !important;
    }
    html:not(.dark) .bg-dark-900,
    html:not(.dark) .bg-dark-900\/95,
    html:not(.dark) .bg-dark-900\/98 {
      background-color: #ffffff !important;
      border-color: #e2e8f0 !important;
    }
    html:not(.dark) .bg-dark-850,
    html:not(.dark) .bg-dark-850\/80 {
      background-color: #f1f5f9 !important;
      border-color: #e2e8f0 !important;
      color: #1e293b !important;
    }
    html:not(.dark) .bg-dark-800 {
      background-color: #e2e8f0 !important;
      color: #0f172a !important;
    }
    html:not(.dark) .text-gray-100,
    html:not(.dark) .text-gray-200,
    html:not(.dark) .text-white {
      color: #0f172a !important;
    }
    html:not(.dark) .text-gray-300 {
      color: #334155 !important;
    }
    html:not(.dark) .text-gray-400 {
      color: #64748b !important;
    }
    html:not(.dark) .border-white\/10,
    html:not(.dark) .border-white\/15,
    html:not(.dark) .border-white\/\[0\.08\],
    html:not(.dark) .border-white\/\[0\.06\],
    html:not(.dark) .border-white\/\[0\.04\] {
      border-color: #e2e8f0 !important;
    }
    html:not(.dark) select option {
      background-color: #ffffff !important;
      color: #0f172a !important;
    }
  </style>
</head>
<body class="min-h-screen flex flex-col antialiased selection:bg-cyan-500/25 selection:text-cyan-200">

  <!-- Header -->
  <header class="border-b border-white/[0.08] bg-dark-950/80 sticky top-0 z-50 backdrop-blur-2xl">
    <div class="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
      
      <!-- Brand Logo -->
      <div class="flex items-center space-x-3.5">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500/20 via-blue-500/20 to-fuchsia-500/20 border border-cyan-500/40 flex items-center justify-center text-cyan-400 font-bold text-xl shadow-lg shadow-cyan-500/20">
          ⚕
        </div>
        <div>
          <div class="flex items-center space-x-2">
            <span class="font-extrabold text-xl tracking-tight text-cyan-400">DOCU</span>
            <span class="font-extrabold text-xl tracking-tight bg-gradient-to-r from-fuchsia-400 via-indigo-300 to-cyan-300 bg-clip-text text-transparent">DOCTOR</span>
            <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-cyan-950/90 text-cyan-300 border border-cyan-700/60 shadow-sm">
              v0.3.0
            </span>
          </div>
          <p class="text-[11px] text-gray-400 hidden sm:block">Code Health, Maintainability Index & Total Healer</p>
        </div>
      </div>

      <!-- Right Header Actions -->
      <div class="flex items-center space-x-3">
        <div class="hidden sm:flex items-center space-x-2 px-3 py-1.5 rounded-full bg-emerald-950/40 border border-emerald-500/30 text-emerald-400 text-xs font-semibold">
          <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span>Engine Online</span>
        </div>

        <a href="https://github.com/prasunkrghosh-18/docudoctor" target="_blank" class="hidden sm:flex items-center space-x-2 text-xs font-semibold text-gray-200 hover:text-white bg-dark-850 hover:bg-dark-800 px-3.5 py-2 rounded-xl border border-white/10 hover:border-white/20 transition-all shadow-sm">
          <svg class="w-4 h-4 fill-current" viewBox="0 0 24 24"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/></svg>
          <span>GitHub</span>
        </a>

        <!-- Theme Mode Selector Dropdown (System, Dark, Light) -->
        <div class="relative">
          <button id="themeBtn" type="button" onclick="toggleThemeMenu(event)" title="Theme: System, Dark, Light" class="flex items-center space-x-1.5 px-3 py-2 rounded-xl border border-white/10 hover:border-cyan-500/40 bg-dark-850 hover:bg-dark-800 text-xs font-semibold text-gray-200 transition-all shadow-sm cursor-pointer group">
            <span id="themeActiveIcon" class="text-sm">💻</span>
            <span id="themeActiveText" class="hidden sm:inline text-xs font-semibold">System</span>
            <svg class="w-3.5 h-3.5 text-gray-400 group-hover:text-cyan-400 transition" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
          </button>
          
          <div id="themeMenu" style="display: none;" class="absolute right-0 top-full mt-2 w-44 bg-dark-900/98 border border-white/15 rounded-2xl shadow-2xl backdrop-blur-2xl p-1.5 z-50 flex flex-col space-y-1 animate-toast">
            <button type="button" onclick="setTheme('system')" id="themeOptSystem" class="w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-semibold hover:bg-cyan-500/15 transition cursor-pointer text-left text-gray-200">
              <div class="flex items-center space-x-2.5">
                <span>💻</span><span>System</span>
              </div>
              <span id="checkSystem" class="text-cyan-400 font-bold">✓</span>
            </button>
            <button type="button" onclick="setTheme('dark')" id="themeOptDark" class="w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-semibold hover:bg-cyan-500/15 transition cursor-pointer text-left text-gray-200">
              <div class="flex items-center space-x-2.5">
                <span>🌙</span><span>Dark Mode</span>
              </div>
              <span id="checkDark" class="hidden text-cyan-400 font-bold">✓</span>
            </button>
            <button type="button" onclick="setTheme('light')" id="themeOptLight" class="w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-semibold hover:bg-cyan-500/15 transition cursor-pointer text-left text-gray-200">
              <div class="flex items-center space-x-2.5">
                <span>☀️</span><span>Light Mode</span>
              </div>
              <span id="checkLight" class="hidden text-cyan-400 font-bold">✓</span>
            </button>
          </div>
        </div>

        <!-- Rightmost User Avatar & Profile Reveal Dropdown -->
        <div class="relative">
          <button id="profileDropdownBtn" onclick="toggleProfileDropdown(event)" title="Developer Profile" class="flex items-center focus:outline-none ring-2 ring-white/10 hover:ring-cyan-400 p-0.5 rounded-full transition-all group shadow-sm bg-dark-850">
            <img src="https://github.com/prasunkrghosh-18.png" alt="Prasun Kumar Ghosh" class="w-8 h-8 rounded-full object-cover" onerror="this.onerror=null; this.src='https://ui-avatars.com/api/?name=Prasun+Kumar+Ghosh&background=06b6d4&color=fff'">
          </button>

          <!-- Profile Reveal Popover -->
          <div id="profileDropdown" style="display: none;" class="absolute right-0 top-full mt-2.5 w-80 bg-dark-900/98 border border-white/15 rounded-2xl shadow-2xl backdrop-blur-2xl p-4 z-50 animate-toast">
            <!-- User Header -->
            <div class="flex items-center space-x-3 pb-3 border-b border-white/[0.08]">
              <div class="relative">
                <img src="https://github.com/prasunkrghosh-18.png" alt="Prasun Kumar Ghosh" class="w-12 h-12 rounded-full border-2 border-cyan-400/70 shadow-md shadow-cyan-500/20 object-cover bg-dark-850" onerror="this.onerror=null; this.src='https://ui-avatars.com/api/?name=Prasun+Kumar+Ghosh&background=06b6d4&color=fff'">
                <span class="absolute bottom-0 right-0 w-3 h-3 rounded-full bg-emerald-400 border-2 border-dark-900" title="Active"></span>
              </div>
              <div class="flex-1 min-w-0">
                <div class="flex items-center justify-between">
                  <h4 class="font-extrabold text-sm text-white truncate">Prasun Kumar Ghosh</h4>
                  <span class="px-1.5 py-0.5 rounded text-[9px] font-bold bg-cyan-950 text-cyan-300 border border-cyan-700/60">AUTHOR</span>
                </div>
                <p class="text-xs text-gray-400 font-mono">@prasunkrghosh-18</p>
                <p class="text-[11px] text-gray-500 mt-0.5">Creator of DocuDoctor</p>
              </div>
            </div>

            <!-- Bio Details -->
            <div class="py-3 text-xs text-gray-300 leading-relaxed border-b border-white/[0.08]">
              <p>Creator & Lead Developer of <span class="text-cyan-400 font-semibold">DocuDoctor</span>. Building intelligent multi-language docstring synthesis and automated code health tools.</p>
              <div class="mt-2.5 flex flex-wrap gap-1.5">
                <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-dark-800 text-cyan-300 border border-cyan-800/30">Python</span>
                <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-dark-800 text-blue-300 border border-blue-800/30">C</span>
                <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-dark-800 text-indigo-300 border border-indigo-800/30">C++</span>
                <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-dark-800 text-amber-300 border border-amber-800/30">Java</span>
              </div>
            </div>

            <!-- Profile Actions -->
            <div class="pt-3 flex flex-col space-y-2">
              <a href="https://github.com/prasunkrghosh-18" target="_blank" class="w-full text-center text-xs font-semibold text-white bg-cyan-600 hover:bg-cyan-500 py-2 rounded-xl transition shadow-md shadow-cyan-950/60 flex items-center justify-center space-x-1.5">
                <span>View GitHub Profile</span>
                <span>↗</span>
              </a>
              <a href="https://github.com/prasunkrghosh-18/docudoctor" target="_blank" class="w-full text-center text-xs font-semibold text-gray-300 hover:text-white bg-dark-850 hover:bg-dark-800 py-2 rounded-xl border border-white/10 transition flex items-center justify-center space-x-1.5">
                <span>⭐ Star DocuDoctor Repo</span>
              </a>
            </div>
          </div>
        </div>

      </div>
    </div>
  </header>

  <!-- Main Container -->
  <main class="max-w-7xl mx-auto px-6 py-6 flex-1 w-full flex flex-col gap-6">

    <!-- Unified Command & Control Bar -->
    <div class="glass-panel p-3 rounded-2xl flex flex-wrap items-center justify-between gap-4 relative z-40">
      
      <!-- Left: Choose Language & File Controls -->
      <div class="flex flex-wrap items-center gap-3">
        
        <!-- Premium Choose Language Dropdown Selector -->
        <div class="flex items-center space-x-2.5 bg-dark-900/95 hover:bg-dark-850 border border-white/10 hover:border-cyan-500/50 rounded-xl px-3.5 py-2 transition-all shadow-inner group">
          <span class="text-lg select-none" id="langEmojiIcon">🐍</span>
          <div class="flex flex-col">
            <span class="text-[9px] text-gray-400 uppercase tracking-wider font-extrabold leading-none">Choose Language</span>
            <select id="languageSelect" onchange="onLanguageChange(this.value, true)" class="bg-transparent text-xs font-bold text-white hover:text-cyan-300 focus:outline-none cursor-pointer mt-0.5 pr-2">
              <option value="python" class="bg-dark-900 text-white font-medium py-1">🐍 Python (.py)</option>
              <option value="c" class="bg-dark-900 text-white font-medium py-1">⚡ C Language (.c / .h)</option>
              <option value="cpp" class="bg-dark-900 text-white font-medium py-1">🚀 C++ (.cpp / .hpp)</option>
              <option value="java" class="bg-dark-900 text-white font-medium py-1">☕ Java (.java)</option>
            </select>
          </div>
        </div>

        <!-- Hidden input for file upload -->
        <input type="file" id="fileInput" accept=".py,.c,.h,.cpp,.hpp,.cc,.java" class="hidden" onchange="handleFileUpload(event)">

        <button onclick="document.getElementById('fileInput').click()" class="bg-dark-850 hover:bg-dark-800 text-gray-300 hover:text-white text-xs font-semibold px-3.5 py-2.5 rounded-xl border border-white/10 hover:border-white/20 transition flex items-center space-x-1.5 shadow-sm cursor-pointer">
          <span>📁</span><span>Upload File</span>
        </button>

        <button onclick="loadSampleForLanguage()" class="bg-dark-850 hover:bg-dark-800 text-cyan-400 hover:text-cyan-300 text-xs font-semibold px-3.5 py-2.5 rounded-xl border border-white/10 hover:border-cyan-500/30 transition flex items-center space-x-1.5 shadow-sm cursor-pointer">
          <span>📂</span><span>Load Sample</span>
        </button>

        <button onclick="clearEditor()" class="text-xs text-gray-400 hover:text-white px-2.5 py-2 transition font-medium cursor-pointer">
          Clear
        </button>
      </div>

      <!-- Right: Doc Style & Action Buttons -->
      <div class="flex flex-wrap items-center gap-2.5">
        
        <!-- Style Picker -->
        <div class="flex items-center space-x-2 bg-dark-900 border border-white/10 rounded-xl px-3 py-2 shadow-inner">
          <label class="text-[11px] text-gray-400 font-medium">Style:</label>
          <select id="docStyle" class="bg-transparent text-xs text-cyan-400 font-semibold focus:outline-none cursor-pointer">
            <option value="google" class="bg-dark-900 text-gray-200">Google Style</option>
            <option value="numpy" class="bg-dark-900 text-gray-200">NumPy Style</option>
            <option value="sphinx" class="bg-dark-900 text-gray-200">Sphinx Style</option>
          </select>
        </div>

        <!-- Audit Button -->
        <button onclick="auditCode()" class="bg-gradient-to-r from-cyan-600 via-cyan-500 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-bold text-xs px-4 py-2.5 rounded-xl transition-all flex items-center space-x-2 shadow-lg shadow-cyan-950/80 hover:shadow-cyan-500/30 active:scale-95 cursor-pointer">
          <span>🔍</span><span>Audit Code</span>
        </button>

        <!-- Total Healer Button -->
        <button onclick="fixCode()" title="Heals missing docstrings, dangerous mutable defaults, and infers type annotations" class="bg-gradient-to-r from-fuchsia-600 via-purple-600 to-indigo-600 hover:from-fuchsia-500 hover:to-indigo-500 text-white font-bold text-xs px-4 py-2.5 rounded-xl transition-all flex items-center space-x-2 shadow-lg shadow-fuchsia-950/80 hover:shadow-fuchsia-500/30 active:scale-95 cursor-pointer">
          <span>⚡</span><span>Total Healer</span>
        </button>

        <!-- Export Markdown Report Button -->
        <button onclick="exportMarkdownReport()" title="Generate & Download full GitHub-ready Markdown audit report" class="bg-dark-850 hover:bg-dark-800 text-gray-200 hover:text-white font-semibold text-xs px-3.5 py-2.5 rounded-xl border border-white/10 hover:border-cyan-500/40 transition-all flex items-center space-x-1.5 shadow-sm cursor-pointer">
          <span>📄</span><span>Export Report</span>
        </button>
      </div>

    </div>

    <!-- Workspace Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1">

      <!-- Left Column: Modern IDE Code Editor (7 cols) -->
      <div class="lg:col-span-7 flex flex-col glass-panel rounded-2xl overflow-hidden min-h-[560px]">
        
        <!-- Editor Window Header -->
        <div class="bg-dark-950/90 border-b border-white/[0.08] px-4 py-3 flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <div class="flex items-center space-x-1.5">
              <div class="w-3 h-3 rounded-full bg-[#ff5f56] border border-red-400/30 shadow-sm"></div>
              <div class="w-3 h-3 rounded-full bg-[#ffbd2e] border border-yellow-400/30 shadow-sm"></div>
              <div class="w-3 h-3 rounded-full bg-[#27c93f] border border-green-400/30 shadow-sm"></div>
            </div>
            <div class="flex items-center space-x-2 pl-3 border-l border-white/10">
              <span id="fileIcon">🐍</span>
              <span id="fileNameDisplay" class="text-xs font-mono font-medium text-gray-200">main.py</span>
            </div>
          </div>

          <div class="flex items-center space-x-3 text-[11px] text-gray-500 font-mono">
            <span id="lineCountDisplay">Lines: 1</span>
            <span>•</span>
            <span id="charCountDisplay">Chars: 0</span>
            <button onclick="downloadCode()" title="Download file" class="text-gray-400 hover:text-cyan-400 transition ml-2">
              📥
            </button>
          </div>
        </div>

        <!-- Editor with Synced Line Gutter -->
        <div class="flex-1 flex bg-dark-950/60 relative">
          <div id="gutter" class="py-4 px-2 select-none font-mono text-xs text-gray-600 bg-dark-950/90 border-r border-white/[0.06] text-right min-w-[2.75rem]">
            1
          </div>
          <textarea id="codeEditor" oninput="updateGutter()" onscroll="syncGutterScroll()" class="w-full flex-1 bg-transparent text-gray-100 p-4 text-xs md:text-sm leading-relaxed focus:outline-none resize-none font-mono selection:bg-cyan-900/60" spellcheck="false" placeholder="# Paste code here, load a sample, or upload a .py, .c, .cpp, or .java file..."></textarea>
        </div>
      </div>

      <!-- Right Column: Health Scorecard & Issue Inspector (5 cols) -->
      <div class="lg:col-span-5 flex flex-col gap-5">

        <!-- Scorecard Card -->
        <div class="glass-panel p-5 rounded-2xl flex items-center justify-between relative overflow-hidden">
          <div>
            <span class="text-[11px] uppercase tracking-wider text-gray-400 font-bold">Documentation Health</span>
            <div class="flex items-baseline space-x-2 mt-1">
              <span id="scoreVal" class="text-4xl font-extrabold tracking-tight text-cyan-400">--</span>
              <span class="text-xs font-semibold text-gray-500">/ 100</span>
            </div>
            <div id="gradeBadge" class="mt-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-dark-850 text-gray-400 border border-white/10">
              Awaiting Audit
            </div>
          </div>

          <!-- Circular Metric Graphic -->
          <div class="relative w-24 h-24 flex items-center justify-center">
            <svg class="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
              <path class="text-dark-850" stroke-width="3.2" stroke="currentColor" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"/>
              <path id="circleProgress" class="text-cyan-400 transition-all duration-700 ease-out" stroke-dasharray="0, 100" stroke-width="3.2" stroke-linecap="round" stroke="currentColor" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"/>
            </svg>
            <span id="gradeLetter" class="absolute text-2xl font-black text-white">?</span>
          </div>
        </div>

        <!-- 3 Metrics Grid -->
        <div class="grid grid-cols-3 gap-2.5">
          <div class="glass-card p-3 rounded-xl text-center">
            <span class="text-[10px] text-gray-400 font-medium">Functions</span>
            <p id="statFuncs" class="text-base font-bold text-gray-100 mt-0.5">--</p>
          </div>
          <div class="glass-card p-3 rounded-xl text-center">
            <span class="text-[10px] text-gray-400 font-medium">Documented</span>
            <p id="statDocs" class="text-base font-bold text-emerald-400 mt-0.5">--</p>
          </div>
          <div class="glass-card p-3 rounded-xl text-center">
            <span class="text-[10px] text-gray-400 font-medium">Typed Returns</span>
            <p id="statTyped" class="text-base font-bold text-fuchsia-400 mt-0.5">--</p>
          </div>
        </div>

        <!-- Maintainability Index & Complexity Strip -->
        <div class="glass-card p-3.5 rounded-xl flex items-center justify-between text-xs border border-white/5 shadow-sm">
          <div class="flex items-center space-x-2.5">
            <div class="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-sm shadow-sm">
              🧠
            </div>
            <div>
              <span class="text-[9px] text-gray-400 font-bold uppercase tracking-wider block">Maintainability</span>
              <div class="flex items-center space-x-1.5">
                <span id="statMaintainability" class="font-extrabold text-white text-sm">-- / 100</span>
                <span id="statMiGrade" class="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800/40">Grade -</span>
              </div>
            </div>
          </div>
          <div class="text-right">
            <span class="text-[9px] text-gray-400 font-bold uppercase tracking-wider block">Avg Complexity</span>
            <div class="flex items-center space-x-1.5 justify-end">
              <span id="statComplexity" class="font-extrabold text-white text-sm">--</span>
              <span id="complexityStatus" class="text-[10px] font-semibold text-emerald-400">Low Risk</span>
            </div>
          </div>
        </div>

        <!-- Detailed Issue List Card -->
        <div class="glass-panel rounded-2xl flex-1 flex flex-col overflow-hidden max-h-[320px]">
          <div class="px-4 py-2.5 border-b border-white/[0.08] flex items-center justify-between bg-dark-950/70">
            <div class="flex items-center space-x-1.5">
              <button onclick="setFilter('all')" id="filterAll" class="text-[11px] font-semibold text-cyan-400 bg-cyan-950/80 px-2.5 py-1 rounded-lg border border-cyan-700/50">All (<span id="countAll">0</span>)</button>
              <button onclick="setFilter('error')" id="filterError" class="text-[11px] font-semibold text-gray-400 hover:text-red-400 px-2 py-1 rounded-lg">Errors (<span id="countError">0</span>)</button>
              <button onclick="setFilter('warning')" id="filterWarning" class="text-[11px] font-semibold text-gray-400 hover:text-amber-400 px-2 py-1 rounded-lg">Warnings (<span id="countWarning">0</span>)</button>
            </div>
            <span id="issueCountBadge" class="text-xs bg-dark-850 text-gray-400 px-2.5 py-0.5 rounded-full border border-white/10">0 issues</span>
          </div>

          <div id="issuesContainer" class="p-3.5 overflow-y-auto space-y-2.5 flex-1 text-xs">
            <p class="text-gray-500 text-center py-10">No code analyzed yet.<br>Click <b>Load Sample</b> or paste code, then click <b>Audit Code</b>.</p>
          </div>
        </div>

      </div>
    </div>

    <!-- Proposed Diff Output (Visible after Fix) -->
    <div id="diffSection" class="glass-panel rounded-2xl overflow-hidden hidden">
      <div class="bg-dark-950/90 px-4 py-3.5 border-b border-white/[0.08] flex items-center justify-between">
        <div class="flex items-center space-x-2">
          <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
          <span class="text-xs font-bold text-cyan-400 tracking-wide uppercase">Proposed Patch & Diff Preview</span>
        </div>
        <div class="flex items-center space-x-2">
          <button onclick="downloadCode()" class="text-xs bg-dark-850 hover:bg-dark-800 text-gray-200 px-3 py-1.5 rounded-lg border border-white/10 transition flex items-center space-x-1.5 cursor-pointer">
            <span>📥</span><span>Download Code</span>
          </button>
          <button onclick="exportMarkdownReport()" class="text-xs bg-dark-850 hover:bg-dark-800 text-cyan-300 px-3 py-1.5 rounded-lg border border-cyan-500/30 transition flex items-center space-x-1.5 cursor-pointer">
            <span>📄</span><span>Export Report</span>
          </button>
          <button onclick="copyPatchedCode()" class="text-xs bg-cyan-950/80 hover:bg-cyan-900 text-cyan-300 px-3 py-1.5 rounded-lg border border-cyan-700/50 transition flex items-center space-x-1.5 cursor-pointer">
            <span>📋</span><span>Copy</span>
          </button>
        </div>
      </div>
      <div class="p-4 bg-dark-950/90 overflow-x-auto">
        <pre id="diffOutput" class="text-xs leading-relaxed font-mono whitespace-pre text-gray-300"></pre>
      </div>
    </div>

  </main>

  <!-- Toast Notification Box -->
  <div id="toastBox" class="fixed bottom-6 right-6 z-50 flex flex-col space-y-2 pointer-events-none"></div>

  <script>
    let currentLanguage = 'python';
    let currentIssues = [];
    let activeFilter = 'all';
    let lastPatchedCode = "";

    const SAMPLES = {
      python: `class PaymentGateway:
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
    return True`,

      c: `#include <stdio.h>
#include <string.h>

double calculate_discount(double price, double discount_percent) {
    double discount = price * (discount_percent / 100.0);
    return price - discount;
}

int process_transaction(const char* user_id, double amount, int retry_count) {
    if (amount <= 0.0) {
        return -1;
    }
    printf("Processed transaction for %s: $%.2f\\n", user_id, amount);
    return 1;
}

void reset_gateway_cache(void) {
    // Reset cache memory
}`,

      cpp: `#include <string>
#include <vector>

class OrderManager {
public:
    double compute_subtotal(const std::vector<double>& items, double tax_rate) {
        double total = 0.0;
        for (double price : items) {
            total += price;
        }
        return total * (1.0 + tax_rate);
    }

    bool cancel_order(const std::string& order_id, bool refund_immediate) {
        return true;
    }
};

void send_alert(const std::string& message) {
    // Dispatches critical alert
}`,

      java: `package com.docudoctor.example;

import java.util.List;

public class PaymentService {

    public double calculateTotal(double subtotal, double taxRate) {
        return subtotal * (1.0 + taxRate);
    }

    public boolean executeTransaction(String customerId, double totalAmount) {
        if (totalAmount <= 0) {
            return false;
        }
        return true;
    }

    private void logSecurityAudit(String eventId) {
        System.out.println("Security event: " + eventId);
    }
}`
    };

    const LANG_CONFIG = {
      python: { ext: 'py', icon: '🐍', label: 'Python', name: 'main.py', styles: ['Google Style', 'NumPy Style', 'Sphinx Style'], styleValues: ['google', 'numpy', 'sphinx'] },
      c: { ext: 'c', icon: '⚡', label: 'C Language', name: 'main.c', styles: ['Doxygen Style (@brief)'], styleValues: ['doxygen'] },
      cpp: { ext: 'cpp', icon: '🚀', label: 'C++', name: 'main.cpp', styles: ['Doxygen Style (@brief)'], styleValues: ['doxygen'] },
      java: { ext: 'java', icon: '☕', label: 'Java', name: 'PaymentService.java', styles: ['Standard Javadoc'], styleValues: ['javadoc'] }
    };

    let currentThemeMode = 'system';

    function initTheme() {
      const saved = localStorage.getItem('docudoctor_theme') || 'system';
      setTheme(saved, false);
    }

    function setTheme(mode, showNotification = true) {
      currentThemeMode = mode;
      localStorage.setItem('docudoctor_theme', mode);

      let effectiveTheme = mode;
      if (mode === 'system') {
        const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
        effectiveTheme = prefersDark ? 'dark' : 'light';
      }

      if (effectiveTheme === 'dark') {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }

      const iconEl = document.getElementById('themeActiveIcon');
      const textEl = document.getElementById('themeActiveText');
      if (iconEl) iconEl.innerText = mode === 'system' ? '💻' : (mode === 'dark' ? '🌙' : '☀️');
      if (textEl) textEl.innerText = mode === 'system' ? 'System' : (mode === 'dark' ? 'Dark' : 'Light');

      const checkSystem = document.getElementById('checkSystem');
      const checkDark = document.getElementById('checkDark');
      const checkLight = document.getElementById('checkLight');
      if (checkSystem) checkSystem.className = mode === 'system' ? 'text-cyan-400 font-bold' : 'hidden';
      if (checkDark) checkDark.className = mode === 'dark' ? 'text-cyan-400 font-bold' : 'hidden';
      if (checkLight) checkLight.className = mode === 'light' ? 'text-cyan-400 font-bold' : 'hidden';

      closeThemeMenu();

      if (showNotification) {
        const label = mode === 'system' ? '💻 System Default' : (mode === 'dark' ? '🌙 Dark Mode' : '☀️ Light Mode');
        showToast(`Theme updated to ${label}`, "cyan");
      }
    }

    function toggleThemeMenu(event) {
      if (event) event.stopPropagation();
      closeProfileDropdown();
      const menu = document.getElementById('themeMenu');
      if (!menu) return;
      const isVisible = menu.style.display === 'flex';
      menu.style.display = isVisible ? 'none' : 'flex';
    }

    function closeThemeMenu() {
      const menu = document.getElementById('themeMenu');
      if (menu) menu.style.display = 'none';
    }

    if (window.matchMedia) {
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        if (currentThemeMode === 'system') {
          setTheme('system', false);
        }
      });
    }

    function toggleProfileDropdown(event) {
      if (event) {
        event.stopPropagation();
      }
      closeThemeMenu();
      const menu = document.getElementById('profileDropdown');
      if (!menu) return;
      const isVisible = menu.style.display === 'block';
      menu.style.display = isVisible ? 'none' : 'block';
    }

    function closeProfileDropdown() {
      const menu = document.getElementById('profileDropdown');
      if (menu) menu.style.display = 'none';
    }

    // Global outside click handler for profile & theme popovers
    document.addEventListener('click', (e) => {
      const profMenu = document.getElementById('profileDropdown');
      const profBtn = document.getElementById('profileDropdownBtn');
      if (profMenu && !profMenu.contains(e.target) && (!profBtn || !profBtn.contains(e.target))) {
        profMenu.style.display = 'none';
      }

      const themeMenu = document.getElementById('themeMenu');
      const themeBtn = document.getElementById('themeBtn');
      if (themeMenu && !themeMenu.contains(e.target) && (!themeBtn || !themeBtn.contains(e.target))) {
        themeMenu.style.display = 'none';
      }
    });

    function onLanguageChange(lang, autoLoad = true) {
      currentLanguage = lang;
      const conf = LANG_CONFIG[lang] || LANG_CONFIG.python;

      // Update active emoji icon
      const iconEl = document.getElementById('langEmojiIcon');
      if (iconEl) iconEl.innerText = conf.icon;

      // Sync the select element value
      const sel = document.getElementById('languageSelect');
      if (sel && sel.value !== lang) sel.value = lang;

      // Update mock editor tab filename and icon
      const fileIcon = document.getElementById('fileIcon');
      if (fileIcon) fileIcon.innerText = conf.icon;
      const fileNameDisplay = document.getElementById('fileNameDisplay');
      if (fileNameDisplay) fileNameDisplay.innerText = conf.name;

      // Update Styles Dropdown options
      const styleSelect = document.getElementById('docStyle');
      if (styleSelect) {
        styleSelect.innerHTML = conf.styles.map((name, i) => `<option value="${conf.styleValues[i]}" class="bg-dark-900 text-gray-200">${name}</option>`).join('');
      }

      // Automatically load the code sample for this language if requested
      if (autoLoad) {
        const sampleCode = SAMPLES[lang] || SAMPLES.python;
        document.getElementById('codeEditor').value = sampleCode;
        updateGutter();
        flashEditor();
        auditCode();
      }

      showToast(`Selected ${conf.icon} ${conf.label}`, "cyan");
    }

    // Alias for compatibility
    function selectLanguage(lang, autoLoad = true) {
      onLanguageChange(lang, autoLoad);
    }

    function loadSampleForLanguage() {
      onLanguageChange(currentLanguage, true);
    }

    function handleFileUpload(event) {
      const file = event.target.files[0];
      if (!file) return;

      const filename = file.name;
      let detectedLang = 'python';
      if (filename.endsWith('.java')) detectedLang = 'java';
      else if (filename.endsWith('.cpp') || filename.endsWith('.hpp') || filename.endsWith('.cc')) detectedLang = 'cpp';
      else if (filename.endsWith('.c') || filename.endsWith('.h')) detectedLang = 'c';

      onLanguageChange(detectedLang, false);
      document.getElementById('fileNameDisplay').innerText = filename;

      const reader = new FileReader();
      reader.onload = function(e) {
        document.getElementById('codeEditor').value = e.target.result;
        updateGutter();
        flashEditor();
        showToast(`Loaded ${filename} (${detectedLang.toUpperCase()})`, "emerald");
        auditCode();
      };
      reader.readAsText(file);
    }

    function updateGutter() {
      const editor = document.getElementById('codeEditor');
      const text = editor.value;
      const lines = text.split('\\n').length || 1;
      const gutter = document.getElementById('gutter');

      let gutterHtml = '';
      for (let i = 1; i <= lines; i++) {
        gutterHtml += `<div>${i}</div>`;
      }
      gutter.innerHTML = gutterHtml;

      document.getElementById('lineCountDisplay').innerText = `Lines: ${lines}`;
      document.getElementById('charCountDisplay').innerText = `Chars: ${text.length}`;
    }

    function syncGutterScroll() {
      const editor = document.getElementById('codeEditor');
      const gutter = document.getElementById('gutter');
      gutter.scrollTop = editor.scrollTop;
    }

    function flashEditor() {
      const editor = document.getElementById('codeEditor');
      editor.classList.add('ring-2', 'ring-cyan-500');
      setTimeout(() => editor.classList.remove('ring-2', 'ring-cyan-500'), 450);
    }

    function clearEditor() {
      document.getElementById('codeEditor').value = "";
      updateGutter();
      document.getElementById('scoreVal').innerText = "--";
      document.getElementById('gradeLetter').innerText = "?";
      document.getElementById('gradeBadge').innerText = "Awaiting Code";
      document.getElementById('circleProgress').setAttribute('stroke-dasharray', '0, 100');
      document.getElementById('statFuncs').innerText = "--";
      document.getElementById('statDocs').innerText = "--";
      document.getElementById('statTyped').innerText = "--";
      document.getElementById('statMaintainability').innerText = "-- / 100";
      document.getElementById('statMiGrade').innerText = "Grade -";
      document.getElementById('statComplexity').innerText = "--";
      document.getElementById('complexityStatus').innerText = "Awaiting Audit";
      document.getElementById('countAll').innerText = "0";
      document.getElementById('countError').innerText = "0";
      document.getElementById('countWarning').innerText = "0";
      document.getElementById('issueCountBadge').innerText = "0 issues";
      document.getElementById('issuesContainer').innerHTML = `<p class="text-gray-500 text-center py-10">No code analyzed yet.<br>Click <b>Load Sample</b> or paste code, then click <b>Audit Code</b>.</p>`;
      document.getElementById('diffSection').classList.add('hidden');
      currentIssues = [];
      showToast("Editor cleared.", "gray");
    }

    async function auditCode() {
      const code = document.getElementById('codeEditor').value;
      if (!code.trim()) {
        showToast("Please enter or upload code first!", "amber");
        return;
      }

      try {
        const res = await fetch('/api/audit', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ code, language: currentLanguage })
        });
        const data = await res.json();
        if (!res.ok) {
          showToast(data.detail || "Audit syntax error.", "red");
          return;
        }

        currentIssues = data.issues || [];
        renderDashboard(data);
        renderIssues();
        showToast(`Audit complete: Health ${data.score}% • Maintainability ${data.maintainability_index}%`, "emerald");
      } catch (err) {
        showToast("Error connecting to server: " + err.message, "red");
      }
    }

    function renderDashboard(data) {
      document.getElementById('scoreVal').innerText = data.score;
      document.getElementById('gradeLetter').innerText = data.grade;
      document.getElementById('gradeLetter').style.color = data.color;

      const badge = document.getElementById('gradeBadge');
      badge.innerText = `${data.label} (Grade ${data.grade})`;
      badge.style.color = data.color;
      badge.style.borderColor = `${data.color}50`;
      badge.style.backgroundColor = `${data.color}15`;

      document.getElementById('circleProgress').setAttribute('stroke-dasharray', `${data.score}, 100`);
      document.getElementById('circleProgress').style.color = data.color;

      document.getElementById('statFuncs').innerText = data.total_functions;
      document.getElementById('statDocs').innerText = `${data.documented_functions}/${data.total_functions}`;
      document.getElementById('statTyped').innerText = `${data.typed_returns}/${data.total_functions}`;

      // Maintainability & Complexity Strip
      document.getElementById('statMaintainability').innerText = `${data.maintainability_index} / 100`;
      document.getElementById('statMiGrade').innerText = `Grade ${data.maintainability_grade}`;
      document.getElementById('statComplexity').innerText = data.avg_complexity;

      const compStatus = document.getElementById('complexityStatus');
      const avgComp = data.avg_complexity || 1.0;
      if (avgComp <= 5) {
        compStatus.innerText = 'Low Risk';
        compStatus.className = 'text-[10px] font-semibold text-emerald-400';
      } else if (avgComp <= 10) {
        compStatus.innerText = 'Moderate';
        compStatus.className = 'text-[10px] font-semibold text-amber-400';
      } else {
        compStatus.innerText = 'High Risk';
        compStatus.className = 'text-[10px] font-semibold text-red-400';
      }

      document.getElementById('issueCountBadge').innerText = `${data.issues.length} issues`;

      document.getElementById('countAll').innerText = data.issues.length;
      document.getElementById('countError').innerText = data.issues.filter(i => i.severity === 'ERROR').length;
      document.getElementById('countWarning').innerText = data.issues.filter(i => i.severity === 'WARNING').length;
    }

    function setFilter(filter) {
      activeFilter = filter;
      const btnAll = document.getElementById('filterAll');
      const btnErr = document.getElementById('filterError');
      const btnWrn = document.getElementById('filterWarning');

      btnAll.className = filter === 'all' ? 'text-[11px] font-semibold text-cyan-400 bg-cyan-950/80 px-2.5 py-1 rounded-lg border border-cyan-700/50' : 'text-[11px] font-semibold text-gray-400 hover:text-white px-2 py-1 rounded-lg';
      btnErr.className = filter === 'error' ? 'text-[11px] font-semibold text-red-400 bg-red-950/80 px-2.5 py-1 rounded-lg border border-red-700/50' : 'text-[11px] font-semibold text-gray-400 hover:text-red-400 px-2 py-1 rounded-lg';
      btnWrn.className = filter === 'warning' ? 'text-[11px] font-semibold text-amber-400 bg-amber-950/80 px-2.5 py-1 rounded-lg border border-amber-700/50' : 'text-[11px] font-semibold text-gray-400 hover:text-amber-400 px-2 py-1 rounded-lg';

      renderIssues();
    }

    function renderIssues() {
      const container = document.getElementById('issuesContainer');
      let filtered = currentIssues;

      if (activeFilter === 'error') {
        filtered = currentIssues.filter(i => i.severity === 'ERROR');
      } else if (activeFilter === 'warning') {
        filtered = currentIssues.filter(i => i.severity === 'WARNING');
      }

      if (filtered.length === 0) {
        if (currentIssues.length === 0) {
          container.innerHTML = `<div class="p-6 text-center text-emerald-400 font-semibold">✨ All functions and classes are fully documented, typed, and clean!</div>`;
        } else {
          container.innerHTML = `<div class="p-6 text-center text-gray-400">No issues matching this filter.</div>`;
        }
        return;
      }

      container.innerHTML = filtered.map(iss => {
        let badgeColor = iss.severity === "ERROR" ? "bg-red-950/80 text-red-300 border-red-700/60" : (iss.severity === "WARNING" ? "bg-amber-950/80 text-amber-300 border-amber-700/60" : "bg-cyan-950/80 text-cyan-300 border-cyan-700/60");

        let fixBtnHtml = "";
        if (iss.can_fix) {
          let btnLabel = "Fix Documentation";
          if (iss.issue_type === "Mutable Default Arg") btnLabel = "Heal Mutable Default";
          else if (iss.issue_type === "Missing Return Type") btnLabel = "Infer Return Type";
          else if (iss.issue_type === "Missing Docstring") btnLabel = "Inject Docstring";

          fixBtnHtml = `
            <button onclick="fixSpecific('${iss.entity}')" class="mt-2 text-[11px] font-semibold bg-fuchsia-950/80 hover:bg-fuchsia-800 text-fuchsia-200 border border-fuchsia-600/50 px-3 py-1 rounded-lg flex items-center space-x-1.5 transition shadow-sm w-fit active:scale-95 cursor-pointer">
              <span>⚡</span><span>${btnLabel}</span>
            </button>
          `;
        }

        return `
          <div class="p-3 rounded-xl bg-dark-850/80 border border-white/[0.06] flex flex-col space-y-1.5 hover:border-white/10 transition">
            <div class="flex items-center justify-between">
              <div class="flex items-center space-x-2">
                <span class="px-2 py-0.5 rounded-md text-[10px] font-bold border ${badgeColor}">Line ${iss.line}</span>
                <span class="text-cyan-300 font-mono font-semibold">${iss.entity}</span>
                <span class="text-gray-500 text-[11px]">(${iss.entity_type})</span>
              </div>
              <span class="text-[10px] uppercase font-bold text-gray-500 tracking-wider">${iss.issue_type}</span>
            </div>

            <p class="text-gray-300 text-xs leading-relaxed">${iss.message}</p>
            <div class="p-2 rounded-lg bg-dark-950/70 border border-white/[0.04] text-gray-400 text-[11px] italic">
              💡 ${iss.recommendation}
            </div>

            ${fixBtnHtml}
          </div>
        `;
      }).join('');
    }

    async function fixSpecific(entityName) {
      const code = document.getElementById('codeEditor').value;
      const style = document.getElementById('docStyle').value;

      try {
        const res = await fetch('/api/fix', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ code, language: currentLanguage, style, target: entityName })
        });
        const data = await res.json();
        if (!res.ok) {
          showToast(data.detail || "Fix failed.", "red");
          return;
        }

        lastPatchedCode = data.patched_code;
        document.getElementById('codeEditor').value = data.patched_code;
        updateGutter();
        flashEditor();

        // Render Diff
        const diffSection = document.getElementById('diffSection');
        diffSection.classList.remove('hidden');

        const diffEl = document.getElementById('diffOutput');
        diffEl.innerHTML = data.diff.split('\\n').map(line => {
          if (line.startsWith('+')) return `<span class="text-emerald-400 font-medium">${escapeHtml(line)}</span>`;
          if (line.startsWith('-')) return `<span class="text-red-400 font-medium">${escapeHtml(line)}</span>`;
          if (line.startsWith('@')) return `<span class="text-cyan-400 font-semibold">${escapeHtml(line)}</span>`;
          return `<span class="text-gray-500">${escapeHtml(line)}</span>`;
        }).join('\\n');

        showToast(`✨ Generated documentation for '${entityName}'!`, "fuchsia");
        auditCode();
      } catch (err) {
        showToast("Error fixing: " + err.message, "red");
      }
    }

    async function fixCode() {
      const code = document.getElementById('codeEditor').value;
      if (!code.trim()) {
        showToast("Please enter or upload code first!", "amber");
        return;
      }
      const style = document.getElementById('docStyle').value;

      try {
        const res = await fetch('/api/fix', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ code, language: currentLanguage, style })
        });
        const data = await res.json();
        if (!res.ok) {
          showToast(data.detail || "Fix failed.", "red");
          return;
        }

        lastPatchedCode = data.patched_code;
        document.getElementById('codeEditor').value = data.patched_code;
        updateGutter();
        flashEditor();

        // Render Diff
        const diffSection = document.getElementById('diffSection');
        diffSection.classList.remove('hidden');

        const diffEl = document.getElementById('diffOutput');
        diffEl.innerHTML = data.diff.split('\\n').map(line => {
          if (line.startsWith('+')) return `<span class="text-emerald-400 font-medium">${escapeHtml(line)}</span>`;
          if (line.startsWith('-')) return `<span class="text-red-400 font-medium">${escapeHtml(line)}</span>`;
          if (line.startsWith('@')) return `<span class="text-cyan-400 font-semibold">${escapeHtml(line)}</span>`;
          return `<span class="text-gray-500">${escapeHtml(line)}</span>`;
        }).join('\\n');

        showToast(`✨ Successfully patched ${data.patched_count} item(s)!`, "fuchsia");
        auditCode();
      } catch (err) {
        showToast("Error generating docs: " + err.message, "red");
      }
    }

    function copyPatchedCode() {
      const codeToCopy = lastPatchedCode || document.getElementById('codeEditor').value;
      if (!codeToCopy) return showToast("No code to copy.", "amber");
      navigator.clipboard.writeText(codeToCopy).then(() => {
        showToast("📋 Copied code to clipboard!", "emerald");
      });
    }

    function downloadCode() {
      const codeToDownload = document.getElementById('codeEditor').value;
      if (!codeToDownload.trim()) return showToast("No code to download.", "amber");

      const conf = LANG_CONFIG[currentLanguage] || LANG_CONFIG.python;
      const blob = new Blob([codeToDownload], { type: 'text/plain;charset=utf-8' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `healed_${conf.name}`;
      a.click();
      URL.revokeObjectURL(a.href);
      showToast(`📥 Downloaded healed_${conf.name}`, "emerald");
    }

    async function exportMarkdownReport() {
      const code = document.getElementById('codeEditor').value;
      if (!code.trim()) {
        showToast("Enter or load code before generating report!", "amber");
        return;
      }

      const conf = LANG_CONFIG[currentLanguage] || LANG_CONFIG.python;
      try {
        const res = await fetch('/api/report', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            code: code,
            language: currentLanguage,
            filename: conf.name,
          })
        });
        const data = await res.json();
        if (!res.ok) {
          showToast(data.detail || "Failed to generate report.", "red");
          return;
        }

        const blob = new Blob([data.report], { type: 'text/markdown;charset=utf-8' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = data.filename || "DOCUDOCTOR_REPORT.md";
        a.click();
        URL.revokeObjectURL(a.href);
        showToast("📄 Exported " + (data.filename || "DOCUDOCTOR_REPORT.md"), "emerald");
      } catch (err) {
        showToast("Error generating report: " + err.message, "red");
      }
    }

    function showToast(message, color = "cyan") {
      const box = document.getElementById('toastBox');
      const toast = document.createElement('div');
      let accentBg = "bg-cyan-400";
      if (color === "emerald") accentBg = "bg-emerald-400";
      else if (color === "red") accentBg = "bg-red-400";
      else if (color === "amber") accentBg = "bg-amber-400";
      else if (color === "fuchsia") accentBg = "bg-fuchsia-400";

      toast.className = `animate-toast px-4 py-3 rounded-xl text-xs font-semibold text-white shadow-2xl flex items-center space-x-2.5 border border-white/10 bg-dark-900/90 backdrop-blur-xl`;
      toast.innerHTML = `<span class="w-2 h-2 rounded-full ${accentBg}"></span><span>${message}</span>`;
      box.appendChild(toast);
      setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.25s ease';
        setTimeout(() => toast.remove(), 250);
      }, 3000);
    }

    function escapeHtml(text) {
      return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    // Initialize on load
    window.addEventListener('DOMContentLoaded', () => {
      initTheme();
      onLanguageChange('python', true);
    });
  </script>
</body>
</html>
"""
