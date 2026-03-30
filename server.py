"""
server.py — FastAPI server exposing the pipeline as a REST + SSE API.

Endpoints:
    POST /research          — blocking, returns full result JSON
    POST /research/stream   — SSE stream of progress events + final report
    GET  /health            — health check

Run:
    uvicorn server:app --reload --port 8000

Next.js fetch:
    const res = await fetch("http://localhost:8000/research", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: "Agentic AI 2025" }),
    });
    const data = await res.json();
    console.log(data.report);
"""

import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from chains.report_chain import run_research_pipeline
from utils.logger import get_logger

log = get_logger("server")

app = FastAPI(
    title="Research & Report Agent API",
    description="Multi-agent research pipeline: LangChain + Groq + ChromaDB",
    version="2.0.0",
)

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"

# Allow all origins for local dev — tighten this in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if FRONTEND_DIR.exists():
    app.mount("/ui", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="ui")


# ── Request / Response models ──────────────────────────────────────────────────

class ResearchRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=300, example="Agentic AI trends 2025")
    session_id: str | None = Field(None, example="my-run-001")
    keep_memory: bool = Field(False, description="Keep ChromaDB collection after run")


class ResearchResponse(BaseModel):
    topic: str
    session_id: str
    report: str
    saved_to: str
    searches: int
    timings: dict
    generated_at: str


# ── Blocking endpoint ─────────────────────────────────────────────────────────

@app.post("/research", response_model=ResearchResponse)
async def research(req: ResearchRequest):
    """
    Run the full pipeline synchronously.
    Returns the complete report JSON when done (may take 60-180s).
    """
    log.info(f"POST /research topic={req.topic!r}")
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: run_research_pipeline(
                topic=req.topic,
                session_id=req.session_id,
                keep_memory=req.keep_memory,
            ),
        )
        return ResearchResponse(
            topic=result["topic"],
            session_id=result["session_id"],
            report=result["report"],
            saved_to=result["saved_to"],
            searches=result["searches"],
            timings=result["timings"],
            generated_at=datetime.now().isoformat(),
        )
    except Exception as e:
        log.error(f"Pipeline error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── Streaming SSE endpoint ────────────────────────────────────────────────────

def _sse_event(event: str, data: dict) -> str:
    """Format a Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.post("/research/stream")
async def research_stream(req: ResearchRequest):
    """
    Stream progress events via SSE while the pipeline runs.

    Event types:
        progress  — { phase, message }
        done      — { report, saved_to, searches, timings }
        error     — { detail }

    Next.js usage:
        const es = new EventSource("/research/stream");  // use fetch for POST
        es.addEventListener("progress", e => console.log(JSON.parse(e.data)));
        es.addEventListener("done", e => setReport(JSON.parse(e.data).report));
    """
    queue: asyncio.Queue = asyncio.Queue()

    def callback(phase: str, message: str):
        queue.put_nowait({"phase": phase, "message": message})

    async def event_generator() -> AsyncGenerator[str, None]:
        # Run pipeline in thread, feed progress via queue
        loop = asyncio.get_event_loop()

        future = loop.run_in_executor(
            None,
            lambda: run_research_pipeline(
                topic=req.topic,
                session_id=req.session_id,
                keep_memory=req.keep_memory,
                progress_callback=callback,
            ),
        )

        # Stream progress events while pipeline runs
        while not future.done():
            try:
                item = await asyncio.wait_for(queue.get(), timeout=0.5)
                yield _sse_event("progress", item)
            except asyncio.TimeoutError:
                yield ": keep-alive\n\n"   # prevent proxy timeouts

        # Drain any remaining progress events
        while not queue.empty():
            yield _sse_event("progress", queue.get_nowait())

        # Emit final result or error
        try:
            result = await future
            yield _sse_event("done", {
                "report":   result["report"],
                "saved_to": result["saved_to"],
                "searches": result["searches"],
                "timings":  result["timings"],
            })
        except Exception as e:
            log.error(f"Stream pipeline error: {e}", exc_info=True)
            yield _sse_event("error", {"detail": str(e)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/research/stream")
def research_stream_help():
    """Helpful response when endpoint is opened directly in browser."""
    return {
        "message": "Use POST /research/stream with JSON body to start streaming research.",
        "example": {
            "topic": "Agentic AI trends 2026",
            "session_id": "optional-session-id",
            "keep_memory": False,
        },
    }


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0", "timestamp": datetime.now().isoformat()}


@app.get("/")
def root():
    return {
        "message": "Research & Report Agent API",
        "docs": "/docs",
        "health": "/health",
    }
