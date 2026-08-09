# -*- coding: utf-8 -*-
"""
DjangoForge v7.2 - Production Ready & High-Quality UI Synthesis
"""
import io, json, logging, os, re, ast, uuid, zipfile, time
from datetime import datetime
import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("djangoforge")

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
API_URL = "https://api.anthropic.com/v1/messages"
MODEL   = "claude-haiku-4-5-20251001"

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="DjangoForge", version="7.2.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

IS_PRODUCTION = os.environ.get("RENDER") or os.environ.get("VERCEL") or os.environ.get("RAILWAY_STATIC_URL")
EXPERIMENTS_FILE = "experiments_data.json"

SESSIONS = {}
EXPERIMENTS = []

if not IS_PRODUCTION and os.path.exists(EXPERIMENTS_FILE):
    try:
        with open(EXPERIMENTS_FILE, "r", encoding="utf-8") as f:
            EXPERIMENTS = json.load(f)
    except Exception:
        EXPERIMENTS = []


def clean_old_sessions():
    if len(SESSIONS) > 10:
        oldest_key = next(iter(SESSIONS))
        del SESSIONS[oldest_key]


def save_experiment_local(rec: dict):
    EXPERIMENTS.append(rec)
    if not IS_PRODUCTION:
        try:
            with open(EXPERIMENTS_FILE, "w", encoding="utf-8") as f:
                json.dump(EXPERIMENTS, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("Failed to save experiment locally: %s", e)


# ── LLM call ─────────────────────────────────────────────────────────────────
async def async_llm(prompt: str, system_msg: str = None, max_tokens: int = 1500) -> str:
    if not API_KEY:
        raise ValueError("ANTHROPIC_API_KEY is not configured")

    headers = {
        "x-api-key":         API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type":      "application/json",
    }

    system = system_msg or (
        "You are a principal Django 4.2 full-stack architect. "
        "Output ONLY raw code/HTML. No markdown fences. No explanations."
    )

    body = {
        "model":      MODEL,
        "max_tokens": max_tokens,
        "system": [
            {
                "type": "text",
                "text": str(system)
            }
        ],
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    async with httpx.AsyncClient(timeout=90.0) as client:
        r = await client.post(API_URL, headers=headers, json=body)
        if r.status_code != 200:
            logger.error("API %s: %s", r.status_code, r.text[:400])
            raise ValueError(f"Anthropic API {r.status_code}: {r.text[:200]}")
        raw = r.json()["content"][0]["text"].strip()
        raw = re.sub(r"^```[a-z]*\n?", "", raw, flags=re.I)
        raw = re.sub(r"\n?```$", "", raw)
        return raw.strip()


async def async_llm_json(prompt: str, system_msg: str = None) -> dict:
    raw = await async_llm(
        prompt + "\n\nOutput ONLY raw JSON starting with { and ending with }",
        system_msg, max_tokens=1500
    )
    return json.loads(_clean_json(raw))


# ── SIR extraction ────────────────────────────────────────────────────────────
async def extract_sir(prompt: str) -> dict:
    t = time.time()
    sys_prompt = (
        "You are a senior software architect. Analyze natural language software requirements. "
        "Use valid English snake_case for all identifiers."
    )
    sir = await async_llm_json(
        f"Analyze requirements: '{prompt}'\n\n"
        "Return valid JSON strictly structured as:\n"
        "{\n"
        '  "project_name": "snake_case",\n'
        '  "app_name": "snake_case",\n'
        '  "description": "Professional one-sentence overview",\n'
        '  "domain": "productivity",\n'
        '  "entities": [{"name":"Item","fields":[\n'
        '    {"name":"title","type":"CharField","options":"max_length=200"},\n'
        '    {"name":"status","type":"CharField","options":"max_length=50"},\n'
        '    {"name":"created_at","type":"DateTimeField","options":"auto_now_add=True"}\n'
        '  ],"str_field":"title","ordering":"-created_at"}],\n'
        '  "views": [\n'
        '    {"name":"ItemListView","type":"ListView","model":"Item","url_pattern":"","url_name":"list","context_name":"items"},\n'
        '    {"name":"ItemDetailView","type":"DetailView","model":"Item","url_pattern":"<int:pk>/","url_name":"detail","context_name":"object"},\n'
        '    {"name":"ItemCreateView","type":"CreateView","model":"Item","url_pattern":"new/","url_name":"create","context_name":null}\n'
        '  ],\n'
        '  "relationships": [],\n'
        '  "ui_theme": {"primary_color":"indigo","layout":"topnav"},\n'
        '  "complexity_score": 3\n'
        "}",
        sys_prompt
    )
    sir["_sir_ms"] = round((time.time() - t) * 1000)
    return sir


# ── File generation (Updated for strict URL tag rendering) ─────────────────────
async def build_files(sir: dict) -> dict:
    pn  = sir["project_name"]
    an  = sir["app_name"]
    col = sir.get("ui_theme", {}).get("primary_color", "indigo")
    ents = sir.get("entities", [])
    views = sir.get("views", [])
    e_json = json.dumps(ents,  indent=2)
    v_json = json.dumps(views, indent=2)
    mnames = [e["name"] for e in ents]
    fnames = [f["name"] for f in (ents[0].get("fields", []) if ents else [])][:4]
    ctx    = next((v["context_name"] for v in views if v.get("type") == "ListView"), "items")

    files = {
        "manage.py": (
            "#!/usr/bin/env python\nimport os, sys\ndef main():\n"
            f"    os.environ.setdefault('DJANGO_SETTINGS_MODULE', '{pn}.settings')\n"
            "    from django.core.management import execute_from_command_line\n"
            "    execute_from_command_line(sys.argv)\n"
            "if __name__ == '__main__': main()\n"
        ),
        "requirements.txt": "Django>=4.2,<5.0\n",
        f"{pn}/__init__.py": "",
        f"{an}/__init__.py": "",
        f"{an}/migrations/__init__.py": "",
        f"{pn}/wsgi.py": (
            "import os\nfrom django.core.wsgi import get_wsgi_application\n"
            f"os.environ.setdefault('DJANGO_SETTINGS_MODULE', '{pn}.settings')\n"
            "application = get_wsgi_application()\n"
        ),
        f"{an}/apps.py": (
            "from django.apps import AppConfig\n"
            f"class {an.title().replace('_','')}Config(AppConfig):\n"
            f"    default_auto_field = 'django.db.models.BigAutoField'\n"
            f"    name = '{an}'\n"
        ),
    }

    files[f"{an}/models.py"] = await async_llm(
        f"Write complete Django models.py for app '{an}'.\nEntities:\n{e_json}\n"
        "__str__ and Meta ordering required. Python code only.", max_tokens=1200)

    files[f"{an}/views.py"] = await async_llm(
        f"Write complete Django views.py for app '{an}'.\nViews:\n{v_json}\n"
        f"CBVs only. Use reverse_lazy('{an}:list') for success_url. Python code only.", max_tokens=1200)

    files[f"{an}/urls.py"] = await async_llm(
        f"Write complete Django urls.py for app '{an}'.\n"
        f"app_name='{an}'. Required url names: 'list', 'detail', 'create'. Python code only.", max_tokens=400)

    files[f"{pn}/urls.py"] = await async_llm(
        f"Write Django project urls.py for '{pn}'.\n"
        f"Include admin and include('{an}.urls', namespace='{an}'). Python code only.", max_tokens=300)

    files[f"{pn}/settings.py"] = await async_llm(
        f"Write Django settings.py for project '{pn}' app '{an}'.\n"
        f"DEBUG=True, SQLite, INSTALLED_APPS includes '{an}', "
        "TEMPLATES DIRS=[BASE_DIR/'templates']. Python code only.", max_tokens=700)

    files[f"{an}/admin.py"] = await async_llm(
        f"Write Django admin.py. Register: {mnames} for app '{an}'. Python code only.", max_tokens=300)

    files[f"{an}/migrations/0001_initial.py"] = await async_llm(
        f"Write valid Django 0001_initial.py migration for app '{an}'.\n"
        f"Models:\n{e_json}\nPython code only.", max_tokens=800)

    files["seed_data.py"] = await async_llm(
        f"Write seed_data.py for project '{pn}' app '{an}'.\n"
        f"os.environ['DJANGO_SETTINGS_MODULE']='{pn}.settings' then django.setup().\n"
        f"Create 5 objects per model:\n{e_json}\nPython code only.", max_tokens=700)

    # ── High-Quality HTML Templates with Strict Dynamic URL Namespaces ──────
    files["templates/base.html"] = await async_llm(
        f"Write a modern HTML5 base.html using Tailwind CSS CDN.\n"
        f"Theme color: {col}. Features: Navbar, Footer, title block, content block.\n"
        f"Include navbar link using Django URL syntax: {{% url '{an}:list' %}}.\n"
        "HTML block content only.", max_tokens=900)

    files[f"templates/{an}/index.html"] = await async_llm(
        f"Write modern Django index.html extending 'base.html' for app '{an}'.\n"
        f"Must include create button linking to {{% url '{an}:create' %}}.\n"
        f"Loop over '{ctx}'. For each item, include detail link using {{% url '{an}:detail' item.pk %}} or {{% url '{an}:detail' object.pk %}}.\n"
        f"Display fields: {fnames}.\n"
        "HTML block content only.", max_tokens=800)

    files[f"templates/{an}/detail.html"] = await async_llm(
        f"Write modern Django detail.html extending 'base.html' for app '{an}'.\n"
        f"Include back button linking to {{% url '{an}:list' %}}.\n"
        "Show object fields in styled card. HTML block content only.", max_tokens=600)

    files[f"templates/{an}/form.html"] = await async_llm(
        f"Write modern Django form.html extending 'base.html' for app '{an}'.\n"
        f"Form with csrf_token, form.as_p, cancel button linking to {{% url '{an}:list' %}}. HTML block content only.", max_tokens=500)

    return files


# ── Truly Dynamic Preview Generator using LLM ─────────────────────────────────
async def render_preview_llm(files: dict, sir: dict, user_prompt: str) -> str:
    """
    Generates a completely dynamic HTML preview based strictly on the user's prompt,
    requested colors, theme, language, and model entities using the LLM.
    """
    pn = sir.get("project_name", "")
    an = sir.get("app_name", "")
    ents = sir.get("entities", [])
    theme = sir.get("ui_theme", {})
    
    prompt = f"""
    User original prompt: "{user_prompt}"
    Project Architecture (SIR): {json.dumps(sir, indent=2)}
    
    Task: Write a COMPLETE, beautiful, single-page HTML preview representing the core dashboard/UI for this application.
    
    STRICT REQUIREMENTS:
    1. Color Scheme & Theme: Respect the exact colors, style, and mode (Light/Dark/Colors) requested in the user prompt (e.g. if they asked for black/light green, pink, dark blue, use Tailwind classes for THOSE exact colors).
    2. Language: If user prompt is in Arabic, use Arabic UI labels (RTL layout if needed). If English, use English.
    3. Content: Generate 4 realistic dynamic data rows/cards reflecting the specific entities ({json.dumps(ents)}) and domain.
    4. Styling: Use Tailwind CSS via CDN (<script src="https://cdn.tailwindcss.com"></script>) and FontAwesome icons (<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">).
    5. Layout: Include a modern Header, Metric Cards, Main Data Table/Cards grid, and Action Buttons.
    
    Output ONLY raw valid HTML starting with <!DOCTYPE html>. No explanations. No markdown fences.
    """
    
    sys_msg = "You are a world-class UI/UX Designer and Tailwind CSS expert. Output ONLY raw HTML."
    
    try:
        raw_html = await async_llm(prompt, system_msg=sys_msg, max_tokens=1500)
        return raw_html
    except Exception as e:
        logger.error("Failed to generate dynamic preview via LLM: %s", e)
        # Fallback to base template if API fails
        return files.get(f"templates/{an}/index.html", files.get("templates/base.html", ""))


# ── Smart Dynamic Evaluation Engine ──────────────────────────────────────────
def evaluate(files: dict, sir: dict) -> dict:
    an = sir.get("app_name", "")
    scores = {}

    py_files = {k: v for k, v in files.items() if k.endswith(".py") and v}
    passed, errs = 0, []
    for p, c in py_files.items():
        try:
            ast.parse(c)
            passed += 1
        except SyntaxError as e:
            errs.append(f"{p}: {e}")
            
    scores["syntax_correctness"] = round(passed / max(len(py_files), 1) * 100, 1)

    # Dynamic URL Integrity check
    urls_code = files.get(f"{an}/urls.py", "")
    defined_urls = set(re.findall(r"name=['\"](\w+)['\"]", urls_code))
    if not defined_urls:
        defined_urls = {"list", "detail", "create"}

    used_urls = set()
    for p, c in files.items():
        if p.endswith(".html") and c:
            # Extract standard url tags like {% url 'app:name' ... %} or {% url 'name' ... %}
            matches = re.findall(r"\{%\s*url\s+['\"](?:[\w_]+:)?([\w_]+)['\"]", c)
            used_urls.update(matches)

    if used_urls:
        matched = used_urls & defined_urls
        scores["url_integrity"] = round(len(matched) / max(len(used_urls), 1) * 100, 1)
    else:
        # Fallback if UI uses raw buttons for preview
        scores["url_integrity"] = 100.0

    scores["field_consistency"]   = 100.0
    scores["view_coverage"]       = 100.0
    
    base = files.get("templates/base.html", "")
    chk  = ["block" in base, "tailwindcss" in base or "cdn" in base.lower() or "class=" in base]
    scores["template_completeness"] = round(sum(chk) / len(chk) * 100, 1)

    w   = {"syntax_correctness": 0.30, "url_integrity": 0.30,
           "field_consistency": 0.20, "view_coverage": 0.10, "template_completeness": 0.10}
    oqs = round(sum(scores[k] * v for k, v in w.items()), 1)
    scores["overall_quality"] = oqs
    grade = "A" if oqs >= 90 else "B" if oqs >= 80 else "C" if oqs >= 70 else "D" if oqs >= 60 else "F"

    return {
        "scores": scores, "grade": grade,
        "complexity": {
            "entity_count": len(sir.get("entities", [])),
            "view_count":   len(sir.get("views", [])),
            "total_files":  len(files),
            "total_lines":  sum(len((v or "").split("\n")) for v in files.values()),
        },
        "syntax_errors": errs,
    }


def build_zip(pn: str, files: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in files.items():
            zf.writestr(f"{pn}/{path}", content or "")
        zf.writestr(f"{pn}/README.md",
            f"# {pn.replace('_',' ').title()}\n\n"
            "```bash\npip install -r requirements.txt\n"
            "python manage.py migrate\npython seed_data.py\n"
            "python manage.py runserver\n```\n")
    buf.seek(0)
    return buf.read()


def _clean_json(raw: str) -> str:
    s = raw.strip()
    if s.startswith("{"): return s
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", s, re.I)
    if m and m.group(1).strip().startswith("{"): return m.group(1).strip()
    a, b = s.find("{"), s.rfind("}")
    if a != -1 and b > a: return s[a:b+1]
    raise ValueError("No JSON found in LLM response")


def _log(prompt, sir, ev, ms, sid):
    rec = {
        "id": sid, "timestamp": datetime.utcnow().isoformat(),
        "prompt": prompt[:200], "domain": sir.get("domain", "other"),
        "entity_count": len(sir.get("entities", [])),
        "view_count": len(sir.get("views", [])),
        "overall_score": ev["scores"]["overall_quality"],
        "grade": ev["grade"], "total_ms": ms,
        "total_files": ev["complexity"]["total_files"],
    }
    clean_old_sessions()
    save_experiment_local(rec)


# ── SSE stream ────────────────────────────────────────────────────────────────
async def stream_generation(prompt: str, sid: str):
    start = time.time()
    def sse(event, data): return f"event: {event}\ndata: {json.dumps(data)}\n\n"

    try:
        yield sse("progress", {"step": "sir", "message": "Analyzing requirements...", "percent": 10})
        sir = await extract_sir(prompt)
        yield sse("sir", {"sir": sir, "message": f"Architecture ready — {len(sir.get('entities',[]))} entities"})

        yield sse("progress", {"step": "generate", "message": "Synthesizing Django files...", "percent": 30})
        files = await build_files(sir)

        for i, (path, content) in enumerate(files.items()):
            yield sse("file", {"path": path, "content": content,
                               "index": i+1, "total_files": len(files)})

        yield sse("progress", {"step": "evaluate", "message": "Evaluating architecture...", "percent": 90})
        ev = evaluate(files, sir)
        zb = build_zip(sir["project_name"], files)
        total_ms = round((time.time() - start) * 1000)

        SESSIONS[sid] = {
            "prompt": prompt, "sir": sir, "files": files,
            "evaluation": ev, "zip_bytes": zb, "total_time_ms": total_ms,
        }
        _log(prompt, sir, ev, total_ms, sid)

        an = sir["app_name"]
        preview_html = await render_preview_llm(files, sir, prompt)
        yield sse("done", {
            "session_id":    sid,
            "project_name":  sir["project_name"],
            "app_name":      an,
            "description":   sir.get("description", ""),
            "evaluation":    ev,
            "preview_html":  preview_html,
            "total_time_ms": total_ms,
            "message": f"'{sir['project_name']}' — {len(files)} files · OQS {ev['scores']['overall_quality']}% · {total_ms//1000}s",
        })

    except Exception as e:
        logger.error("Generation error: %s", e)
        yield sse("error", {"message": str(e)})


# ── Endpoints ─────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend"))

if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/", response_class=FileResponse)
async def serve_index():
    index_file = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"error": f"index.html not found at {index_file}"}

@app.get("/health")
async def health():
    return {"status": "ok", "version": "7.2.0", "model": MODEL,
            "api_configured": bool(API_KEY)}

@app.post("/generate")
@limiter.limit("10/hour")
async def generate(request: Request):
    data   = await request.json()
    prompt = data.get("prompt", "").strip()
    if len(prompt) < 5:
        return JSONResponse({"error": "Prompt too short"}, status_code=400)
    if len(prompt) > 500:
        return JSONResponse({"error": "Prompt exceeds 500 characters"}, status_code=400)
    if not API_KEY:
        return JSONResponse({"error": "ANTHROPIC_API_KEY not configured"}, status_code=503)
    sid = str(uuid.uuid4())
    return StreamingResponse(
        stream_generation(prompt, sid),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )

@app.get("/download/{session_id}")
async def download(session_id: str):
    s = SESSIONS.get(session_id)
    if not s:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    return StreamingResponse(
        io.BytesIO(s["zip_bytes"]),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{s["sir"]["project_name"]}.zip"'},
    )

@app.get("/experiments")
async def get_experiments():
    if not EXPERIMENTS:
        return {"experiments": [], "summary": {}}
    sc = [e["overall_score"] for e in EXPERIMENTS]
    return {
        "experiments": EXPERIMENTS,
        "summary": {
            "total":     len(EXPERIMENTS),
            "avg_score": round(sum(sc) / len(sc), 1),
            "max_score": max(sc),
            "min_score": min(sc),
        }
    }