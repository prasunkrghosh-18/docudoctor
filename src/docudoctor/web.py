"""FastAPI Web Application for DocuDoctor with interactive multi-language web interface."""

import difflib
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel

from docudoctor.languages import (
    Language,
    audit_code_by_language,
    patch_code_by_language,
)
from docudoctor.reporter import generate_markdown_report
from docudoctor.complexity_estimator import analyse_complexity
from docudoctor.style_analyzer import analyze_code_style
from docudoctor.ai_engine import (
    patch_code_with_smart_ai,
    ai_deep_code_review,
    get_effective_api_key,
)

app = FastAPI(title="DocuDoctor Web", version="0.5.0")


class AuditRequest(BaseModel):
    code: str
    language: str = "python"


class FixRequest(BaseModel):
    code: str
    language: str = "python"
    style: str = "google"
    target: Optional[str] = None
    use_ai: bool = False
    api_key: Optional[str] = None


class ReportRequest(BaseModel):
    code: str
    language: str = "python"
    filename: str = "main.py"


class ComplexityRequest(BaseModel):
    code: str
    language: str = "python"


class StyleRequest(BaseModel):
    code: str
    language: str = "python"


class AIReviewRequest(BaseModel):
    code: str
    language: str = "python"
    api_key: Optional[str] = None


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
    """Patch missing documentation into code using Fast AST or Super Smart AI with AST guardrails."""
    try:
        lang = Language(req.language.lower())
    except ValueError:
        lang = Language.PYTHON

    try:
        if req.use_ai:
            patched_code, patched_count, msg = patch_code_with_smart_ai(
                req.code,
                language=lang.value,
                style=req.style,
                api_key=req.api_key,
                target=req.target,
            )
        else:
            patched_code, patched_count = patch_code_by_language(
                req.code, language=lang, style=req.style, target=req.target
            )
            msg = f"Successfully injected {patched_count} docstring(s)!"

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
            "message": msg,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/complexity")
def api_complexity(req: ComplexityRequest):
    """Estimate time and space complexity (Big-O) for each function in the code."""
    try:
        result = analyse_complexity(req.code, language=req.language)
        return {
            "overall_time": result.overall_time,
            "overall_space": result.overall_space,
            "overall_risk": result.overall_risk,
            "summary": result.summary,
            "functions": [
                {
                    "name": f.name,
                    "line": f.line,
                    "time_complexity": f.time_complexity,
                    "space_complexity": f.space_complexity,
                    "time_reason": f.time_reason,
                    "space_reason": f.space_reason,
                    "risk": f.risk,
                }
                for f in result.functions
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/style")
def api_style(req: StyleRequest):
    """Analyse code style quality — naming, structure, formatting (a.k.a. linting/PEP8)."""
    try:
        result = analyze_code_style(req.code, language=req.language)
        return {
            "style_score": result.style_score,
            "style_grade": result.style_grade,
            "style_label": result.style_label,
            "breakdown": result.breakdown,
            "issues": [
                {
                    "line": i.line,
                    "code": i.code,
                    "message": i.message,
                    "severity": i.severity,
                    "category": i.category,
                }
                for i in result.issues
            ],
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


@app.post("/api/ai-review")
def api_ai_review(req: AIReviewRequest):
    """Run semantic AI deep code review for bug risks and optimization tips."""
    try:
        res = ai_deep_code_review(req.code, language=req.language, api_key=req.api_key)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


DOCUDOCTOR_FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <defs>
    <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#060913"/>
      <stop offset="50%" stop-color="#0b1329"/>
      <stop offset="100%" stop-color="#180b2b"/>
    </linearGradient>
    <linearGradient id="c" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#22d3ee"/>
      <stop offset="100%" stop-color="#06b6d4"/>
    </linearGradient>
    <linearGradient id="p" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#c084fc"/>
      <stop offset="100%" stop-color="#9333ea"/>
    </linearGradient>
  </defs>
  <rect x="2" y="2" width="60" height="60" rx="16" fill="url(#g)" stroke="#22d3ee" stroke-width="2.5" stroke-opacity="0.8"/>
  <path d="M20 22L12 32l8 10" fill="none" stroke="url(#c)" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M44 22l8 10-8 10" fill="none" stroke="url(#p)" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M22 32h5l3-9 4 18 3-9h5" fill="none" stroke="#22d3ee" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="32" cy="13" r="3.5" fill="#c084fc"/>
</svg>"""


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    """Serves the official DocuDoctor SVG favicon for the browser title bar & tab."""
    return Response(content=DOCUDOCTOR_FAVICON_SVG, media_type="image/svg+xml")


@app.get("/", response_class=HTMLResponse)
def index():
    """Serves the interactive DocuDoctor single-page web app."""
    return HTML_CONTENT

HTML_CONTENT = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DocuDoctor • Multi-Language Code Health &amp; Docstring Engine</title>
  <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2064%2064%22%3E%3Cdefs%3E%3ClinearGradient%20id%3D%22g%22%20x1%3D%220%25%22%20y1%3D%220%25%22%20x2%3D%22100%25%22%20y2%3D%22100%25%22%3E%3Cstop%20offset%3D%220%25%22%20stop-color%3D%22%23060913%22%2F%3E%3Cstop%20offset%3D%2250%25%22%20stop-color%3D%22%230b1329%22%2F%3E%3Cstop%20offset%3D%22100%25%22%20stop-color%3D%22%23180b2b%22%2F%3E%3C%2FlinearGradient%3E%3ClinearGradient%20id%3D%22c%22%20x1%3D%220%25%22%20y1%3D%220%25%22%20x2%3D%22100%25%22%20y2%3D%22100%25%22%3E%3Cstop%20offset%3D%220%25%22%20stop-color%3D%22%2322d3ee%22%2F%3E%3Cstop%20offset%3D%22100%25%22%20stop-color%3D%22%2306b6d4%22%2F%3E%3C%2FlinearGradient%3E%3ClinearGradient%20id%3D%22p%22%20x1%3D%220%25%22%20y1%3D%220%25%22%20x2%3D%22100%25%22%20y2%3D%22100%25%22%3E%3Cstop%20offset%3D%220%25%22%20stop-color%3D%22%23c084fc%22%2F%3E%3Cstop%20offset%3D%22100%25%22%20stop-color%3D%22%239333ea%22%2F%3E%3C%2FlinearGradient%3E%3C%2Fdefs%3E%3Crect%20x%3D%222%22%20y%3D%222%22%20width%3D%2260%22%20height%3D%2260%22%20rx%3D%2216%22%20fill%3D%22url(%23g)%22%20stroke%3D%22%2322d3ee%22%20stroke-width%3D%222.5%22%20stroke-opacity%3D%220.8%22%2F%3E%3Cpath%20d%3D%22M20%2022L12%2032l8%2010%22%20fill%3D%22none%22%20stroke%3D%22url(%23c)%22%20stroke-width%3D%224.5%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%2F%3E%3Cpath%20d%3D%22M44%2022l8%2010-8%2010%22%20fill%3D%22none%22%20stroke%3D%22url(%23p)%22%20stroke-width%3D%224.5%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%2F%3E%3Cpath%20d%3D%22M22%2032h5l3-9%204%2018%203-9h5%22%20fill%3D%22none%22%20stroke%3D%22%2322d3ee%22%20stroke-width%3D%223.5%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%2F%3E%3Ccircle%20cx%3D%2232%22%20cy%3D%2213%22%20r%3D%223.5%22%20fill%3D%22%23c084fc%22%2F%3E%3C%2Fsvg%3E">
  <link rel="alternate icon" href="/favicon.ico">
  <script>
    // Immediate Theme Init — no flash on first load
    (function() {
      var saved = localStorage.getItem('docudoctor_theme') || 'system';
      var isDark = saved === 'dark' ? true : saved === 'light' ? false
                  : (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);
      if (isDark) document.documentElement.classList.add('dark');
      else document.documentElement.classList.remove('dark');
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
          fontFamily: { sans: ['Plus Jakarta Sans', 'sans-serif'], mono: ['Fira Code', 'monospace'] },
          colors: {
            dark: { 950: '#06080d', 900: '#0b0f17', 850: '#101622', 800: '#161f30', 750: '#1e293f', 700: '#25344f' }
          }
        }
      }
    }
  </script>
  <style>
    /* ═══════════════════════════════════════════════════════
       DARK THEME BASE (default)
    ═══════════════════════════════════════════════════════ */
    body {
      background-color: #06080d;
      color: #e2e8f0;
      background-image:
        radial-gradient(ellipse 80% 50% at 50% -20%, rgba(6,182,212,0.15), transparent),
        radial-gradient(ellipse 60% 40% at 90% 20%, rgba(168,85,247,0.12), transparent),
        radial-gradient(ellipse 50% 50% at 10% 80%, rgba(59,130,246,0.08), transparent);
      background-attachment: fixed;
      transition: background-color 0.25s ease, color 0.25s ease;
    }
    .glass-panel {
      background: rgba(11,15,23,0.75);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border: 1px solid rgba(255,255,255,0.08);
      box-shadow: 0 20px 40px -15px rgba(0,0,0,0.7), inset 0 1px 0 0 rgba(255,255,255,0.06);
    }
    .glass-card {
      background: rgba(16,22,34,0.7);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(255,255,255,0.07);
      transition: border-color 0.2s ease;
    }
    .glass-card:hover { border-color: rgba(255,255,255,0.14); }

    /* Scrollbars */
    ::-webkit-scrollbar { width: 5px; height: 5px; }
    ::-webkit-scrollbar-track { background: rgba(0,0,0,0.2); }
    ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.14); border-radius: 9999px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.3); }

    /* Toast animation */
    @keyframes toastIn { from { opacity:0; transform:translateY(12px); } to { opacity:1; transform:translateY(0); } }
    .animate-toast { animation: toastIn 0.22s ease both; }

    /* ═══════════════════════════════════════════════════════
       LIGHT THEME OVERRIDES
    ═══════════════════════════════════════════════════════ */
    html:not(.dark) body {
      background-color: #f1f5f9;
      color: #0f172a;
      background-image:
        radial-gradient(ellipse 80% 50% at 50% -20%, rgba(6,182,212,0.08), transparent),
        radial-gradient(ellipse 60% 40% at 90% 20%, rgba(168,85,247,0.06), transparent),
        radial-gradient(ellipse 50% 50% at 10% 80%, rgba(59,130,246,0.05), transparent);
    }
    html:not(.dark) header {
      background-color: rgba(255,255,255,0.95) !important;
      border-color: rgba(226,232,240,0.9) !important;
    }
    html:not(.dark) .glass-panel {
      background: rgba(255,255,255,0.9);
      border-color: rgba(203,213,225,0.8);
      box-shadow: 0 4px 24px -4px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.9);
    }
    html:not(.dark) .glass-card {
      background: rgba(248,250,252,0.95);
      border-color: rgba(203,213,225,0.7);
    }
    html:not(.dark) .glass-card:hover { border-color: rgba(148,163,184,0.6); }
    /* Editor */
    html:not(.dark) #gutter {
      background-color: #f8fafc !important;
      color: #94a3b8 !important;
      border-color: #e2e8f0 !important;
    }
    html:not(.dark) #codeEditor { color: #0f172a !important; }
    /* Utility bg/text overrides */
    html:not(.dark) .bg-dark-950,
    html:not(.dark) .bg-dark-900,
    html:not(.dark) .bg-dark-850,
    html:not(.dark) .bg-dark-800 { background-color: #ffffff !important; }
    html:not(.dark) .bg-dark-950\/90,
    html:not(.dark) .bg-dark-950\/80,
    html:not(.dark) .bg-dark-950\/70,
    html:not(.dark) .bg-dark-950\/60 { background-color: rgba(248,250,252,0.95) !important; }
    html:not(.dark) .bg-dark-900\/98,
    html:not(.dark) .bg-dark-900\/95 { background-color: rgba(255,255,255,0.98) !important; border-color: #e2e8f0 !important; }
    html:not(.dark) .bg-dark-850\/80 { background-color: rgba(241,245,249,0.95) !important; }
    html:not(.dark) .text-gray-100,
    html:not(.dark) .text-gray-200,
    html:not(.dark) .text-white { color: #0f172a !important; }
    html:not(.dark) .text-gray-300 { color: #334155 !important; }
    html:not(.dark) .text-gray-400 { color: #64748b !important; }
    html:not(.dark) .text-gray-500 { color: #94a3b8 !important; }
    html:not(.dark) .text-gray-600 { color: #64748b !important; }
    html:not(.dark) .border-white\/10,
    html:not(.dark) .border-white\/15,
    html:not(.dark) .border-white\/\[0\.08\],
    html:not(.dark) .border-white\/\[0\.06\],
    html:not(.dark) .border-white\/\[0\.04\] { border-color: #e2e8f0 !important; }
    html:not(.dark) .border-white\/5 { border-color: #f1f5f9 !important; }
    html:not(.dark) select option { background-color: #fff !important; color: #0f172a !important; }
    /* Theme/Profile dropdowns in light mode */
    html:not(.dark) #themeMenu,
    html:not(.dark) #profileDropdown {
      background-color: rgba(255,255,255,0.98) !important;
      border-color: #e2e8f0 !important;
    }
    html:not(.dark) #themeMenu button,
    html:not(.dark) #profileDropdown a { color: #1e293b !important; }
    html:not(.dark) #themeMenu button:hover { background-color: rgba(6,182,212,0.08) !important; }

    /* Popover High-Contrast Hub */
    #geminiPopover {
      min-width: 330px;
      background-color: rgba(11, 15, 23, 0.98);
      border: 1px solid rgba(168, 85, 247, 0.45);
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7);
    }
    html:not(.dark) #geminiPopover {
      background-color: #ffffff !important;
      border: 1px solid #cbd5e1 !important;
      box-shadow: 0 20px 45px -10px rgba(0, 0, 0, 0.15), 0 0 0 1px rgba(168, 85, 247, 0.25) !important;
    }
    html:not(.dark) #geminiPopover .popover-title { color: #0f172a !important; font-weight: 800 !important; }
    html:not(.dark) #geminiPopover .popover-sub { color: #475569 !important; font-weight: 500 !important; }
    html:not(.dark) #geminiPopover .popover-item { color: #1e293b !important; font-weight: 600 !important; }
    html:not(.dark) #geminiPopover .popover-item span { color: #1e293b !important; }
    html:not(.dark) #geminiEngineBadge {
      background-color: rgba(168, 85, 247, 0.12) !important;
      border-color: rgba(168, 85, 247, 0.45) !important;
      color: #6b21a8 !important;
    }

    /* Preserve Bright White Text on Action Gradient Buttons */
    html:not(.dark) button.text-white,
    html:not(.dark) a.text-white,
    html:not(.dark) [class*="bg-purple-600"] *,
    html:not(.dark) [class*="from-purple-600"],
    html:not(.dark) [class*="from-purple-600"] *,
    html:not(.dark) [class*="from-cyan-600"] *,
    html:not(.dark) [class*="bg-cyan-600"] *,
    html:not(.dark) .btn-solid-white {
      color: #ffffff !important;
    }

    /* High-Contrast AI Review Cards - Dark Mode */
    .ai-assessment-card {
      background: rgba(88, 28, 135, 0.22);
      border: 1px solid rgba(168, 85, 247, 0.35);
      color: #f1f5f9;
    }
    .ai-assessment-title { color: #d8b4fe; }
    .ai-section-title { color: #cbd5e1; }
    .ai-card-opt {
      background: rgba(26, 32, 44, 0.85);
      border: 1px solid rgba(245, 158, 11, 0.35);
    }
    .ai-card-opt .ai-title { color: #fbbf24; }
    .ai-card-bug {
      background: rgba(26, 32, 44, 0.85);
      border: 1px solid rgba(239, 68, 68, 0.35);
    }
    .ai-card-bug .ai-title { color: #f87171; }
    .ai-card-tips {
      background: rgba(15, 23, 42, 0.75);
      border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .ai-desc { color: #e2e8f0; }

    /* High-Contrast AI Review Cards - Light Mode */
    html:not(.dark) .ai-assessment-card {
      background: #f5f3ff !important;
      border: 1px solid #ddd6fe !important;
      color: #1e293b !important;
    }
    html:not(.dark) .ai-assessment-title { color: #6b21a8 !important; }
    html:not(.dark) .ai-section-title { color: #334155 !important; font-weight: 700 !important; }
    html:not(.dark) .ai-card-opt {
      background: #fffbeb !important;
      border: 1px solid #fde68a !important;
    }
    html:not(.dark) .ai-card-opt .ai-title { color: #92400e !important; }
    html:not(.dark) .ai-card-bug {
      background: #fef2f2 !important;
      border: 1px solid #fecaca !important;
    }
    html:not(.dark) .ai-card-bug .ai-title { color: #991b1b !important; }
    html:not(.dark) .ai-card-tips {
      background: #f8fafc !important;
      border: 1px solid #e2e8f0 !important;
    }
    html:not(.dark) .ai-desc { color: #1e293b !important; font-weight: 500 !important; }
    html:not(.dark) .ai-loading-title { color: #6b21a8 !important; }
    html:not(.dark) .ai-loading-sub { color: #64748b !important; }

    /* Issue cards */
    html:not(.dark) .issue-card { background: rgba(248,250,252,0.9) !important; border-color: #e2e8f0 !important; }
    html:not(.dark) .issue-card:hover { border-color: #cbd5e1 !important; }
    /* Toast */
    html:not(.dark) .toast-box {
      background: rgba(255,255,255,0.95) !important;
      border-color: #e2e8f0 !important;
      color: #0f172a !important;
    }
    /* Complexity & Style new cards */
    html:not(.dark) .metric-card { background: rgba(248,250,252,0.95) !important; border-color: #e2e8f0 !important; }
    html:not(.dark) .fn-row { background: rgba(241,245,249,0.9) !important; border-color: #e2e8f0 !important; }
    html:not(.dark) .diff-panel { background: rgba(248,250,252,0.98) !important; }
  
    /* Tab Navigation Styles */
    .tab-btn-active {
      background: rgba(6, 182, 212, 0.15) !important;
      color: #22d3ee !important;
      border: 1px solid rgba(6, 182, 212, 0.45) !important;
      box-shadow: 0 2px 10px rgba(6, 182, 212, 0.15);
    }
    .tab-btn-inactive {
      background: transparent !important;
      color: #94a3b8 !important;
      border: 1px solid transparent !important;
    }
    .tab-btn-inactive:hover {
      color: #f1f5f9 !important;
      background: rgba(255, 255, 255, 0.05) !important;
    }

    html:not(.dark) .tab-btn-active {
      background: rgba(6, 182, 212, 0.12) !important;
      color: #0891b2 !important;
      border-color: rgba(6, 182, 212, 0.5) !important;
      box-shadow: 0 2px 8px rgba(6, 182, 212, 0.1) !important;
    }
    html:not(.dark) .tab-btn-inactive {
      color: #64748b !important;
    }
    html:not(.dark) .tab-btn-inactive:hover {
      color: #0f172a !important;
      background: rgba(0, 0, 0, 0.04) !important;
    }

    /* ═══════════════════════════════════════════════════════
       CINEMATIC WELCOME INTRO ANIMATIONS
    ═══════════════════════════════════════════════════════ */
    .welcome-card {
      background: rgba(11, 15, 23, 0.92);
      backdrop-filter: blur(28px);
      -webkit-backdrop-filter: blur(28px);
      box-shadow: 0 30px 80px -15px rgba(0, 0, 0, 0.95), 0 0 0 1px rgba(255, 255, 255, 0.1), 0 0 60px -10px rgba(168, 85, 247, 0.3);
      animation: welcomeCardIn 0.85s cubic-bezier(0.16, 1, 0.3, 1) both;
    }

    @keyframes welcomeCardIn {
      0% {
        opacity: 0;
        transform: scale(0.9) translateY(28px);
        filter: blur(12px);
      }
      100% {
        opacity: 1;
        transform: scale(1) translateY(0);
        filter: blur(0);
      }
    }

    .welcome-shimmer-title {
      background: linear-gradient(135deg, #ffffff 0%, #22d3ee 30%, #c084fc 65%, #67e8f9 85%, #ffffff 100%);
      background-size: 250% auto;
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      animation: welcomeShimmer 4s ease infinite;
    }

    @keyframes welcomeShimmer {
      0% { background-position: 0% 50%; }
      50% { background-position: 100% 50%; }
      100% { background-position: 0% 50%; }
    }

    .welcome-icon-float {
      animation: welcomeFloat 3s ease-in-out infinite;
    }

    @keyframes welcomeFloat {
      0%, 100% { transform: translateY(0); }
      50% { transform: translateY(-7px); }
    }

    /* Futuristic Reticle & HUD Animations */
    @keyframes spinClockwise {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }
    @keyframes spinCounter {
      from { transform: rotate(360deg); }
      to { transform: rotate(0deg); }
    }

    .hud-reticle-ring-1 {
      position: absolute;
      width: 116px;
      height: 116px;
      border-radius: 9999px;
      border: 1.5px dashed rgba(34, 211, 238, 0.5);
      animation: spinClockwise 12s linear infinite;
      pointer-events: none;
    }

    .hud-reticle-ring-2 {
      position: absolute;
      width: 140px;
      height: 140px;
      border-radius: 9999px;
      border: 1.5px solid rgba(168, 85, 247, 0.4);
      border-top-color: transparent;
      border-bottom-color: transparent;
      animation: spinCounter 8s linear infinite;
      pointer-events: none;
    }

    .hud-radar-sweep {
      position: absolute;
      width: 124px;
      height: 124px;
      border-radius: 9999px;
      background: conic-gradient(from 0deg, transparent 75%, rgba(34, 211, 238, 0.22) 100%);
      animation: spinClockwise 2.4s linear infinite;
      pointer-events: none;
    }

    .hud-terminal-box {
      background: rgba(6, 10, 18, 0.9);
      border: 1px solid rgba(34, 211, 238, 0.25);
      box-shadow: inset 0 0 20px rgba(6, 182, 212, 0.08), 0 10px 30px -5px rgba(0, 0, 0, 0.8);
    }

    .welcome-badge-pulse {
      animation: welcomeBadgePop 2s ease-in-out infinite;
    }

    @keyframes welcomeBadgePop {
      0%, 100% { transform: scale(1); }
      50% { transform: scale(1.12); }
    }

    .welcome-nebula {
      position: absolute;
      border-radius: 9999px;
      filter: blur(100px);
      opacity: 0.35;
      pointer-events: none;
      animation: welcomeNebulaBreath 6s ease-in-out infinite alternate;
    }

    .welcome-nebula-cyan {
      width: 480px;
      height: 480px;
      top: 15%;
      left: 15%;
      background: radial-gradient(circle, rgba(6, 182, 212, 0.45) 0%, transparent 70%);
    }

    .welcome-nebula-purple {
      width: 520px;
      height: 520px;
      bottom: 15%;
      right: 15%;
      background: radial-gradient(circle, rgba(168, 85, 247, 0.4) 0%, transparent 70%);
      animation-delay: -3s;
    }

    @keyframes welcomeNebulaBreath {
      0% { transform: scale(0.9) translate(0, 0); opacity: 0.25; }
      100% { transform: scale(1.15) translate(20px, -20px); opacity: 0.45; }
    }

    .welcome-grid-pattern {
      position: absolute;
      inset: 0;
      background-image: linear-gradient(rgba(255, 255, 255, 0.035) 1px, transparent 1px),
                        linear-gradient(90deg, rgba(255, 255, 255, 0.035) 1px, transparent 1px);
      background-size: 36px 36px;
      mask-image: radial-gradient(ellipse 60% 60% at 50% 50%, black, transparent);
    }

    /* Main Workspace Reveal & Kinetic Studio Move */
    #mainWorkspaceApp {
      opacity: 0;
      transform: scale(0.96) translateY(22px);
      filter: blur(10px);
      transition: opacity 0.7s cubic-bezier(0.16, 1, 0.3, 1),
                  transform 0.7s cubic-bezier(0.16, 1, 0.3, 1),
                  filter 0.7s cubic-bezier(0.16, 1, 0.3, 1);
      will-change: opacity, transform, filter;
    }

    #mainWorkspaceApp.studio-revealed {
      opacity: 1;
      transform: scale(1) translateY(0);
      filter: blur(0);
    }

    .welcome-exit-warp {
      animation: welcomeWarpExit 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards !important;
    }

    @keyframes welcomeWarpExit {
      0% {
        opacity: 1;
        transform: scale(1);
        filter: blur(0);
      }
      100% {
        opacity: 0;
        transform: scale(1.1);
        filter: blur(16px);
        pointer-events: none;
      }
    }

    /* Laser scanline sweep on code editor */
    .editor-scanline-active::after {
      content: '';
      position: absolute;
      left: 0;
      right: 0;
      height: 3px;
      background: linear-gradient(90deg, transparent, rgba(34, 211, 238, 0.9), rgba(168, 85, 247, 0.9), transparent);
      box-shadow: 0 0 16px rgba(34, 211, 238, 0.8), 0 0 30px rgba(168, 85, 247, 0.6);
      animation: scanlineSweep 1.1s cubic-bezier(0.4, 0, 0.2, 1) forwards;
      pointer-events: none;
      z-index: 30;
    }

    @keyframes scanlineSweep {
      0% { top: 0%; opacity: 0; }
      15% { opacity: 1; }
      85% { opacity: 1; }
      100% { top: 100%; opacity: 0; }
    }
</style>
</head>
<body class="min-h-screen flex flex-col antialiased selection:bg-cyan-500/25 selection:text-cyan-200">

  <!-- ════════════════════════ WELCOME CINEMATIC INTRO ════════════════════════ -->
  <div id="welcomeIntroOverlay" onclick="unlockAudioAndStart()" class="fixed inset-0 z-[9999] flex items-center justify-center bg-dark-950/98 backdrop-blur-3xl select-none cursor-pointer">
    <!-- Ambient glowing nebulas -->
    <div class="absolute inset-0 overflow-hidden pointer-events-none">
      <div class="welcome-nebula welcome-nebula-cyan"></div>
      <div class="welcome-nebula welcome-nebula-purple"></div>
      <div class="welcome-grid-pattern"></div>
    </div>

    <!-- Centered Cyber HUD Portal Card -->
    <div class="relative z-10 max-w-lg w-full mx-4 p-8 md:p-10 rounded-3xl welcome-card border border-white/10 text-center flex flex-col items-center space-y-6 shadow-2xl">
      <!-- Floating Holographic Logo & Cyber Reticle Rings -->
      <div class="relative flex items-center justify-center py-2">
        <div class="hud-radar-sweep"></div>
        <div class="hud-reticle-ring-1"></div>
        <div class="hud-reticle-ring-2"></div>
        <div class="w-20 h-20 md:w-24 md:h-24 rounded-3xl bg-gradient-to-tr from-cyan-500/20 via-purple-500/30 to-indigo-500/20 border border-purple-400/50 flex items-center justify-center text-4xl md:text-5xl shadow-2xl backdrop-blur-xl welcome-icon-float">
          <span>🩺</span>
        </div>
        <div class="absolute -bottom-1 -right-1 w-9 h-9 rounded-2xl bg-purple-600 border border-white/20 flex items-center justify-center text-lg shadow-lg welcome-badge-pulse">
          🧠
        </div>
      </div>

      <!-- Kinetic Text Block -->
      <div class="space-y-2">
        <div class="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-cyan-950/60 border border-cyan-500/30 text-cyan-300 text-[11px] font-bold tracking-widest uppercase">
          <span class="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping"></span>
          <span>Next-Gen Code Intelligence</span>
        </div>

        <h1 class="text-3xl md:text-4xl font-extrabold tracking-tight welcome-shimmer-title">
          Welcome to DocuDoctor
        </h1>

        <p class="text-xs md:text-sm text-gray-300 max-w-sm mx-auto leading-relaxed">
          Autonomous AST Engine, Complexity Profiling &amp; Multi-Language Docstring Intelligence.
        </p>
      </div>

      <!-- Futuristic Cyber HUD Loading Module -->
      <div class="w-full space-y-2.5 pt-1">
        <!-- Terminal telemetry box -->
        <div class="hud-terminal-box p-3.5 rounded-2xl space-y-2 text-left font-mono">
          <div class="flex items-center justify-between text-[10px] pb-1.5 border-b border-white/[0.08]">
            <div class="flex items-center space-x-1.5 text-cyan-400">
              <span class="w-2 h-2 rounded-full bg-cyan-400 animate-ping"></span>
              <span class="font-bold tracking-wider">NEURAL_TELEMETRY_BUS</span>
            </div>
            <div class="flex items-center space-x-2 text-gray-400">
              <span id="welcomeProgressHex" class="text-purple-300 font-bold">0x7F4A</span>
              <span class="text-gray-600">|</span>
              <span id="welcomeProgressPct" class="font-bold text-cyan-300">0%</span>
            </div>
          </div>

          <!-- Dynamic Telemetry Ticker -->
          <div class="flex items-center space-x-2 text-[11px] text-gray-200 h-5 overflow-hidden">
            <span class="text-cyan-400 font-bold">&gt;_</span>
            <span id="welcomeProgressText" class="truncate text-slate-200">Initializing AST compiler...</span>
          </div>

          <!-- High-Tech Neon Segmented Meter (12 segments) -->
          <div class="grid grid-cols-12 gap-1.5 pt-1">
            <div class="hud-seg h-1.5 rounded-sm bg-slate-800 transition-all duration-150"></div>
            <div class="hud-seg h-1.5 rounded-sm bg-slate-800 transition-all duration-150"></div>
            <div class="hud-seg h-1.5 rounded-sm bg-slate-800 transition-all duration-150"></div>
            <div class="hud-seg h-1.5 rounded-sm bg-slate-800 transition-all duration-150"></div>
            <div class="hud-seg h-1.5 rounded-sm bg-slate-800 transition-all duration-150"></div>
            <div class="hud-seg h-1.5 rounded-sm bg-slate-800 transition-all duration-150"></div>
            <div class="hud-seg h-1.5 rounded-sm bg-slate-800 transition-all duration-150"></div>
            <div class="hud-seg h-1.5 rounded-sm bg-slate-800 transition-all duration-150"></div>
            <div class="hud-seg h-1.5 rounded-sm bg-slate-800 transition-all duration-150"></div>
            <div class="hud-seg h-1.5 rounded-sm bg-slate-800 transition-all duration-150"></div>
            <div class="hud-seg h-1.5 rounded-sm bg-slate-800 transition-all duration-150"></div>
            <div class="hud-seg h-1.5 rounded-sm bg-slate-800 transition-all duration-150"></div>
          </div>

          <!-- Standby prompt for browsers where autoplay requires user activation -->
          <div id="standbyLaunchWrapper" class="pt-2 hidden">
            <button type="button" id="standbyLaunchBtn" onclick="userInitiatedBoot(event)" class="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-cyan-600 via-cyan-500 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-mono font-bold text-xs tracking-wider flex items-center justify-center space-x-2 shadow-lg shadow-cyan-950/80 hover:shadow-cyan-500/40 transition-all cursor-pointer active:scale-95 animate-pulse">
              <span>🔊</span>
              <span>INITIALIZE DOCUDOCTOR // AUDIO ON</span>
            </button>
          </div>
        </div>

        <!-- Micro telemetry footer without buttons -->
        <div class="flex items-center justify-between text-[10px] font-mono text-gray-500 px-1 pt-1">
          <span class="flex items-center space-x-1.5">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            <span class="text-emerald-400/90 font-bold tracking-wide">QUANTUM CORE ACTIVE</span>
          </span>
          <span id="welcomeAudioHint" class="text-cyan-400 font-mono text-[9px] tracking-wider animate-pulse hidden">🔊 TAP TO UNMUTE</span>
          <span id="welcomeOsLabel" class="text-gray-400/80 font-mono text-[9px] tracking-wider">DOCUDOCTOR OS</span>
        </div>
      </div>
    </div>
  </div>

  <!-- ════════════════════════ MAIN WORKSPACE WRAPPER ════════════════════════ -->
  <div id="mainWorkspaceApp" class="flex-1 flex flex-col">

  <!-- ════════════════════════ HEADER ════════════════════════ -->
  <header class="border-b border-white/[0.08] bg-dark-950/80 sticky top-0 z-50 backdrop-blur-2xl transition-colors duration-200">
    <div class="max-w-screen-xl mx-auto px-5 h-16 flex items-center justify-between">

      <!-- Brand -->
      <div class="flex items-center space-x-3">
        <div class="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-500/20 via-blue-500/20 to-fuchsia-500/20 border border-cyan-500/40 flex items-center justify-center p-1.5 shadow-lg shadow-cyan-500/20">
          <svg class="w-full h-full" viewBox="0 0 64 64" fill="none">
            <path d="M20 22L12 32l8 10" stroke="#22d3ee" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M44 22l8 10-8 10" stroke="#c084fc" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M22 32h5l3-9 4 18 3-9h5" stroke="#22d3ee" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>
            <circle cx="32" cy="13" r="3.5" fill="#c084fc"/>
          </svg>
        </div>
        <div>
          <div class="flex items-center space-x-2">
            <span class="font-extrabold text-xl tracking-tight text-cyan-400">DOCU</span>
            <span class="font-extrabold text-xl tracking-tight bg-gradient-to-r from-fuchsia-400 via-indigo-300 to-cyan-300 bg-clip-text text-transparent">DOCTOR</span>
          </div>
          <p class="text-[11px] text-gray-400 hidden sm:block">Code Health, Complexity Estimation &amp; Style Analysis</p>
        </div>
      </div>

      <!-- Right header controls -->
      <div class="flex items-center space-x-2.5">
        <!-- Built-in Gemini AI Interactive Hub -->
        <div class="relative">
          <button id="geminiEngineBadge" type="button" onclick="toggleGeminiPopover(event)" title="Click to open Gemini AI Engine Hub" class="flex items-center space-x-1.5 px-3 py-1.5 rounded-full bg-purple-950/60 hover:bg-purple-900/80 border border-purple-500/40 hover:border-purple-400 text-purple-200 text-xs font-semibold shadow-sm cursor-pointer transition-all active:scale-95 group">
            <span class="w-2 h-2 rounded-full bg-purple-400 animate-pulse"></span>
            <span>Gemini AI Built-in</span>
            <svg class="w-3 h-3 text-purple-400 group-hover:text-purple-200 transition" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
          </button>

          <!-- Gemini AI Popover Dropdown -->
          <div id="geminiPopover" style="display: none;" class="absolute right-0 top-full mt-2 w-80 rounded-2xl p-4 z-50 animate-toast space-y-3">
            <div class="flex items-center space-x-3 pb-2.5 border-b border-purple-500/20">
              <div class="w-10 h-10 rounded-2xl bg-purple-500/20 border border-purple-500/40 flex items-center justify-center text-xl shadow-inner">🧠</div>
              <div class="flex-1 min-w-0">
                <div class="flex items-center justify-between">
                  <h4 class="font-extrabold text-sm popover-title text-white">Gemini AI Engine</h4>
                  <span class="px-2 py-0.5 rounded-full text-[9px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">ONLINE • FLASH</span>
                </div>
                <p class="text-[11px] popover-sub text-gray-400">Google Gemini Code Intelligence</p>
              </div>
            </div>

            <div class="space-y-2 text-xs popover-item text-gray-200">
              <div class="flex items-center space-x-2">
                <span class="text-purple-400 font-bold">⚡</span>
                <span>Semantic Architecture &amp; Deep Code Review</span>
              </div>
              <div class="flex items-center space-x-2">
                <span class="text-purple-400 font-bold">🛡️</span>
                <span>AST Guardrails (0% Hallucinations)</span>
              </div>
              <div class="flex items-center space-x-2">
                <span class="text-purple-400 font-bold">🌐</span>
                <span>Multi-Language: Python, C, C++, Java</span>
              </div>
            </div>

            <div class="pt-1 flex flex-col space-y-2">
              <button type="button" onclick="openAiReviewFromPopover()" class="w-full text-center text-xs font-bold text-white bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 py-2.5 px-4 rounded-xl transition shadow-lg shadow-purple-950/50 flex items-center justify-center space-x-2 cursor-pointer active:scale-95 btn-solid-white">
                <span>🚀</span><span>Launch AI Deep Code Review</span>
              </button>
            </div>
          </div>
        </div>

        <!-- Theme selector -->
        <div class="relative">
          <button id="themeBtn" type="button" onclick="toggleThemeMenu(event)" class="flex items-center space-x-1.5 px-3 py-2 rounded-xl border border-white/10 hover:border-cyan-500/40 bg-dark-850 hover:bg-dark-800 text-xs font-semibold text-gray-200 transition-all shadow-sm cursor-pointer group">
            <span id="themeActiveIcon" class="text-sm">💻</span>
            <span id="themeActiveText" class="hidden sm:inline text-xs font-semibold">System</span>
            <svg class="w-3 h-3 text-gray-400 group-hover:text-cyan-400 transition" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
          </button>
          <div id="themeMenu" style="display:none;" class="absolute right-0 top-full mt-2 w-44 bg-dark-900/98 border border-white/15 rounded-2xl shadow-2xl backdrop-blur-2xl p-1.5 z-50 flex flex-col space-y-1 animate-toast">
            <button type="button" onclick="setTheme('system')" id="themeOptSystem" class="w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-semibold hover:bg-cyan-500/15 transition cursor-pointer text-left text-gray-200">
              <div class="flex items-center space-x-2.5"><span>💻</span><span>System</span></div>
              <span id="checkSystem" class="text-cyan-400 font-bold">✓</span>
            </button>
            <button type="button" onclick="setTheme('dark')" id="themeOptDark" class="w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-semibold hover:bg-cyan-500/15 transition cursor-pointer text-left text-gray-200">
              <div class="flex items-center space-x-2.5"><span>🌙</span><span>Dark Mode</span></div>
              <span id="checkDark" class="hidden text-cyan-400 font-bold">✓</span>
            </button>
            <button type="button" onclick="setTheme('light')" id="themeOptLight" class="w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-semibold hover:bg-cyan-500/15 transition cursor-pointer text-left text-gray-200">
              <div class="flex items-center space-x-2.5"><span>☀️</span><span>Light Mode</span></div>
              <span id="checkLight" class="hidden text-cyan-400 font-bold">✓</span>
            </button>
          </div>
        </div>

        <!-- Profile avatar -->
        <div class="relative">
          <button id="profileDropdownBtn" onclick="toggleProfileDropdown(event)" title="Developer Profile" class="flex items-center focus:outline-none ring-2 ring-white/10 hover:ring-cyan-400 p-0.5 rounded-full transition-all shadow-sm bg-dark-850">
            <img src="https://github.com/prasunkrghosh-18.png" alt="Prasun Kumar Ghosh" class="w-8 h-8 rounded-full object-cover" onerror="this.onerror=null;this.src='https://ui-avatars.com/api/?name=Prasun+Kumar+Ghosh&background=06b6d4&color=fff'">
          </button>
          <!-- Profile dropdown -->
          <div id="profileDropdown" style="display:none;" class="absolute right-0 top-full mt-2.5 w-72 bg-dark-900/98 border border-white/15 rounded-2xl shadow-2xl backdrop-blur-2xl p-4 z-50 animate-toast">
            <div class="flex items-center space-x-3 pb-3 border-b border-white/[0.08]">
              <div class="relative">
                <img src="https://github.com/prasunkrghosh-18.png" alt="Prasun" class="w-11 h-11 rounded-full border-2 border-cyan-400/70 shadow-md object-cover bg-dark-850" onerror="this.onerror=null;this.src='https://ui-avatars.com/api/?name=Prasun+Kumar+Ghosh&background=06b6d4&color=fff'">
                <span class="absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full bg-emerald-400 border-2 border-dark-900"></span>
              </div>
              <div class="flex-1 min-w-0">
                <div class="flex items-center justify-between">
                  <h4 class="font-extrabold text-sm text-white truncate">Prasun Kumar Ghosh</h4>
                  <span class="px-1.5 py-0.5 rounded text-[9px] font-bold bg-cyan-950 text-cyan-300 border border-cyan-700/60">AUTHOR</span>
                </div>
                <p class="text-xs text-gray-400 font-mono">@prasunkrghosh-18</p>
                <p class="text-[11px] text-gray-500 mt-0.5">Creator of DocuDoctor • Lead Developer</p>
              </div>
            </div>
            <div class="py-2.5 text-xs text-gray-300 leading-relaxed border-b border-white/[0.08]">
              <p>Building intelligent multi-language docstring synthesis and automated code health tools.</p>
              <div class="mt-2 flex flex-wrap gap-1.5">
                <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-dark-800 text-cyan-300 border border-cyan-800/30">Python</span>
                <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-dark-800 text-blue-300 border border-blue-800/30">C</span>
                <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-dark-800 text-indigo-300 border border-indigo-800/30">C++</span>
                <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-dark-800 text-amber-300 border border-amber-800/30">Java</span>
              </div>
            </div>
            <div class="pt-3 flex flex-col space-y-2">
              <a href="https://github.com/prasunkrghosh-18" target="_blank" class="w-full text-center text-xs font-semibold text-white bg-cyan-600 hover:bg-cyan-500 py-2 rounded-xl transition shadow-md flex items-center justify-center space-x-1.5">
                <span>View GitHub Profile ↗</span>
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

  <!-- ════════════════════════ MAIN ════════════════════════ -->
  <main class="max-w-screen-xl mx-auto px-5 py-5 flex-1 w-full flex flex-col gap-5">

    <!-- ── Control Bar ── -->
    <div class="glass-panel p-3 rounded-2xl flex flex-wrap items-center justify-between gap-3 relative z-40">
      <div class="flex flex-wrap items-center gap-2.5">
        <!-- Language picker -->
        <div class="flex items-center space-x-2 bg-dark-900/95 hover:bg-dark-850 border border-white/10 hover:border-cyan-500/50 rounded-xl px-3 py-2 transition-all shadow-inner group cursor-pointer">
          <span class="text-lg select-none" id="langEmojiIcon">🐍</span>
          <div class="flex flex-col">
            <span class="text-[9px] text-gray-400 uppercase tracking-wider font-extrabold leading-none">Language</span>
            <select id="languageSelect" onchange="onLanguageChange(this.value,false)" class="bg-transparent text-xs font-bold text-white hover:text-cyan-300 focus:outline-none cursor-pointer mt-0.5 pr-1">
              <option value="python" class="bg-dark-900 text-white">🐍 Python (.py)</option>
              <option value="c" class="bg-dark-900 text-white">⚡ C (.c / .h)</option>
              <option value="cpp" class="bg-dark-900 text-white">🚀 C++ (.cpp)</option>
              <option value="java" class="bg-dark-900 text-white">☕ Java (.java)</option>
            </select>
          </div>
        </div>



        <input type="file" id="fileInput" accept=".py,.c,.h,.cpp,.hpp,.cc,.java" class="hidden" onchange="handleFileUpload(event)">
        <button onclick="document.getElementById('fileInput').click()" class="bg-dark-850 hover:bg-dark-800 text-gray-300 hover:text-white text-xs font-semibold px-3 py-2.5 rounded-xl border border-white/10 hover:border-white/20 transition flex items-center space-x-1.5 shadow-sm cursor-pointer">
          <span>📁</span><span>Upload</span>
        </button>
        <button onclick="loadSampleForLanguage()" class="bg-dark-850 hover:bg-dark-800 text-cyan-400 hover:text-cyan-300 text-xs font-semibold px-3 py-2.5 rounded-xl border border-white/10 hover:border-cyan-500/30 transition flex items-center space-x-1.5 shadow-sm cursor-pointer">
          <span>📂</span><span>Sample</span>
        </button>
        <button onclick="clearEditor()" class="text-xs text-gray-400 hover:text-white px-2.5 py-2 transition font-medium cursor-pointer">Clear</button>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <!-- Doc style -->
        <div class="flex items-center space-x-2 bg-dark-900 border border-white/10 rounded-xl px-3 py-2 shadow-inner">
          <label class="text-[11px] text-gray-400 font-medium">Style:</label>
          <select id="docStyle" class="bg-transparent text-xs text-cyan-400 font-semibold focus:outline-none cursor-pointer">
            <option value="google" class="bg-dark-900 text-gray-200">Google Style</option>
            <option value="numpy" class="bg-dark-900 text-gray-200">NumPy Style</option>
            <option value="sphinx" class="bg-dark-900 text-gray-200">Sphinx Style</option>
          </select>
        </div>
        <!-- Audit -->
        <button onclick="auditCode()" class="bg-gradient-to-r from-cyan-600 via-cyan-500 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-bold text-xs px-4 py-2.5 rounded-xl transition-all flex items-center space-x-2 shadow-lg shadow-cyan-950/80 hover:shadow-cyan-500/30 active:scale-95 cursor-pointer">
          <span>🔍</span><span>Audit Code</span>
        </button>
        <!-- Total Healer -->
        <button onclick="fixCode()" class="bg-gradient-to-r from-fuchsia-600 via-purple-600 to-indigo-600 hover:from-fuchsia-500 hover:to-indigo-500 text-white font-bold text-xs px-4 py-2.5 rounded-xl transition-all flex items-center space-x-2 shadow-lg shadow-fuchsia-950/80 hover:shadow-fuchsia-500/30 active:scale-95 cursor-pointer">
          <span>⚡</span><span>Total Healer</span>
        </button>
        <!-- Export -->
        <button onclick="exportMarkdownReport()" class="bg-dark-850 hover:bg-dark-800 text-gray-200 hover:text-white font-semibold text-xs px-3 py-2.5 rounded-xl border border-white/10 hover:border-cyan-500/40 transition-all flex items-center space-x-1.5 shadow-sm cursor-pointer">
          <span>📄</span><span>Export Report</span>
        </button>
      </div>
    </div>

    <!-- ── Main Workspace Grid ── -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-5 flex-1">

      <!-- Left: Code Editor (7 cols) -->
      <div id="codeEditorPanel" class="lg:col-span-7 flex flex-col glass-panel rounded-2xl overflow-hidden min-h-[520px] relative">
        <!-- Editor header -->
        <div class="bg-dark-950/90 border-b border-white/[0.08] px-4 py-2.5 flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <div class="flex items-center space-x-1.5">
              <div class="w-3 h-3 rounded-full bg-[#ff5f56] border border-red-400/30"></div>
              <div class="w-3 h-3 rounded-full bg-[#ffbd2e] border border-yellow-400/30"></div>
              <div class="w-3 h-3 rounded-full bg-[#27c93f] border border-green-400/30"></div>
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
            <button onclick="downloadCode()" title="Download" class="text-gray-400 hover:text-cyan-400 transition ml-1">📥</button>
          </div>
        </div>
        <!-- Editor body -->
        <div class="flex-1 flex bg-dark-950/60 relative overflow-hidden">
          <div id="gutter" class="py-4 px-2 select-none font-mono text-xs text-gray-600 bg-dark-950/90 border-r border-white/[0.06] text-right min-w-[2.75rem] overflow-hidden">1</div>
          <textarea id="codeEditor" oninput="updateGutter()" onscroll="syncGutterScroll()"
            class="w-full flex-1 bg-transparent text-gray-100 p-4 text-xs md:text-sm leading-relaxed focus:outline-none resize-none font-mono selection:bg-cyan-900/60"
            spellcheck="false" placeholder="# Paste code here, load a sample, or upload a file..."></textarea>
        </div>
      </div>

      <!-- Right: Executive Vitals + Spacious Tabbed Studio (5 cols) -->
      <div class="lg:col-span-5 flex flex-col gap-4">

        <!-- 1. Executive Vitals Card (Top) -->
        <div class="glass-panel p-4 rounded-2xl relative overflow-hidden flex flex-col gap-3">
          <div class="flex items-center justify-between">
            <div>
              <div class="flex items-center space-x-1.5">
                <span class="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span>
                <span class="text-[10px] uppercase tracking-wider text-gray-400 font-extrabold">Documentation Health</span>
              </div>
              <div class="flex items-baseline space-x-2 mt-1">
                <span id="scoreVal" class="text-3xl font-black tracking-tight text-cyan-400">--</span>
                <span class="text-xs font-semibold text-gray-400">/ 100</span>
                <div id="gradeBadge" class="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-dark-850 text-gray-400 border border-white/10">
                  Awaiting Audit
                </div>
              </div>
            </div>

            <!-- Circular progress -->
            <div class="relative w-16 h-16 flex items-center justify-center flex-shrink-0">
              <svg class="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                <path class="text-dark-850" stroke-width="3.2" stroke="currentColor" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"/>
                <path id="circleProgress" class="text-cyan-400 transition-all duration-700 ease-out" stroke-dasharray="0, 100" stroke-width="3.2" stroke-linecap="round" stroke="currentColor" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"/>
              </svg>
              <span id="gradeLetter" class="absolute text-lg font-black text-white">?</span>
            </div>
          </div>

          <!-- Quick Vitals Grid (4 chips giving the whole picture at a glance) -->
          <div class="grid grid-cols-4 gap-2 pt-2.5 border-t border-white/[0.08]">
            <div class="p-2 rounded-xl bg-dark-850/60 border border-white/[0.04] text-center">
              <span class="text-[9px] uppercase tracking-wider text-gray-400 font-bold block">Functions</span>
              <span id="statFuncsQuick" class="text-xs font-bold text-gray-200 mt-0.5 block">--</span>
            </div>
            <div class="p-2 rounded-xl bg-dark-850/60 border border-white/[0.04] text-center">
              <span class="text-[9px] uppercase tracking-wider text-gray-400 font-bold block">Maintainability</span>
              <span id="statMiQuick" class="text-xs font-bold text-cyan-300 mt-0.5 block">--</span>
            </div>
            <div class="p-2 rounded-xl bg-dark-850/60 border border-white/[0.04] text-center">
              <span class="text-[9px] uppercase tracking-wider text-gray-400 font-bold block">Complexity</span>
              <span id="statComplexityQuick" class="text-xs font-bold text-emerald-400 mt-0.5 block">--</span>
            </div>
            <div class="p-2 rounded-xl bg-dark-850/60 border border-white/[0.04] text-center">
              <span class="text-[9px] uppercase tracking-wider text-gray-400 font-bold block">Style</span>
              <span id="statStyleQuick" class="text-xs font-bold text-fuchsia-300 mt-0.5 block">--</span>
            </div>
          </div>
        </div>

        <!-- 2. Spacious Tabbed Studio Inspector (Fills the rest of the height) -->
        <div class="glass-panel rounded-2xl flex flex-col flex-1 overflow-hidden min-h-[500px]">
          
          <!-- Tabs Navigation Bar -->
          <div class="p-2 border-b border-white/[0.08] bg-dark-950/80 flex items-center space-x-1.5 overflow-x-auto select-none">
            <button id="tabBtnIssues" type="button" onclick="switchRightTab('issues')" class="tab-btn px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center space-x-1.5 cursor-pointer tab-btn-active">
              <span>🐛</span>
              <span>Issues</span>
              <span id="tabCountIssues" class="px-1.5 py-0.2 rounded-full text-[10px] font-mono font-bold bg-dark-800 text-gray-300">0</span>
            </button>
            <button id="tabBtnComplexity" type="button" onclick="switchRightTab('complexity')" class="tab-btn px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center space-x-1.5 cursor-pointer tab-btn-inactive">
              <span>⏱️</span>
              <span>Complexity</span>
              <span id="tabBadgeComplexity" class="px-1.5 py-0.2 rounded-full text-[10px] font-mono font-bold bg-dark-800 text-gray-300">--</span>
            </button>
            <button id="tabBtnStyle" type="button" onclick="switchRightTab('style')" class="tab-btn px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center space-x-1.5 cursor-pointer tab-btn-inactive">
              <span>🎨</span>
              <span>Style</span>
              <span id="tabBadgeStyle" class="px-1.5 py-0.2 rounded-full text-[10px] font-mono font-bold bg-dark-800 text-gray-300">--</span>
            </button>
            <button id="tabBtnAiReview" type="button" onclick="switchRightTab('aiReview')" class="tab-btn px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center space-x-1.5 cursor-pointer tab-btn-inactive">
              <span>🧠</span>
              <span>AI Review</span>
            </button>
            <button id="tabBtnMetrics" type="button" onclick="switchRightTab('metrics')" class="tab-btn px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center space-x-1.5 cursor-pointer tab-btn-inactive">
              <span>📊</span>
              <span>Metrics</span>
            </button>
          </div>

          <!-- TAB PANE 1: Issues & Fixes -->
          <div id="tabPaneIssues" class="tab-pane flex flex-col flex-1 overflow-hidden">
            <!-- Filter Bar -->
            <div class="px-4 py-2.5 border-b border-white/[0.06] flex items-center justify-between bg-dark-950/60">
              <div class="flex items-center space-x-1.5">
                <button onclick="setFilter('all')" id="filterAll" class="text-[11px] font-semibold text-cyan-400 bg-cyan-950/80 px-2.5 py-1 rounded-lg border border-cyan-700/50">All (<span id="countAll">0</span>)</button>
                <button onclick="setFilter('error')" id="filterError" class="text-[11px] font-semibold text-gray-400 hover:text-red-400 px-2 py-1 rounded-lg">Errors (<span id="countError">0</span>)</button>
                <button onclick="setFilter('warning')" id="filterWarning" class="text-[11px] font-semibold text-gray-400 hover:text-amber-400 px-2 py-1 rounded-lg">Warnings (<span id="countWarning">0</span>)</button>
              </div>
              <span id="issueCountBadge" class="text-xs bg-dark-850 text-gray-400 px-2.5 py-0.5 rounded-full border border-white/10">0 issues</span>
            </div>

            <!-- Issue cards container with full spacious scrolling -->
            <div id="issuesContainer" class="p-4 overflow-y-auto space-y-3 flex-1 text-xs">
              <p class="text-gray-500 text-center py-14">No code analyzed yet.<br>Click <b>Load Sample</b> or paste code, then click <b>Audit Code</b>.</p>
            </div>
          </div>

          <!-- TAB PANE 2: Time & Space Complexity -->
          <div id="tabPaneComplexity" class="tab-pane hidden flex-col flex-1 overflow-hidden">
            <!-- Header banner with scale info -->
            <div class="p-4 border-b border-white/[0.06] bg-dark-950/40 space-y-3">
              <div class="flex items-center justify-between">
                <div class="flex items-center space-x-2">
                  <span class="text-base">⏱️</span>
                  <div>
                    <h4 class="text-xs font-bold text-gray-100 uppercase tracking-wide">Big-O Complexity Bounds</h4>
                    <p class="text-[10px] text-gray-400">Worst-case execution time and memory scaling</p>
                  </div>
                </div>
                <div class="flex items-center space-x-2">
                  <span id="overallTimeBig" class="text-xs font-mono font-bold px-2.5 py-1 rounded-lg bg-indigo-950/80 text-indigo-300 border border-indigo-700/40">Time: --</span>
                  <span id="overallSpaceBig" class="text-xs font-mono font-bold px-2.5 py-1 rounded-lg bg-violet-950/80 text-violet-300 border border-violet-700/40">Space: --</span>
                </div>
              </div>

              <!-- Practical Runtime Scale Guide (Answers user query about seconds) -->
              <div class="p-3 rounded-xl bg-dark-900/90 border border-white/[0.06] text-[11px] space-y-1.5">
                <div class="flex items-center justify-between text-gray-300 font-semibold">
                  <span class="flex items-center space-x-1.5">
                    <span class="text-cyan-400">⚡</span>
                    <span>Practical Execution Speed Scale</span>
                  </span>
                  <span class="text-[10px] text-gray-400 font-normal">Physical time vs Input Size (N)</span>
                </div>
                <p class="text-[10px] text-gray-400 leading-relaxed">
                  Exact execution seconds depend on hardware and dataset size <i>N</i>. Below is the reference transition:
                </p>
                <div class="grid grid-cols-3 gap-2 pt-1 text-center text-[10px] font-mono">
                  <div class="p-1.5 rounded-lg bg-dark-850/70 border border-white/[0.04]">
                    <span class="text-gray-400 block text-[9px] uppercase">N = 1,000</span>
                    <span class="text-emerald-400 font-bold block mt-0.5">&lt; 1 ms (Instant)</span>
                  </div>
                  <div class="p-1.5 rounded-lg bg-dark-850/70 border border-white/[0.04]">
                    <span class="text-gray-400 block text-[9px] uppercase">N = 10,000</span>
                    <span class="text-cyan-300 font-bold block mt-0.5">~15 ms (Fast)</span>
                  </div>
                  <div class="p-1.5 rounded-lg bg-dark-850/70 border border-white/[0.04]">
                    <span class="text-gray-400 block text-[9px] uppercase">N = 1,000,000</span>
                    <span class="text-amber-300 font-bold block mt-0.5">O(n²): ~16 min</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Function List with spacious padding -->
            <div id="complexityFnList" class="p-4 space-y-3 overflow-y-auto flex-1 text-xs">
              <p class="text-gray-500 text-center py-14">Run <b>Audit Code</b> to inspect function time and space bounds.</p>
            </div>
          </div>

          <!-- TAB PANE 3: Code Style & Linting -->
          <div id="tabPaneStyle" class="tab-pane hidden flex-col flex-1 overflow-hidden">
            <div class="p-4 border-b border-white/[0.06] bg-dark-950/40 space-y-3">
              <div class="flex items-center justify-between">
                <div>
                  <h4 class="text-xs font-bold text-gray-100 uppercase tracking-wide">Code Style &amp; Linting</h4>
                  <p class="text-[10px] text-gray-400">PEP 8 / naming conventions / structural hygiene</p>
                </div>
                <div class="flex items-center space-x-2">
                  <span id="styleScoreVal" class="text-sm font-black text-white">--</span>
                  <span id="styleGradeBadge" class="text-[10px] font-bold px-2 py-0.5 rounded-lg bg-dark-850 text-gray-400 border border-white/10">Grade -</span>
                </div>
              </div>

              <!-- Animated Gradient Bar -->
              <div>
                <div class="w-full bg-dark-850 rounded-full h-2 overflow-hidden border border-white/[0.06]">
                  <div id="styleScoreBar" class="h-2 rounded-full bg-gradient-to-r from-emerald-500 to-cyan-400 transition-all duration-700" style="width:0%"></div>
                </div>
                <div class="flex justify-between mt-1 text-[9px] text-gray-500 font-mono">
                  <span>0 (Defects)</span><span>50</span><span>100 (Clean)</span>
                </div>
              </div>

              <!-- 4 Category Breakdown Chips -->
              <div class="grid grid-cols-4 gap-2 text-center">
                <div class="bg-dark-850/60 rounded-xl p-2 border border-white/[0.05]">
                  <span class="text-[9px] text-gray-400 uppercase font-bold block">Naming</span>
                  <span id="styleNaming" class="text-xs font-bold text-white mt-0.5 block">--</span>
                </div>
                <div class="bg-dark-850/60 rounded-xl p-2 border border-white/[0.05]">
                  <span class="text-[9px] text-gray-400 uppercase font-bold block">Structure</span>
                  <span id="styleStructure" class="text-xs font-bold text-white mt-0.5 block">--</span>
                </div>
                <div class="bg-dark-850/60 rounded-xl p-2 border border-white/[0.05]">
                  <span class="text-[9px] text-gray-400 uppercase font-bold block">Formatting</span>
                  <span id="styleFormat" class="text-xs font-bold text-white mt-0.5 block">--</span>
                </div>
                <div class="bg-dark-850/60 rounded-xl p-2 border border-white/[0.05]">
                  <span class="text-[9px] text-gray-400 uppercase font-bold block">Total Items</span>
                  <span id="styleTotal" class="text-xs font-bold text-white mt-0.5 block">--</span>
                </div>
              </div>
            </div>

            <!-- Style issues list -->
            <div id="styleIssueList" class="p-4 space-y-2.5 overflow-y-auto flex-1 text-xs">
              <p class="text-gray-500 text-center py-14">Run <b>Audit Code</b> to review style and structural conventions.</p>
            </div>
          </div>

          <!-- TAB PANE: AI Review -->
          <div id="tabPaneAiReview" class="tab-pane hidden flex-col flex-1 overflow-hidden p-4 space-y-3.5 overflow-y-auto">
            <div class="glass-card p-4 rounded-xl border border-purple-500/25 bg-purple-950/20 flex items-center justify-between">
              <div class="flex items-center space-x-2.5">
                <span class="text-xl">🧠</span>
                <div>
                  <h4 class="text-xs font-bold text-white uppercase tracking-wide">Semantic AI Code Review</h4>
                  <p class="text-[10px] text-gray-400">Deep architecture, bug risk &amp; optimization audit</p>
                </div>
              </div>
              <button id="runAiReviewBtn" type="button" onclick="runAiDeepReview()" class="bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-bold text-xs px-3.5 py-2 rounded-xl transition shadow-md shadow-purple-950/60 flex items-center space-x-1.5 cursor-pointer active:scale-95">
                <span>🚀</span><span>Run Review</span>
              </button>
            </div>
            <div id="aiReviewOutput" class="space-y-3 text-xs">
              <div class="p-10 text-center text-gray-500">
                Click <b>Run Review</b> to trigger deep AI inspection for performance bottlenecks, edge-case bug risks, and best practices.
              </div>
            </div>
          </div>

          <!-- TAB PANE 4: Deep Metrics -->
          <div id="tabPaneMetrics" class="tab-pane hidden flex-col flex-1 overflow-hidden p-4 space-y-3.5 overflow-y-auto">
            <!-- 3 Stat cards -->
            <div class="grid grid-cols-3 gap-2.5">
              <div class="glass-card p-3 rounded-xl text-center metric-card">
                <span class="text-[10px] text-gray-400 font-medium">Total Functions</span>
                <p id="statFuncs" class="text-base font-bold text-gray-100 mt-0.5">--</p>
              </div>
              <div class="glass-card p-3 rounded-xl text-center metric-card">
                <span class="text-[10px] text-gray-400 font-medium">Documented</span>
                <p id="statDocs" class="text-base font-bold text-emerald-400 mt-0.5">--</p>
              </div>
              <div class="glass-card p-3 rounded-xl text-center metric-card">
                <span class="text-[10px] text-gray-400 font-medium">Typed Returns</span>
                <p id="statTyped" class="text-base font-bold text-fuchsia-400 mt-0.5">--</p>
              </div>
            </div>

            <!-- Maintainability Index Card -->
            <div class="glass-card p-4 rounded-xl space-y-2 border border-white/5 metric-card">
              <div class="flex items-center justify-between">
                <div class="flex items-center space-x-2.5">
                  <span class="text-lg">🧠</span>
                  <div>
                    <h5 class="text-xs font-bold text-gray-200">Maintainability Index (MI)</h5>
                    <p class="text-[10px] text-gray-400">Volume + Complexity + Defect Density</p>
                  </div>
                </div>
                <div class="flex items-center space-x-1.5">
                  <span id="statMaintainability" class="font-black text-white text-sm">-- / 100</span>
                  <span id="statMiGrade" class="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800/40">Grade -</span>
                </div>
              </div>
              <p class="text-[10px] text-gray-400 leading-relaxed pt-1.5 border-t border-white/[0.04]">
                Scores above 80 (Grade A) denote easy refactoring, high legibility, and minimal technical debt.
              </p>
            </div>

            <!-- Cyclomatic Complexity Card -->
            <div class="glass-card p-4 rounded-xl space-y-2 border border-white/5 metric-card">
              <div class="flex items-center justify-between">
                <div class="flex items-center space-x-2.5">
                  <span class="text-lg">⚡</span>
                  <div>
                    <h5 class="text-xs font-bold text-gray-200">Cyclomatic Decision Paths</h5>
                    <p class="text-[10px] text-gray-400">Independent branching paths per function</p>
                  </div>
                </div>
                <div class="flex items-center space-x-1.5">
                  <span id="statComplexity" class="font-black text-white text-sm">--</span>
                  <span id="complexityStatus" class="text-[10px] font-semibold text-emerald-400">Low Risk</span>
                </div>
              </div>
              <p class="text-[10px] text-gray-400 leading-relaxed pt-1.5 border-t border-white/[0.04]">
                Recommended threshold is &le; 5.0 branches per function. Code with higher branching should be split into smaller helpers.
              </p>
            </div>
          </div>

        </div>

      </div>
    </div>

    <!-- ── Diff Output ── -->
    <div id="diffSection" class="glass-panel rounded-2xl overflow-hidden hidden diff-panel">
      <div class="bg-dark-950/90 px-4 py-3 border-b border-white/[0.08] flex items-center justify-between">
        <div class="flex items-center space-x-2">
          <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
          <span class="text-xs font-bold text-cyan-400 tracking-wide uppercase">Proposed Patch &amp; Diff Preview</span>
        </div>
        <div class="flex items-center space-x-2">
          <button onclick="downloadCode()" class="text-xs bg-dark-850 hover:bg-dark-800 text-gray-200 px-3 py-1.5 rounded-lg border border-white/10 transition flex items-center space-x-1.5 cursor-pointer"><span>📥</span><span>Download</span></button>
          <button onclick="exportMarkdownReport()" class="text-xs bg-dark-850 hover:bg-dark-800 text-cyan-300 px-3 py-1.5 rounded-lg border border-cyan-500/30 transition flex items-center space-x-1.5 cursor-pointer"><span>📄</span><span>Report</span></button>
          <button onclick="copyPatchedCode()" class="text-xs bg-cyan-950/80 hover:bg-cyan-900 text-cyan-300 px-3 py-1.5 rounded-lg border border-cyan-700/50 transition flex items-center space-x-1.5 cursor-pointer"><span>📋</span><span>Copy</span></button>
        </div>
      </div>
      <div class="p-4 bg-dark-950/90 overflow-x-auto">
        <pre id="diffOutput" class="text-xs leading-relaxed font-mono whitespace-pre text-gray-300"></pre>
      </div>
    </div>

  </main>
  </div>

  <!-- Toast box -->
  <div id="toastBox" class="fixed bottom-5 right-5 z-50 flex flex-col space-y-2 pointer-events-none"></div>

  <script>
    
    let currentRightTab = 'issues';

    async function runAiDeepReview() {
      const code = document.getElementById('codeEditor').value;
      if (!code.trim()) {
        showToast('Please enter or load code first!', 'amber');
        return;
      }

      const out = document.getElementById('aiReviewOutput');
      const btn = document.getElementById('runAiReviewBtn');
      if (btn) btn.innerHTML = '<span>⏳</span><span>Gemini Analyzing...</span>';
      if (out) {
        out.innerHTML = `
          <div class="p-8 text-center space-y-3">
            <div class="inline-block w-8 h-8 border-2 border-purple-500/30 border-t-purple-400 rounded-full animate-spin"></div>
            <div class="space-y-1">
              <h5 class="text-xs font-bold text-purple-300 dark:text-purple-300 ai-loading-title">Gemini Analyzing Code...</h5>
              <p class="text-[11px] text-gray-400 ai-loading-sub">Inspecting AST structure, algorithmic complexity & bug risks</p>
            </div>
          </div>
        `;
      }

      try {
        const res = await fetch('/api/ai-review', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ code, language: currentLanguage })
        });
        const data = await res.json();
        if (!res.ok) {
          showToast(data.detail || 'AI review failed.', 'red');
          return;
        }

        if (!data.available) {
          out.innerHTML = `
            <div class="p-4 rounded-xl border border-amber-500/40 bg-amber-950/30 text-amber-200 dark:text-amber-200 space-y-2">
              <div class="flex items-center space-x-2">
                <span class="text-base">🔑</span>
                <span class="font-bold text-amber-300 dark:text-amber-300 text-xs uppercase tracking-wide">Gemini AI Setup</span>
              </div>
              <p class="text-xs leading-relaxed opacity-95">${escapeHtml(data.message)}</p>
            </div>
          `;
          return;
        }

        let optsHtml = (data.optimizations || []).map(opt => `
          <div class="ai-card-opt p-3.5 rounded-xl border space-y-1.5 shadow-sm transition">
            <span class="font-bold ai-title block text-xs">⚡ ${escapeHtml(opt.title)}</span>
            <p class="ai-desc text-[11px] leading-relaxed">${escapeHtml(opt.description)}</p>
          </div>
        `).join('') || '<p class="text-gray-400 italic">No critical algorithmic bottlenecks identified.</p>';

        let bugsHtml = (data.bug_risks || []).map(bug => `
          <div class="ai-card-bug p-3.5 rounded-xl border space-y-1.5 shadow-sm transition">
            <span class="font-bold ai-title block text-xs">⚠️ ${escapeHtml(bug.title)}</span>
            <p class="ai-desc text-[11px] leading-relaxed">${escapeHtml(bug.description)}</p>
          </div>
        `).join('') || '<p class="text-gray-400 italic">No critical unhandled exceptions flagged.</p>';

        let practicesHtml = (data.best_practices || []).map(tip => `
          <li class="ai-desc text-[11px] leading-relaxed flex items-start space-x-2">
            <span class="text-purple-400 font-bold shrink-0">💡</span>
            <span>${escapeHtml(tip)}</span>
          </li>
        `).join('');

        const modelTag = data.model_used || 'Gemini Flash Engine';
        const noticeHtml = data.cloud_notice ? `
          <div class="p-2 rounded-lg bg-dark-850/50 border border-white/5 text-[10px] text-gray-400 flex items-center space-x-1.5">
            <span>ℹ️</span><span>${escapeHtml(data.cloud_notice)}</span>
          </div>
        ` : '';

        out.innerHTML = `
          <div class="ai-assessment-card p-4 rounded-xl border space-y-2.5 shadow-sm">
            <div class="flex items-center justify-between">
              <div class="flex items-center space-x-2">
                <span class="font-bold uppercase tracking-wider ai-assessment-title text-[11px]">Executive Assessment</span>
                <span class="px-2 py-0.5 rounded-full text-[9px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/40">${escapeHtml(modelTag)}</span>
              </div>
              <span class="px-2.5 py-0.5 rounded-lg bg-emerald-500/15 text-emerald-300 font-bold border border-emerald-500/30 text-[10px]">Score: ${data.cleanliness_score || 8.5}/10</span>
            </div>
            <p class="ai-desc text-xs leading-relaxed">${escapeHtml(data.overall_assessment)}</p>
          </div>

          <div class="space-y-2">
            <span class="font-bold ai-section-title uppercase tracking-wider text-[10px] block">Algorithmic Optimizations</span>
            ${optsHtml}
          </div>

          <div class="space-y-2">
            <span class="font-bold ai-section-title uppercase tracking-wider text-[10px] block">Bug Risks & Edge Cases</span>
            ${bugsHtml}
          </div>

          ${practicesHtml ? `
          <div class="ai-card-tips p-3.5 rounded-xl border space-y-2">
            <span class="font-bold ai-section-title uppercase tracking-wider text-[10px] block">Engineering Best Practices</span>
            <ul class="space-y-1.5 pl-0.5">${practicesHtml}</ul>
          </div>` : ''}

          ${noticeHtml}
        `;

        showToast('🧠 Gemini AI Deep Code Review complete!', 'fuchsia');
      } catch (err) {
        showToast('Error during AI review: ' + err.message, 'red');
      } finally {
        if (btn) btn.innerHTML = '<span>🚀</span><span>Run Review</span>';
      }
    }

    function switchRightTab(tabId) {
      currentRightTab = tabId;
      const tabs = ['issues', 'complexity', 'style', 'aiReview', 'metrics'];
      tabs.forEach(t => {
        const pane = document.getElementById('tabPane' + t.charAt(0).toUpperCase() + t.slice(1));
        const btn = document.getElementById('tabBtn' + t.charAt(0).toUpperCase() + t.slice(1));
        if (pane) {
          if (t === tabId) {
            pane.classList.remove('hidden');
            pane.classList.add('flex');
          } else {
            pane.classList.add('hidden');
            pane.classList.remove('flex');
          }
        }
        if (btn) {
          if (t === tabId) {
            btn.classList.add('tab-btn-active');
            btn.classList.remove('tab-btn-inactive');
          } else {
            btn.classList.remove('tab-btn-active');
            btn.classList.add('tab-btn-inactive');
          }
        }
      });
    }

let currentLanguage = 'python';
    let currentIssues = [];
    let activeFilter = 'all';
    let lastPatchedCode = '';

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

    // ─── Theme ─────────────────────────────────────────────
    let currentThemeMode = 'system';

    function initTheme() {
      const saved = localStorage.getItem('docudoctor_theme') || 'system';
      setTheme(saved, false);
    }

    function setTheme(mode, notify = true) {
      currentThemeMode = mode;
      localStorage.setItem('docudoctor_theme', mode);
      const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
      const effective = mode === 'system' ? (prefersDark ? 'dark' : 'light') : mode;
      effective === 'dark'
        ? document.documentElement.classList.add('dark')
        : document.documentElement.classList.remove('dark');

      const icons = { system: '💻', dark: '🌙', light: '☀️' };
      const labels = { system: 'System', dark: 'Dark', light: 'Light' };
      const icon = document.getElementById('themeActiveIcon');
      const text = document.getElementById('themeActiveText');
      if (icon) icon.innerText = icons[mode];
      if (text) text.innerText = labels[mode];

      ['system','dark','light'].forEach(m => {
        const el = document.getElementById('check' + m.charAt(0).toUpperCase() + m.slice(1));
        if (el) el.className = m === mode ? 'text-cyan-400 font-bold' : 'hidden';
      });

      closeThemeMenu();
      if (notify) showToast(`Theme: ${icons[mode]} ${labels[mode]}`, 'cyan');
    }

        function toggleGeminiPopover(e) {
      if (e) e.stopPropagation();
      closeProfileDropdown();
      closeThemeMenu();
      const p = document.getElementById('geminiPopover');
      if (!p) return;
      p.style.display = p.style.display === 'block' ? 'none' : 'block';
    }

    function closeGeminiPopover() {
      const p = document.getElementById('geminiPopover');
      if (p) p.style.display = 'none';
    }

    function openAiReviewFromPopover() {
      closeGeminiPopover();
      switchRightTab('aiReview');
      runAiDeepReview();
    }

    function toggleThemeMenu(e) {
      if (e) e.stopPropagation();
      closeProfileDropdown();
      closeGeminiPopover();
      const m = document.getElementById('themeMenu');
      if (!m) return;
      m.style.display = m.style.display === 'flex' ? 'none' : 'flex';
    }
    function closeThemeMenu() {
      const m = document.getElementById('themeMenu');
      if (m) m.style.display = 'none';
    }

    if (window.matchMedia) {
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
        if (currentThemeMode === 'system') setTheme('system', false);
      });
    }

    // ─── Profile dropdown ──────────────────────────────────
    function toggleProfileDropdown(e) {
      if (e) e.stopPropagation();
      closeThemeMenu();
      closeGeminiPopover();
      const m = document.getElementById('profileDropdown');
      if (!m) return;
      m.style.display = m.style.display === 'block' ? 'none' : 'block';
    }
    function closeProfileDropdown() {
      const m = document.getElementById('profileDropdown');
      if (m) m.style.display = 'none';
    }

    document.addEventListener('click', e => {
      const prof = document.getElementById('profileDropdown');
      const profBtn = document.getElementById('profileDropdownBtn');
      if (prof && !prof.contains(e.target) && (!profBtn || !profBtn.contains(e.target))) prof.style.display = 'none';
      const theme = document.getElementById('themeMenu');
      const themeBtn = document.getElementById('themeBtn');
      if (theme && !theme.contains(e.target) && (!themeBtn || !themeBtn.contains(e.target))) theme.style.display = 'none';
      const gem = document.getElementById('geminiPopover');
      const gemBtn = document.getElementById('geminiEngineBadge');
      if (gem && !gem.contains(e.target) && (!gemBtn || !gemBtn.contains(e.target))) gem.style.display = 'none';
    });

    // ─── Language ──────────────────────────────────────────
    function onLanguageChange(lang, autoLoad = true) {
      currentLanguage = lang;
      const conf = LANG_CONFIG[lang] || LANG_CONFIG.python;

      const icon = document.getElementById('langEmojiIcon');
      if (icon) icon.innerText = conf.icon;

      const sel = document.getElementById('languageSelect');
      if (sel && sel.value !== lang) sel.value = lang;

      const fi = document.getElementById('fileIcon');
      if (fi) fi.innerText = conf.icon;
      const fn = document.getElementById('fileNameDisplay');
      if (fn) fn.innerText = conf.name;

      const ss = document.getElementById('docStyle');
      if (ss) ss.innerHTML = conf.styles.map((n,i) => `<option value="${conf.styleValues[i]}" class="bg-dark-900 text-gray-200">${n}</option>`).join('');

      if (autoLoad) {
        document.getElementById('codeEditor').value = SAMPLES[lang] || SAMPLES.python;
        updateGutter();
        flashEditor();
        auditCode();
      }

      showToast(`Selected ${conf.icon} ${conf.label}`, 'cyan');
    }

    function selectLanguage(lang, autoLoad = true) { onLanguageChange(lang, autoLoad); }
    function loadSampleForLanguage() { onLanguageChange(currentLanguage, true); }

    function handleFileUpload(event) {
      const file = event.target.files[0];
      if (!file) return;
      const name = file.name;
      let lang = 'python';
      if (name.endsWith('.java')) lang = 'java';
      else if (name.endsWith('.cpp') || name.endsWith('.hpp') || name.endsWith('.cc')) lang = 'cpp';
      else if (name.endsWith('.c') || name.endsWith('.h')) lang = 'c';
      onLanguageChange(lang, false);
      document.getElementById('fileNameDisplay').innerText = name;
      const reader = new FileReader();
      reader.onload = e => {
        document.getElementById('codeEditor').value = e.target.result;
        updateGutter(); flashEditor();
        showToast(`Loaded ${name}`, 'emerald');
        auditCode();
      };
      reader.readAsText(file);
    }

    // ─── Editor utils ──────────────────────────────────────
    function updateGutter() {
      const editor = document.getElementById('codeEditor');
      const lines = editor.value.split('\\n').length || 1;
      const gutter = document.getElementById('gutter');
      let html = '';
      for (let i = 1; i <= lines; i++) html += `<div>${i}</div>`;
      gutter.innerHTML = html;
      document.getElementById('lineCountDisplay').innerText = `Lines: ${lines}`;
      document.getElementById('charCountDisplay').innerText = `Chars: ${editor.value.length}`;
    }

    function syncGutterScroll() {
      const editor = document.getElementById('codeEditor');
      document.getElementById('gutter').scrollTop = editor.scrollTop;
    }

    function flashEditor() {
      const e = document.getElementById('codeEditor');
      e.classList.add('ring-2','ring-cyan-500');
      setTimeout(() => e.classList.remove('ring-2','ring-cyan-500'), 450);
    }

    function clearEditor() {
      document.getElementById('codeEditor').value = '';
      updateGutter();
      resetDashboard();
      document.getElementById('diffSection').classList.add('hidden');
      currentIssues = [];
      showToast('Editor cleared.', 'gray');
    }

    function resetDashboard() {
      document.getElementById('scoreVal').innerText = '--';
      document.getElementById('gradeLetter').innerText = '?';
      document.getElementById('gradeBadge').innerText = 'Awaiting Code';
      document.getElementById('circleProgress').setAttribute('stroke-dasharray','0, 100');
      ['statFuncs','statDocs','statTyped'].forEach(id => document.getElementById(id).innerText = '--');
      document.getElementById('statMaintainability').innerText = '-- / 100';
      document.getElementById('statMiGrade').innerText = 'Grade -';
      document.getElementById('statComplexity').innerText = '--';
      document.getElementById('complexityStatus').innerText = 'Awaiting Audit';
      document.getElementById('countAll').innerText = '0';
      document.getElementById('countError').innerText = '0';
      document.getElementById('countWarning').innerText = '0';
      document.getElementById('issueCountBadge').innerText = '0 issues';
      document.getElementById('issuesContainer').innerHTML = `<p class="text-gray-500 text-center py-8">No code analyzed yet.<br>Click <b>Load Sample</b> or paste code, then click <b>Audit Code</b>.</p>`;
      // Reset complexity
      document.getElementById('overallTimeBig').innerText = 'Time: --';
      document.getElementById('overallSpaceBig').innerText = 'Space: --';
      document.getElementById('complexityFnList').innerHTML = '<p class="text-gray-500 text-center py-6">Run <b>Audit Code</b> to estimate complexity.</p>';
      // Reset style
      document.getElementById('styleScoreVal').innerText = '--';
      document.getElementById('styleGradeBadge').innerText = 'Grade -';
      document.getElementById('styleScoreBar').style.width = '0%';
      ['styleNaming','styleStructure','styleFormat','styleTotal'].forEach(id => document.getElementById(id).innerText = '--');
      document.getElementById('styleIssueList').innerHTML = '<p class="text-gray-500 text-center py-14">Run <b>Audit Code</b> to review style and structural conventions.</p>';
      const fQuick = document.getElementById('statFuncsQuick');
      if (fQuick) fQuick.innerText = '--';
      const miQuick = document.getElementById('statMiQuick');
      if (miQuick) miQuick.innerText = '--';
      const compQuick = document.getElementById('statComplexityQuick');
      if (compQuick) compQuick.innerText = '--';
      const styleQuick = document.getElementById('statStyleQuick');
      if (styleQuick) styleQuick.innerText = '--';
      const tabCnt = document.getElementById('tabCountIssues');
      if (tabCnt) tabCnt.innerText = '0';
      const tabComp = document.getElementById('tabBadgeComplexity');
      if (tabComp) tabComp.innerText = '--';
      const tabSt = document.getElementById('tabBadgeStyle');
      if (tabSt) tabSt.innerText = '--';
    }

    // ─── Audit ─────────────────────────────────────────────
    async function auditCode() {
      const code = document.getElementById('codeEditor').value;
      if (!code.trim()) { showToast('Please enter or upload code first!', 'amber'); return; }

      try {
        // Run all three analyses in parallel
        const [auditRes, complexityRes, styleRes] = await Promise.all([
          fetch('/api/audit', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({code, language:currentLanguage}) }),
          fetch('/api/complexity', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({code, language:currentLanguage}) }),
          fetch('/api/style', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({code, language:currentLanguage}) }),
        ]);

        const auditData = await auditRes.json();
        const complexityData = complexityRes.ok ? await complexityRes.json() : null;
        const styleData = styleRes.ok ? await styleRes.json() : null;

        if (!auditRes.ok) { showToast(auditData.detail || 'Audit error.', 'red'); return; }

        currentIssues = auditData.issues || [];
        renderDashboard(auditData);
        renderIssues();
        if (complexityData) renderComplexity(complexityData);
        if (styleData) renderStyle(styleData);

        showToast(`Audit ✓ — Health ${auditData.score}% · MI ${auditData.maintainability_index}% · Style ${styleData ? styleData.style_score : '--'}%`, 'emerald');
      } catch (err) {
        showToast('Error connecting to server: ' + err.message, 'red');
      }
    }

    // ─── Render helpers ────────────────────────────────────
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
      document.getElementById('statMaintainability').innerText = `${data.maintainability_index} / 100`;
      document.getElementById('statMiGrade').innerText = `Grade ${data.maintainability_grade}`;
      document.getElementById('statComplexity').innerText = data.avg_complexity;

      const compStatus = document.getElementById('complexityStatus');
      const avgComp = data.avg_complexity || 1.0;
      if (avgComp <= 5) { compStatus.innerText = 'Low Risk'; compStatus.className = 'text-[10px] font-semibold text-emerald-400'; }
      else if (avgComp <= 10) { compStatus.innerText = 'Moderate'; compStatus.className = 'text-[10px] font-semibold text-amber-400'; }
      else { compStatus.innerText = 'High Risk'; compStatus.className = 'text-[10px] font-semibold text-red-400'; }

      document.getElementById('issueCountBadge').innerText = `${data.issues.length} issues`;
      document.getElementById('countAll').innerText = data.issues.length;
      document.getElementById('countError').innerText = data.issues.filter(i => i.severity === 'ERROR').length;
      document.getElementById('countWarning').innerText = data.issues.filter(i => i.severity === 'WARNING').length;

      // Update executive vitals summary chips
      const fQuick = document.getElementById('statFuncsQuick');
      if (fQuick) fQuick.innerText = `${data.total_functions} fn`;
      const miQuick = document.getElementById('statMiQuick');
      if (miQuick) miQuick.innerText = `${data.maintainability_index} (${data.maintainability_grade})`;
      const compQuick = document.getElementById('statComplexityQuick');
      if (compQuick) compQuick.innerText = `${data.avg_complexity} avg`;
      const tabCnt = document.getElementById('tabCountIssues');
      if (tabCnt) tabCnt.innerText = data.issues.length;
    }

    // ── Complexity render ──────────────────────────────────
    const RISK_COLORS = {
      low: { bg: 'bg-emerald-950/70', text: 'text-emerald-300', border: 'border-emerald-700/40' },
      medium: { bg: 'bg-amber-950/70', text: 'text-amber-300', border: 'border-amber-700/40' },
      high: { bg: 'bg-orange-950/70', text: 'text-orange-300', border: 'border-orange-700/40' },
      critical: { bg: 'bg-red-950/70', text: 'text-red-300', border: 'border-red-700/40' },
    };

    function renderComplexity(data) {
      const timeEl = document.getElementById('overallTimeBig');
      const spaceEl = document.getElementById('overallSpaceBig');
      const listEl = document.getElementById('complexityFnList');

      const riskCls = RISK_COLORS[data.overall_risk] || RISK_COLORS.low;
      timeEl.innerText = `Time: ${data.overall_time}`;
      timeEl.className = `text-xs font-mono font-bold px-2 py-0.5 rounded-lg ${riskCls.bg} ${riskCls.text} border ${riskCls.border}`;
      spaceEl.innerText = `Space: ${data.overall_space}`;
      spaceEl.className = `text-xs font-mono font-bold px-2.5 py-1 rounded-lg bg-violet-950/70 text-violet-300 border border-violet-700/40`;
      const tabComp = document.getElementById('tabBadgeComplexity');
      if (tabComp) tabComp.innerText = data.overall_time;

      if (!data.functions || data.functions.length === 0) {
        listEl.innerHTML = `<p class="text-gray-500 text-center py-4">${escapeHtml(data.summary || 'No functions detected.')}</p>`;
        return;
      }

      listEl.innerHTML = data.functions.map(fn => {
        const c = RISK_COLORS[fn.risk] || RISK_COLORS.low;
        return `
          <div class="fn-row p-2.5 rounded-xl bg-dark-850/70 border border-white/[0.05] hover:border-white/10 transition space-y-1.5">
            <div class="flex items-center justify-between">
              <span class="font-mono font-semibold text-cyan-300 text-xs">${escapeHtml(fn.name)}</span>
              <span class="text-[9px] text-gray-500">L${fn.line}</span>
            </div>
            <div class="flex items-center space-x-2">
              <span class="text-[10px] font-mono font-bold px-2 py-0.5 rounded ${c.bg} ${c.text} border ${c.border}">⏱ ${escapeHtml(fn.time_complexity)}</span>
              <span class="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-violet-950/60 text-violet-300 border border-violet-700/30">📦 ${escapeHtml(fn.space_complexity)}</span>
            </div>
            <p class="text-[10px] text-gray-400 leading-relaxed">${escapeHtml(fn.time_reason)}</p>
          </div>
        `;
      }).join('');
    }

    // ── Style render ───────────────────────────────────────
    function renderStyle(data) {
      const score = data.style_score;
      const grade = data.style_grade;
      const label = data.style_label;

      document.getElementById('styleScoreVal').innerText = `${score}/100`;
      const gradeBadge = document.getElementById('styleGradeBadge');
      gradeBadge.innerText = `${grade} · ${label}`;

      const gradeColors = { A: 'bg-emerald-950 text-emerald-300 border-emerald-700/60', B: 'bg-cyan-950 text-cyan-300 border-cyan-700/60', C: 'bg-amber-950 text-amber-300 border-amber-700/60', D: 'bg-red-950 text-red-300 border-red-700/60' };
      gradeBadge.className = `text-[10px] font-bold px-1.5 py-0.5 rounded border ${gradeColors[grade] || gradeColors.D}`;

      // Score bar
      const bar = document.getElementById('styleScoreBar');
      bar.style.width = `${score}%`;
      if (score >= 85) bar.className = 'h-1.5 rounded-full bg-gradient-to-r from-emerald-500 to-cyan-400 transition-all duration-700';
      else if (score >= 70) bar.className = 'h-1.5 rounded-full bg-gradient-to-r from-cyan-500 to-blue-400 transition-all duration-700';
      else if (score >= 55) bar.className = 'h-1.5 rounded-full bg-gradient-to-r from-amber-500 to-orange-400 transition-all duration-700';
      else bar.className = 'h-1.5 rounded-full bg-gradient-to-r from-red-500 to-rose-400 transition-all duration-700';

      // Breakdown
      const bd = data.breakdown || {};
      document.getElementById('styleNaming').innerText = bd.naming ?? 0;
      document.getElementById('styleStructure').innerText = bd.structure ?? 0;
      document.getElementById('styleFormat').innerText = bd.formatting ?? 0;
      document.getElementById('styleTotal').innerText = data.issues ? data.issues.length : 0;
      const styleQuick = document.getElementById('statStyleQuick');
      if (styleQuick) styleQuick.innerText = `${data.style_score}% (${data.style_grade})`;
      const tabSt = document.getElementById('tabBadgeStyle');
      if (tabSt) tabSt.innerText = `${data.style_score}%`;

      // Style issues
      const listEl = document.getElementById('styleIssueList');
      if (!data.issues || data.issues.length === 0) {
        listEl.innerHTML = `<div class="p-3 text-center text-emerald-400 font-semibold text-xs">✨ Style looks clean! No issues found.</div>`;
        return;
      }

      const sevColors = { error: 'bg-red-950/70 text-red-300 border-red-700/40', warning: 'bg-amber-950/70 text-amber-300 border-amber-700/40', info: 'bg-blue-950/70 text-blue-300 border-blue-700/40' };
      const catIcons = { naming: '🏷', structure: '🏗', formatting: '📐', complexity: '🔄' };

      listEl.innerHTML = data.issues.map(iss => {
        const sc = sevColors[iss.severity] || sevColors.info;
        return `
          <div class="p-2 rounded-lg bg-dark-850/60 border border-white/[0.05] flex items-start space-x-2">
            <span class="text-sm flex-shrink-0">${catIcons[iss.category] || '📌'}</span>
            <div class="flex-1 min-w-0">
              <div class="flex items-center space-x-1.5 flex-wrap gap-1">
                <span class="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded border ${sc}">${escapeHtml(iss.code)}</span>
                <span class="text-[9px] text-gray-500">L${iss.line}</span>
              </div>
              <p class="text-[10px] text-gray-300 mt-0.5 leading-relaxed">${escapeHtml(iss.message)}</p>
            </div>
          </div>
        `;
      }).join('');
    }

    // ─── Issue list ────────────────────────────────────────
    function setFilter(filter) {
      activeFilter = filter;
      const all = document.getElementById('filterAll');
      const err = document.getElementById('filterError');
      const wrn = document.getElementById('filterWarning');
      all.className = filter === 'all' ? 'text-[11px] font-semibold text-cyan-400 bg-cyan-950/80 px-2.5 py-1 rounded-lg border border-cyan-700/50' : 'text-[11px] font-semibold text-gray-400 hover:text-white px-2 py-1 rounded-lg';
      err.className = filter === 'error' ? 'text-[11px] font-semibold text-red-400 bg-red-950/80 px-2.5 py-1 rounded-lg border border-red-700/50' : 'text-[11px] font-semibold text-gray-400 hover:text-red-400 px-2 py-1 rounded-lg';
      wrn.className = filter === 'warning' ? 'text-[11px] font-semibold text-amber-400 bg-amber-950/80 px-2.5 py-1 rounded-lg border border-amber-700/50' : 'text-[11px] font-semibold text-gray-400 hover:text-amber-400 px-2 py-1 rounded-lg';
      renderIssues();
    }

    function renderIssues() {
      const container = document.getElementById('issuesContainer');
      let filtered = currentIssues;
      if (activeFilter === 'error') filtered = currentIssues.filter(i => i.severity === 'ERROR');
      else if (activeFilter === 'warning') filtered = currentIssues.filter(i => i.severity === 'WARNING');

      if (filtered.length === 0) {
        container.innerHTML = currentIssues.length === 0
          ? `<div class="p-5 text-center text-emerald-400 font-semibold">✨ All documented, typed, and clean!</div>`
          : `<div class="p-5 text-center text-gray-400">No issues matching this filter.</div>`;
        return;
      }

      container.innerHTML = filtered.map(iss => {
        const bc = iss.severity === 'ERROR' ? 'bg-red-950/80 text-red-300 border-red-700/60' : (iss.severity === 'WARNING' ? 'bg-amber-950/80 text-amber-300 border-amber-700/60' : 'bg-cyan-950/80 text-cyan-300 border-cyan-700/60');
        let fixBtn = '';
        if (iss.can_fix) {
          const lbl = iss.issue_type === 'Mutable Default Arg' ? 'Heal Mutable Default'
                    : iss.issue_type === 'Missing Return Type' ? 'Infer Return Type'
                    : 'Inject Docstring';
          fixBtn = `<button onclick="fixSpecific('${iss.entity}')" class="mt-1.5 text-[11px] font-semibold bg-fuchsia-950/80 hover:bg-fuchsia-800 text-fuchsia-200 border border-fuchsia-600/50 px-3 py-1 rounded-lg flex items-center space-x-1.5 transition w-fit active:scale-95 cursor-pointer"><span>⚡</span><span>${lbl}</span></button>`;
        }
        return `
          <div class="issue-card p-2.5 rounded-xl bg-dark-850/80 border border-white/[0.06] flex flex-col space-y-1 hover:border-white/10 transition">
            <div class="flex items-center justify-between flex-wrap gap-1">
              <div class="flex items-center space-x-1.5">
                <span class="px-1.5 py-0.5 rounded text-[10px] font-bold border ${bc}">L${iss.line}</span>
                <span class="text-cyan-300 font-mono font-semibold text-xs">${escapeHtml(iss.entity)}</span>
                <span class="text-gray-500 text-[10px]">(${iss.entity_type})</span>
              </div>
              <span class="text-[9px] uppercase font-bold text-gray-500 tracking-wider">${iss.issue_type}</span>
            </div>
            <p class="text-gray-300 text-[11px] leading-relaxed">${escapeHtml(iss.message)}</p>
            <div class="p-1.5 rounded-lg bg-dark-950/70 border border-white/[0.04] text-gray-400 text-[10px] italic">💡 ${escapeHtml(iss.recommendation)}</div>
            ${fixBtn}
          </div>`;
      }).join('');
    }

    // ─── Fix actions ───────────────────────────────────────
    async function fixSpecific(entityName) {
      const code = document.getElementById('codeEditor').value;
      const style = document.getElementById('docStyle').value;
      try {
        const res = await fetch('/api/fix', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({code, language:currentLanguage, style, target:entityName, use_ai: true}) });
        const data = await res.json();
        if (!res.ok) { showToast(data.detail || 'Fix failed.', 'red'); return; }
        lastPatchedCode = data.patched_code;
        document.getElementById('codeEditor').value = data.patched_code;
        updateGutter(); flashEditor();
        renderDiff(data.diff);
        showToast(`✨ Fixed '${entityName}'!`, 'fuchsia');
        auditCode();
      } catch (err) { showToast('Error fixing: ' + err.message, 'red'); }
    }

    async function fixCode() {
      const code = document.getElementById('codeEditor').value;
      if (!code.trim()) { showToast('Please enter or upload code first!', 'amber'); return; }
      const style = document.getElementById('docStyle').value;
      try {
        const res = await fetch('/api/fix', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({code, language:currentLanguage, style, use_ai: true}) });
        const data = await res.json();
        if (!res.ok) { showToast(data.detail || 'Fix failed.', 'red'); return; }
        lastPatchedCode = data.patched_code;
        document.getElementById('codeEditor').value = data.patched_code;
        updateGutter(); flashEditor();
        renderDiff(data.diff);
        showToast(`✨ Healed ${data.patched_count} item(s)!`, 'fuchsia');
        auditCode();
      } catch (err) { showToast('Error healing: ' + err.message, 'red'); }
    }

    function renderDiff(diff) {
      document.getElementById('diffSection').classList.remove('hidden');
      document.getElementById('diffOutput').innerHTML = diff.split('\\n').map(line => {
        if (line.startsWith('+')) return `<span class="text-emerald-400 font-medium">${escapeHtml(line)}</span>`;
        if (line.startsWith('-')) return `<span class="text-red-400 font-medium">${escapeHtml(line)}</span>`;
        if (line.startsWith('@')) return `<span class="text-cyan-400 font-semibold">${escapeHtml(line)}</span>`;
        return `<span class="text-gray-500">${escapeHtml(line)}</span>`;
      }).join('\\n');
    }

    function copyPatchedCode() {
      const code = lastPatchedCode || document.getElementById('codeEditor').value;
      if (!code) return showToast('No code to copy.', 'amber');
      navigator.clipboard.writeText(code).then(() => showToast('📋 Copied!', 'emerald'));
    }

    function downloadCode() {
      const code = document.getElementById('codeEditor').value;
      if (!code.trim()) return showToast('No code to download.', 'amber');
      const conf = LANG_CONFIG[currentLanguage] || LANG_CONFIG.python;
      const a = Object.assign(document.createElement('a'), {
        href: URL.createObjectURL(new Blob([code], {type:'text/plain'})),
        download: `healed_${conf.name}`
      });
      a.click();
      URL.revokeObjectURL(a.href);
      showToast(`📥 Downloaded healed_${conf.name}`, 'emerald');
    }

    async function exportMarkdownReport() {
      const code = document.getElementById('codeEditor').value;
      if (!code.trim()) { showToast('Load code first!', 'amber'); return; }
      const conf = LANG_CONFIG[currentLanguage] || LANG_CONFIG.python;
      try {
        const res = await fetch('/api/report', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({code, language:currentLanguage, filename:conf.name}) });
        const data = await res.json();
        if (!res.ok) { showToast(data.detail || 'Report failed.', 'red'); return; }
        const a = Object.assign(document.createElement('a'), {
          href: URL.createObjectURL(new Blob([data.report], {type:'text/markdown'})),
          download: data.filename || 'DOCUDOCTOR_REPORT.md'
        });
        a.click();
        URL.revokeObjectURL(a.href);
        showToast('📄 Exported ' + (data.filename || 'DOCUDOCTOR_REPORT.md'), 'emerald');
      } catch (err) { showToast('Report error: ' + err.message, 'red'); }
    }

    // ─── Toast ─────────────────────────────────────────────
    function showToast(message, color = 'cyan') {
      const box = document.getElementById('toastBox');
      const colorMap = { cyan:'bg-cyan-400', emerald:'bg-emerald-400', red:'bg-red-400', amber:'bg-amber-400', fuchsia:'bg-fuchsia-400', gray:'bg-gray-500' };
      const toast = document.createElement('div');
      toast.className = `animate-toast toast-box px-4 py-2.5 rounded-xl text-xs font-semibold text-white shadow-2xl flex items-center space-x-2.5 border border-white/10 bg-dark-900/95 backdrop-blur-xl pointer-events-auto`;
      toast.innerHTML = `<span class="w-2 h-2 rounded-full ${colorMap[color]||colorMap.cyan}"></span><span>${escapeHtml(message)}</span>`;
      box.appendChild(toast);
      setTimeout(() => { toast.style.opacity='0'; toast.style.transition='opacity 0.25s'; setTimeout(()=>toast.remove(),250); }, 3000);
    }

    function escapeHtml(text) {
      if (!text) return '';
      return String(text).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    }

    // ─── Cyberpunk / Sci-Fi Audio Synthesizer (Web Audio API) ───
    let audioCtx = null;
    let masterCompressor = null;
    let masterOut = null;
    let sfxEnabled = true;
    let riserHasPlayed = false;

    function getAudioCtx() {
      if (!audioCtx) {
        const AudioClass = window.AudioContext || window.webkitAudioContext;
        if (AudioClass) {
          audioCtx = new AudioClass();
          try {
            masterCompressor = audioCtx.createDynamicsCompressor();
            masterCompressor.threshold.setValueAtTime(-12, audioCtx.currentTime);
            masterCompressor.knee.setValueAtTime(24, audioCtx.currentTime);
            masterCompressor.ratio.setValueAtTime(10, audioCtx.currentTime);
            masterCompressor.attack.setValueAtTime(0.003, audioCtx.currentTime);
            masterCompressor.release.setValueAtTime(0.2, audioCtx.currentTime);

            masterOut = audioCtx.createGain();
            masterOut.gain.setValueAtTime(0.85, audioCtx.currentTime);

            masterCompressor.connect(masterOut);
            masterOut.connect(audioCtx.destination);
          } catch (e) {}
        }
      }
      if (audioCtx && audioCtx.state === 'suspended') {
        audioCtx.resume().catch(() => {});
      }
      return audioCtx;
    }

    function getAudioDest() {
      const ctx = getAudioCtx();
      if (!ctx) return null;
      return masterCompressor || ctx.destination;
    }

    // Soft saturation curve generator for analog warmth and aggressive harmonics
    function makeDistortionCurve(amount = 20) {
      const n_samples = 44100;
      const curve = new Float32Array(n_samples);
      const deg = Math.PI / 180;
      for (let i = 0; i < n_samples; ++i) {
        const x = (i * 2) / n_samples - 1;
        curve[i] = ((3 + amount) * x * 20 * deg) / (Math.PI + amount * Math.abs(x));
      }
      return curve;
    }

    // White noise buffer generator for pneumatic whooshes and mechanical textures
    function createNoiseBuffer(ctx, duration = 1.6) {
      const bufferSize = Math.floor(ctx.sampleRate * duration);
      const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
      const output = buffer.getChannelData(0);
      for (let i = 0; i < bufferSize; i++) {
        output[i] = Math.random() * 2 - 1;
      }
      return buffer;
    }

    // Actual execution of the catchy cyberpunk riser
    function playCyberpunkRiserActual(ctx) {
      try {
        const now = ctx.currentTime;
        const dest = getAudioDest();
        if (!dest) return;

        // ── 1. Catchy Melodic Cyber-Signature Motif (D4 -> F#4 -> A4 -> D5) ──
        const motif = [
          { f: 293.66, t: 0.00 },
          { f: 369.99, t: 0.16 },
          { f: 440.00, t: 0.32 },
          { f: 587.33, t: 0.48 }
        ];

        motif.forEach(note => {
          const osc1 = ctx.createOscillator();
          const osc2 = ctx.createOscillator();
          const gain = ctx.createGain();
          const filter = ctx.createBiquadFilter();
          const t = now + note.t;

          osc1.type = 'sawtooth';
          osc1.frequency.setValueAtTime(note.f, t);

          osc2.type = 'triangle';
          osc2.frequency.setValueAtTime(note.f * 1.006, t);

          filter.type = 'lowpass';
          filter.frequency.setValueAtTime(4500, t);
          filter.frequency.exponentialRampToValueAtTime(800, t + 0.42);

          gain.gain.setValueAtTime(0.001, t);
          gain.gain.linearRampToValueAtTime(0.35, t + 0.018);
          gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.45);

          osc1.connect(filter);
          osc2.connect(filter);
          filter.connect(gain);
          gain.connect(dest);

          osc1.start(t);
          osc2.start(t);
          osc1.stop(t + 0.48);
          osc2.stop(t + 0.48);
        });

        // ── 2. Pneumatic Cyber Whoosh (Sweeping Bandpass Riser) ──
        const noiseNode = ctx.createBufferSource();
        noiseNode.buffer = createNoiseBuffer(ctx, 1.8);
        const noiseFilter = ctx.createBiquadFilter();
        noiseFilter.type = 'bandpass';
        noiseFilter.Q.setValueAtTime(4.0, now);
        noiseFilter.frequency.setValueAtTime(240, now);
        noiseFilter.frequency.exponentialRampToValueAtTime(4200, now + 1.35);

        const noiseGain = ctx.createGain();
        noiseGain.gain.setValueAtTime(0.001, now);
        noiseGain.gain.linearRampToValueAtTime(0.28, now + 1.1);
        noiseGain.gain.exponentialRampToValueAtTime(0.0001, now + 1.45);

        noiseNode.connect(noiseFilter);
        noiseFilter.connect(noiseGain);
        noiseGain.connect(dest);
        noiseNode.start(now);
        noiseNode.stop(now + 1.5);

        // ── 3. Detuned Dual Supersaw Engine Drone ──
        const subOsc1 = ctx.createOscillator();
        const subOsc2 = ctx.createOscillator();
        const subBass = ctx.createOscillator();
        const synthFilter = ctx.createBiquadFilter();
        const distNode = ctx.createWaveShaper();
        const synthGain = ctx.createGain();

        synthFilter.type = 'lowpass';
        synthFilter.Q.setValueAtTime(5.0, now);
        synthFilter.frequency.setValueAtTime(140, now);
        synthFilter.frequency.exponentialRampToValueAtTime(1800, now + 1.25);

        distNode.curve = makeDistortionCurve(18);
        distNode.oversample = '2x';

        synthGain.gain.setValueAtTime(0.001, now);
        synthGain.gain.linearRampToValueAtTime(0.32, now + 0.35);
        synthGain.gain.exponentialRampToValueAtTime(0.0001, now + 1.45);

        subOsc1.type = 'sawtooth';
        subOsc1.frequency.setValueAtTime(55, now);
        subOsc1.frequency.exponentialRampToValueAtTime(110, now + 1.25);

        subOsc2.type = 'sawtooth';
        subOsc2.frequency.setValueAtTime(55.3, now);
        subOsc2.frequency.exponentialRampToValueAtTime(110.6, now + 1.25);

        subBass.type = 'sine';
        subBass.frequency.setValueAtTime(45, now);
        subBass.frequency.exponentialRampToValueAtTime(90, now + 1.25);

        subOsc1.connect(synthFilter);
        subOsc2.connect(synthFilter);
        subBass.connect(synthFilter);
        synthFilter.connect(distNode);
        distNode.connect(synthGain);
        synthGain.connect(dest);

        subOsc1.start(now);
        subOsc2.start(now);
        subBass.start(now);
        subOsc1.stop(now + 1.48);
        subOsc2.stop(now + 1.48);
        subBass.stop(now + 1.48);
      } catch (err) {}
    }

    // 1. Cyberpunk Pneumatic Tech Riser with Autoplay protection
    function playCyberpunkRiser() {
      if (!sfxEnabled || riserHasPlayed || welcomeDismissed) return;
      try {
        const ctx = getAudioCtx();
        if (!ctx) return;
        if (ctx.state === 'running') {
          riserHasPlayed = true;
          playCyberpunkRiserActual(ctx);
        } else {
          ctx.resume().then(() => {
            if (ctx.state === 'running' && !riserHasPlayed && !welcomeDismissed) {
              riserHasPlayed = true;
              playCyberpunkRiserActual(ctx);
            }
          }).catch(() => {});
        }
      } catch (err) {}
    }

    // 2. Holographic HUD Optical Micro-Tick (Tactile mechanical click + FM laser chirp)
    function playCyberpunkTick(freq = 1400) {
      if (!sfxEnabled) return;
      try {
        const ctx = getAudioCtx();
        if (!ctx) return;
        const now = ctx.currentTime;
        const dest = getAudioDest();
        if (!dest) return;

        // Tactile mechanical noise impulse
        const noise = ctx.createBufferSource();
        noise.buffer = createNoiseBuffer(ctx, 0.03);
        const noiseFilt = ctx.createBiquadFilter();
        noiseFilt.type = 'highpass';
        noiseFilt.frequency.setValueAtTime(3600, now);
        const noiseG = ctx.createGain();
        noiseG.gain.setValueAtTime(0.22, now);
        noiseG.gain.exponentialRampToValueAtTime(0.0001, now + 0.028);
        noise.connect(noiseFilt);
        noiseFilt.connect(noiseG);
        noiseG.connect(dest);
        noise.start(now);
        noise.stop(now + 0.035);

        // Futuristic resonant laser micro-chirp
        const osc = ctx.createOscillator();
        const oscGain = ctx.createGain();
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(freq * 1.5, now);
        osc.frequency.exponentialRampToValueAtTime(freq, now + 0.035);

        oscGain.gain.setValueAtTime(0.001, now);
        oscGain.gain.linearRampToValueAtTime(0.35, now + 0.006);
        oscGain.gain.exponentialRampToValueAtTime(0.0001, now + 0.06);

        osc.connect(oscGain);
        oscGain.connect(dest);
        osc.start(now);
        osc.stop(now + 0.065);
      } catch (err) {}
    }

    // 3. Cyberpunk 808 Sub-Drop Boom + Catchy Grand Starlight Chord
    function playCyberpunkImpact() {
      if (!sfxEnabled) return;
      try {
        const ctx = getAudioCtx();
        if (!ctx) return;
        const now = ctx.currentTime;
        const dest = getAudioDest();
        if (!dest) return;

        // Layer A: Saturated 808 Sub-Bass Shockwave Impact
        const subOsc = ctx.createOscillator();
        const subDist = ctx.createWaveShaper();
        const subGain = ctx.createGain();

        subOsc.type = 'sine';
        subOsc.frequency.setValueAtTime(145, now);
        subOsc.frequency.exponentialRampToValueAtTime(44, now + 0.065);
        subOsc.frequency.exponentialRampToValueAtTime(28, now + 1.25);

        subDist.curve = makeDistortionCurve(16);
        subDist.oversample = '2x';

        subGain.gain.setValueAtTime(0.001, now);
        subGain.gain.linearRampToValueAtTime(0.55, now + 0.035);
        subGain.gain.exponentialRampToValueAtTime(0.0001, now + 1.3);

        subOsc.connect(subDist);
        subDist.connect(subGain);
        subGain.connect(dest);
        subOsc.start(now);
        subOsc.stop(now + 1.35);

        // Layer B: Catchy Grand Holographic Sci-Fi Chord (D4, F#4, A4, D5, A5)
        const chordFreqs = [293.66, 369.99, 440.00, 587.33, 880.00];
        chordFreqs.forEach((f, idx) => {
          const chordOsc = ctx.createOscillator();
          const chordGain = ctx.createGain();
          const t = now + idx * 0.022;

          chordOsc.type = 'sawtooth';
          chordOsc.frequency.setValueAtTime(f, t);

          const chordFilt = ctx.createBiquadFilter();
          chordFilt.type = 'lowpass';
          chordFilt.frequency.setValueAtTime(3800, t);
          chordFilt.frequency.exponentialRampToValueAtTime(900, t + 0.85);

          chordGain.gain.setValueAtTime(0.001, t);
          chordGain.gain.linearRampToValueAtTime(0.42, t + 0.025);
          chordGain.gain.exponentialRampToValueAtTime(0.0001, t + 0.95);

          chordOsc.connect(chordFilt);
          chordFilt.connect(chordGain);
          chordGain.connect(dest);
          chordOsc.start(t);
          chordOsc.stop(t + 1.0);
        });

        // Layer C: Hydraulic Air-Release Exhale (Highpass noise sweep)
        const airNode = ctx.createBufferSource();
        airNode.buffer = createNoiseBuffer(ctx, 0.65);
        const airFilt = ctx.createBiquadFilter();
        airFilt.type = 'highpass';
        airFilt.frequency.setValueAtTime(2600, now);
        airFilt.frequency.exponentialRampToValueAtTime(500, now + 0.45);

        const airGain = ctx.createGain();
        airGain.gain.setValueAtTime(0.28, now);
        airGain.gain.exponentialRampToValueAtTime(0.0001, now + 0.52);

        airNode.connect(airFilt);
        airFilt.connect(airGain);
        airGain.connect(dest);
        airNode.start(now);
        airNode.stop(now + 0.55);
      } catch (err) {}
    }

    // Aliases for compatibility
    const playCinematicSweep = playCyberpunkRiser;
    const playSciFiTick = playCyberpunkTick;
    const playQuantumChime = playCyberpunkImpact;

    let bootSequenceStarted = false;
    let currentAnimationPct = 0;

    // Handles user touch/click/key to immediately unmute audio in exact sync
    function handleAnyUserInteraction() {
      if (welcomeDismissed) return;
      const ctx = getAudioCtx();
      if (ctx && ctx.state === 'suspended') {
        ctx.resume().then(() => {
          if (welcomeDismissed) return;
          // If interaction occurs early (<= 25%), fire opening motif
          if (currentAnimationPct <= 25 && !riserHasPlayed) {
            riserHasPlayed = true;
            playCyberpunkRiserActual(ctx);
          }
          const hint = document.getElementById('welcomeAudioHint');
          if (hint) hint.classList.add('hidden');
          const osLabel = document.getElementById('welcomeOsLabel');
          if (osLabel) osLabel.classList.remove('hidden');
        }).catch(() => {});
      }
    }

    const userInitiatedBoot = handleAnyUserInteraction;
    const unlockAudioAndStart = handleAnyUserInteraction;
    const unlockAudioAndPlay = handleAnyUserInteraction;

    // ─── Synchronized 1:1 Boot Sequence (Audio + Animation in Lockstep) ───
    function startSyncedBootSequence() {
      if (bootSequenceStarted) return;
      bootSequenceStarted = true;

      const ctx = getAudioCtx();
      // Try playing opening riser immediately (succeeds if browser autoplay is permitted)
      if (ctx) {
        ctx.resume().then(() => {
          if (ctx.state === 'running' && !riserHasPlayed) {
            riserHasPlayed = true;
            playCyberpunkRiserActual(ctx);
          } else {
            // Autoplay held by browser: show subtle un-mute indicator
            const hint = document.getElementById('welcomeAudioHint');
            if (hint) hint.classList.remove('hidden');
            const osLabel = document.getElementById('welcomeOsLabel');
            if (osLabel) osLabel.classList.add('hidden');
          }
        }).catch(() => {});
      }

      const steps = [
        { pct: 15, text: '[AST.CORE] Compiling deterministic syntax tree...', hex: '0x7F4A', freq: 1100 },
        { pct: 38, text: '[METRICS] Calibrating cyclomatic complexity & MI...', hex: '0x8B12', freq: 1320 },
        { pct: 65, text: '[POLYGLOT] Python 3.13 · LLVM C/C++ · JVM armed...', hex: '0x9C33', freq: 1540 },
        { pct: 88, text: '[COGNITIVE] Gemini Flash AI coprocessor synced...', hex: '0xFA01', freq: 1880 },
        { pct: 100, text: '[SYS.ONLINE] All telemetry nominal. Entering studio...', hex: '0xFFFF', freq: 0 }
      ];

      const pctEl = document.getElementById('welcomeProgressPct');
      const textEl = document.getElementById('welcomeProgressText');
      const hexEl = document.getElementById('welcomeProgressHex');
      const segments = document.querySelectorAll('.hud-seg');

      currentAnimationPct = 0;
      let stepIdx = 0;

      const timer = setInterval(() => {
        currentAnimationPct += 2;
        if (currentAnimationPct > 100) currentAnimationPct = 100;

        if (pctEl) pctEl.innerText = `${currentAnimationPct}%`;

        // Update active neon segments
        if (segments && segments.length) {
          const activeCount = Math.floor((currentAnimationPct / 100) * segments.length);
          segments.forEach((seg, i) => {
            if (i < activeCount) {
              seg.style.backgroundColor = '#22d3ee';
              seg.style.boxShadow = '0 0 10px rgba(34, 211, 238, 0.7)';
            }
          });
        }

        // Advance telemetry messages and play synchronized cyberpunk audio tick
        if (stepIdx < steps.length && currentAnimationPct >= steps[stepIdx].pct) {
          if (textEl) textEl.innerText = steps[stepIdx].text;
          if (hexEl) hexEl.innerText = steps[stepIdx].hex;
          if (steps[stepIdx].freq > 0) {
            playCyberpunkTick(steps[stepIdx].freq);
          }
          stepIdx++;
        }

        if (currentAnimationPct >= 100) {
          clearInterval(timer);
          playCyberpunkImpact();
          setTimeout(() => {
            dismissWelcomeIntro();
          }, 350);
        }
      }, 35);
    }

    // ─── Welcome Intro Animation & Studio Move ────────────────
    let welcomeDismissed = false;
    function dismissWelcomeIntro() {
      if (welcomeDismissed) return;
      welcomeDismissed = true;

      // Disconnect all temporary welcome activation listeners so workspace interaction is clean
      ['pointerdown', 'mousedown', 'touchstart', 'keydown'].forEach(evt => {
        window.removeEventListener(evt, handleAnyUserInteraction, { passive: true });
        window.removeEventListener(evt, handleAnyUserInteraction);
      });
      const overlay = document.getElementById('welcomeIntroOverlay');
      if (overlay) {
        overlay.removeEventListener('click', handleAnyUserInteraction);
      }

      const mainApp = document.getElementById('mainWorkspaceApp');
      const codeEditorPanel = document.getElementById('codeEditorPanel');

      // Cinematic warp exit on overlay
      if (overlay) {
        overlay.classList.add('welcome-exit-warp');
      }

      // Smooth kinetic move to reveal main studio screen
      if (mainApp) {
        mainApp.classList.add('studio-revealed');
      }

      // Laser scanline sweeping down the code editor
      if (codeEditorPanel) {
        codeEditorPanel.classList.add('editor-scanline-active');
      }

      setTimeout(() => {
        if (overlay) overlay.style.display = 'none';
        const ed = document.getElementById('codeEditor');
        if (ed) ed.focus();
      }, 620);
    }

    function initWelcomeAnimation() {
      // 1. One-time user gesture listeners on window and overlay to unmute immediately on touch/click
      ['pointerdown', 'mousedown', 'touchstart', 'keydown'].forEach(evt => {
        window.addEventListener(evt, handleAnyUserInteraction, { passive: true });
      });
      const overlay = document.getElementById('welcomeIntroOverlay');
      if (overlay) {
        overlay.addEventListener('click', handleAnyUserInteraction);
      }

      // 2. Start the loading animation automatically on page load!
      startSyncedBootSequence();
    }

    // ─── Init ──────────────────────────────────────────────
    window.addEventListener('DOMContentLoaded', () => {
      initTheme();
      // Initialize completely blank without pre-coming code
      onLanguageChange('python', false);
      const ed = document.getElementById('codeEditor');
      if (ed) ed.value = '';
      updateGutter();
      resetDashboard();
      initWelcomeAnimation();
    });
  </script>
</body>
</html>
"""
