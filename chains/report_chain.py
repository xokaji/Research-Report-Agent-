"""
chains/report_chain.py — Orchestrates the three-phase research pipeline.

Pipeline: Research → Analyse → Write → Save

Improvements over original:
  • Session-isolated memory — no cross-run contamination.
  • Timing per phase so you know where time is spent.
  • Rich return dict with metadata for the API / CLI to use.
  • Optional progress_callback for streaming UIs (SSE, WebSocket).
  • Memory cleanup after pipeline completes.
"""

import os
import time
from datetime import datetime
from typing import Callable

from tools.memory import create_session_memory
from agents.researcher import run_researcher
from agents.analyst import run_analyst
from agents.writer import run_writer
from config import OUTPUT_DIR
from utils.logger import get_logger

log = get_logger("pipeline")


def run_research_pipeline(
    topic: str,
    session_id: str | None = None,
    keep_memory: bool = False,
    progress_callback: Callable[[str, str], None] | None = None,
) -> dict:
    """
    Full pipeline: Research → Analyse → Write Report

    Args:
        topic:             The research topic (free-form string).
        session_id:        Optional custom session ID for memory isolation.
        keep_memory:       If True, ChromaDB collection is NOT deleted after run.
        progress_callback: Optional fn(phase: str, message: str) for streaming UIs.

    Returns:
        {
            "topic":      str,
            "session_id": str,
            "research":   str,          # researcher output
            "analysis":   str,          # analyst output
            "report":     str,          # final Markdown report
            "saved_to":   str,          # file path
            "timings":    dict,         # per-phase seconds
            "searches":   int,          # number of web searches run
        }
    """

    def _progress(phase: str, msg: str):
        log.info(f"[{phase}] {msg}")
        if progress_callback:
            progress_callback(phase, msg)

    # ── Setup ─────────────────────────────────────────────────────────────────
    pipeline_start = time.time()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    _progress("PIPELINE", f"Starting research on: {topic!r}")

    sid, save_tool, recall_tool, clear_session = create_session_memory(session_id)
    _progress("PIPELINE", f"Memory session: {sid}")

    timings = {}
    searches_run = 0

    try:
        # ── Phase 1: Research ──────────────────────────────────────────────────
        _progress("RESEARCH", "🔍 Searching the web and gathering facts…")
        t0 = time.time()

        research_result = run_researcher(topic, save_tool)
        research_output = research_result["output"]
        searches_run = research_result["searches_run"]

        timings["research"] = round(time.time() - t0, 1)
        _progress("RESEARCH", f"✅ Done in {timings['research']}s — {searches_run} searches run")

        # Pause between phases to avoid Groq rate limits
        time.sleep(2)

        # ── Phase 2: Analyse ───────────────────────────────────────────────────
        _progress("ANALYSIS", "🧠 Synthesising findings…")
        t0 = time.time()

        analysis_output = run_analyst(topic, recall_tool, save_tool)

        timings["analysis"] = round(time.time() - t0, 1)
        _progress("ANALYSIS", f"✅ Done in {timings['analysis']}s")

        time.sleep(2)

        # ── Phase 3: Write ─────────────────────────────────────────────────────
        _progress("WRITING", "✍️  Writing the report…")
        t0 = time.time()

        report = run_writer(topic, recall_tool)

        timings["writing"] = round(time.time() - t0, 1)
        _progress("WRITING", f"✅ Done in {timings['writing']}s")

        # ── Save to disk ───────────────────────────────────────────────────────
        safe_topic = topic[:50].replace(" ", "_").replace("/", "-")
        timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename   = os.path.join(OUTPUT_DIR, f"{safe_topic}_{timestamp}.md")

        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# Research Report\n\n")
            f.write(f"**Topic:** {topic}  \n")
            f.write(f"**Session:** {sid}  \n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n\n")
            f.write("---\n\n")
            f.write(report)

        timings["total"] = round(time.time() - pipeline_start, 1)
        _progress("PIPELINE", f"🎉 Report saved → {filename} (total: {timings['total']}s)")

        return {
            "topic":      topic,
            "session_id": sid,
            "research":   research_output,
            "analysis":   analysis_output,
            "report":     report,
            "saved_to":   filename,
            "timings":    timings,
            "searches":   searches_run,
        }

    finally:
        if not keep_memory:
            clear_session()
