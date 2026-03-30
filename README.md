# 🤖 Research & Report Agent v2

A production-grade multi-agent research pipeline built with **LangChain**, **Groq (llama-3.3-70b)**, and **ChromaDB**. Give it a topic — it searches the web, synthesises findings, and writes a structured Markdown report.

---

## What's New in v2 (vs the original claude.md)

| Feature | Original | v2 |
|---|---|---|
| Memory isolation | Shared global collection | Per-session ChromaDB collection |
| Rate limit handling | None | Exponential backoff retry |
| Search coverage | 1–3 searches | Minimum 4–6 searches enforced |
| LLM config | Inline in each file | Centralised `AgentConfig` dataclass |
| Logging | `print()` everywhere | Structured logger → stdout + file |
| Report citations | `[brackets]` guidance only | `[Source: URL]` enforced per claim |
| Progress streaming | None | SSE endpoint for real-time frontend |
| Session tracking | None | `session_id` in every run + report |
| Tests | None | Unit + integration test suite |

---

## Architecture

```
Topic
  │
  ▼
┌─────────────────────────────────────────────────────┐
│  chains/report_chain.py  (Orchestrator)             │
│                                                     │
│  ┌─────────────┐   ┌─────────────┐   ┌──────────┐  │
│  │  Researcher │──▶│   Analyst   │──▶│  Writer  │  │
│  │             │   │             │   │          │  │
│  │ web_search  │   │ recall_res  │   │ recall   │  │
│  │ scrape_page │   │ save_res    │   │          │  │
│  │ save_res    │   │             │   │          │  │
│  └─────────────┘   └─────────────┘   └──────────┘  │
│         │                 │                │        │
│         └────────── ChromaDB ──────────────┘        │
│                  (session-isolated)                 │
└─────────────────────────────────────────────────────┘
  │
  ▼
output/report_YYYYMMDD_HHMMSS.md
```

Each agent uses the **ReAct loop**: `Thought → Action → Observation → Thought → … → Final Answer`

### Agents

| Agent | Model | Role | Tools |
|---|---|---|---|
| Researcher | llama-3.3-70b | Web search + scraping | `web_search`, `scrape_webpage`, `save_research` |
| Analyst | llama-3.3-70b | Synthesis + insight extraction | `recall_research`, `save_research` |
| Writer | llama-3.3-70b | Report generation | `recall_research` |

### Tools

| Tool | File | What it does |
|---|---|---|
| `web_search` | `tools/search.py` | Tavily (primary) or DuckDuckGo (fallback) |
| `scrape_webpage` | `tools/scraper.py` | Fetches + cleans page text, prefers `<article>`/`<main>` |
| `save_research` | `tools/memory.py` | Adds text to session ChromaDB collection |
| `recall_research` | `tools/memory.py` | Similarity search over session memory |

---

## Quick Start

### 1. Clone and install

```bash
git clone <your-repo>
cd research_agent

python -m venv venv
source venv/bin/activate       # macOS/Linux

pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If activation is blocked by PowerShell policy, use the interpreter directly:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Set up keys

```bash
cp .env.example .env
# Edit .env — add your GROQ_API_KEY (required)
# TAVILY_API_KEY is optional but recommended
```

Get keys:
- **Groq** (required, free): https://console.groq.com
- **Tavily** (optional, free tier): https://tavily.com
- **LangSmith** (optional, free tracing): https://smith.langchain.com

### 3. Run

```bash
# CLI — basic
python main.py "Impact of large language models on software engineering"

# CLI — custom options
python main.py "Microservices best practices 2025" --keep-memory --session my-run-01

# API server
uvicorn server:app --reload --port 8000
# Docs at http://localhost:8000/docs
```

Windows (PowerShell) recommended commands:

```powershell
# Option A: activate first
.\venv\Scripts\Activate.ps1
python main.py "Impact of large language models on software engineering"

# Option B: no activation (always works)
.\venv\Scripts\python.exe main.py "Impact of large language models on software engineering"

# API server
.\venv\Scripts\python.exe -m uvicorn server:app --reload --port 8000
```

Tip: if you see package errors while running `python main.py`, your terminal is likely using system Python instead of the venv. Use Option A or Option B above.

### 3.1 Windows quick run (copy/paste)

Use this exact sequence in PowerShell:

```powershell
cd F:\AI\research_agent

# Install deps in venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt

# CLI run
.\venv\Scripts\python.exe main.py "Agentic AI trends 2026"

# API run
.\venv\Scripts\python.exe -m uvicorn server:app --reload --port 8000
```

Open after API starts:
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health
- UI: http://localhost:8000/ui

### 4. Web UI (simple frontend)

Start the API server, then open the UI in your browser:

```powershell
.\venv\Scripts\python.exe -m uvicorn server:app --reload --port 8000
```

Open:
- http://localhost:8000/ui

The UI sends requests to `POST /research/stream`, shows live progress events, and renders the final report.

UI source file: `frontend/index.html`.

---

## CLI Reference

```
python main.py [topic] [options]

Arguments:
  topic               Research topic (wrap in quotes). Default: "Agentic AI trends 2025"

Options:
  --keep-memory       Keep ChromaDB collection after run (useful for debugging)
  --session ID        Custom session ID for memory isolation
  --preview-chars N   Characters of report to preview in terminal (default: 1500)
```

Windows-safe form (avoids global Python mismatch):

```powershell
.\venv\Scripts\python.exe main.py "your topic" --keep-memory --session my-run-01
```

---

## API Reference

### `POST /research`
Blocking — returns full JSON when pipeline completes (~60–180s).

```bash
curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{"topic": "Agentic AI 2025"}'
```

Response:
```json
{
  "topic": "Agentic AI 2025",
  "session_id": "a3f9b12c",
  "report": "# Agentic AI 2025 — Research Report\n\n...",
  "saved_to": "output/Agentic_AI_2025_20250330_142301.md",
  "searches": 6,
  "timings": { "research": 45.2, "analysis": 18.1, "writing": 22.4, "total": 85.7 },
  "generated_at": "2025-03-30T14:23:01"
}
```

### `POST /research/stream`
SSE stream — sends progress events while the pipeline runs.

```javascript
// Next.js / React example
const response = await fetch("http://localhost:8000/research/stream", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ topic: "Agentic AI 2025" }),
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { value, done } = await reader.read();
  if (done) break;

  const text = decoder.decode(value);
  const lines = text.split("\n");

  for (const line of lines) {
    if (line.startsWith("data: ")) {
      const data = JSON.parse(line.slice(6));

      if (data.phase) {
        // progress event — { phase, message }
        console.log(`[${data.phase}] ${data.message}`);
      } else if (data.report) {
        // done event — full result
        setReport(data.report);
      }
    }
  }
}
```

### `GET /health`
```json
{ "status": "ok", "version": "2.0.0", "timestamp": "2025-03-30T14:00:00" }
```

---

## Report Structure

Every generated report follows this exact template:

```markdown
# [Topic] — Research Report

> **Summary:** [Executive summary — 2-3 sentences]

## Key Findings
1. **[Finding]** *(Confidence: HIGH)* — description [Source: URL]
...

## [Theme 1 — descriptive name]
In-depth analysis with inline citations [Source: URL]...

## [Theme 2]
...

## [Theme 3]
...

## Conclusion & Recommendations
What the research shows + actionable steps.

## Sources & References
- [Title](URL)
```

---

## Debugging

### Enable LangSmith tracing
Set `LANGCHAIN_TRACING_V2=true` in `.env`. Every Thought/Action/Observation is
logged at https://smith.langchain.com — the best way to debug agent behaviour.

### Verbose logs
All agents run with `verbose=True` by default. You'll see the full ReAct loop in terminal:
```
Thought: I need to find recent statistics on...
Action: web_search
Action Input: "LLM adoption enterprise 2025"
Observation: [search results...]
Thought: Good. Let me save this and search for more...
```

### Common issues

| Issue | Fix |
|---|---|
| `Could not import ddgs python package` | Install dependencies in project venv: `.\venv\Scripts\python.exe -m pip install -r requirements.txt`, then run with venv python |
| `python main.py` uses wrong interpreter | Use `.\venv\Scripts\python.exe main.py "topic"` or activate first with `.\venv\Scripts\Activate.ps1` |
| `cannot import name 'create_react_agent' from langchain.agents` | Reinstall from this repo's `requirements.txt` (LangChain is pinned to `<1.0.0` for this codebase) |
| `GROQ_API_KEY not set` | Add key to `.env` file |
| `OutputParserException` | Already handled — `handle_parsing_errors=True` |
| Agent loops forever | `max_iterations` cap kicks in and returns partial result |
| Groq 429 rate limit | Auto-retry with exponential backoff (up to 3 attempts) |
| ChromaDB slow on first run | Downloads `all-MiniLM-L6-v2` (~80MB) — cached after that |
| Search returns nothing | DuckDuckGo blocks heavy usage — add `TAVILY_API_KEY` |
| `hub.pull()` fails | Needs internet access; LangChain Hub is public |

---

## Running Tests

```bash
# Fast unit tests (no API keys needed)
pytest tests/ -v -k "not integration"

# Integration tests (needs GROQ_API_KEY)
pytest tests/ -v -k integration --tb=short
```

Windows PowerShell:

```powershell
.\venv\Scripts\python.exe -m pytest tests\ -v -k "not integration"
.\venv\Scripts\python.exe -m pytest tests\ -v -k integration --tb=short
```

---

## Extending the Project

### Add a new tool
1. Create `tools/my_tool.py` with a `@tool`-decorated function
2. Import it in `tools/__init__.py`
3. Pass it to the relevant agent's tool list in `agents/*.py`

### Add a new agent
1. Create `agents/my_agent.py` following the same pattern
2. Add a step in `chains/report_chain.py`

### HMS integration (from your hotel management system)
```python
# agents/hms_researcher.py
# Create a HotelResearchAgent that:
# - Searches competitor hotels on Booking.com / TripAdvisor
# - Scrapes pricing trends
# - Feeds findings into your HMS dashboard via your Laravel API
```

### Output formats
```python
# Add to chains/report_chain.py after report is written:
from tools.export import convert_to_pdf, convert_to_docx
pdf_path  = convert_to_pdf(report, filename)
docx_path = convert_to_docx(report, filename)
```

### Scheduled reports
```python
# scheduler.py — using APScheduler
from apscheduler.schedulers.blocking import BlockingScheduler
from chains.report_chain import run_research_pipeline

scheduler = BlockingScheduler()

@scheduler.scheduled_job("cron", day_of_week="mon", hour=8)
def weekly_report():
    run_research_pipeline("AI industry news this week")

scheduler.start()
```

---

## Project Structure

```
research_agent/
├── main.py                  # CLI entry point
├── server.py                # FastAPI REST + SSE server
├── config.py                # All settings in one place
├── llm_factory.py           # ChatGroq builder with retry logic
├── requirements.txt
├── .env.example
│
├── agents/
│   ├── researcher.py        # Web search + scraping agent
│   ├── analyst.py           # Synthesis + insight agent
│   └── writer.py            # Report generation agent
│
├── tools/
│   ├── search.py            # Tavily / DuckDuckGo search
│   ├── scraper.py           # Web page text extractor
│   └── memory.py            # Session-isolated ChromaDB tools
│
├── chains/
│   └── report_chain.py      # Pipeline orchestrator
│
├── utils/
│   └── logger.py            # Structured logging
│
├── output/                  # Generated reports saved here
├── logs/                    # Daily log files
└── tests/
    └── test_agents.py       # Unit + integration tests
```

---

Built with LangChain · Groq · ChromaDB · FastAPI
