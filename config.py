"""
config.py — Central configuration for Research & Report Agent
All tunable settings live here. Never scatter magic values in agent files.
"""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


# ── Model IDs ─────────────────────────────────────────────────────────────────
PRIMARY_MODEL   = "llama-3.3-70b-versatile"   # reasoning, planning, writing
FAST_MODEL      = "llama-3.1-8b-instant"       # summarization, formatting

# ── API Keys ──────────────────────────────────────────────────────────────────
GROQ_API_KEY    = os.getenv("GROQ_API_KEY", "")
TAVILY_API_KEY  = os.getenv("TAVILY_API_KEY", "")

# ── Agent Iteration Limits ────────────────────────────────────────────────────
RESEARCHER_MAX_ITER = 12   # more searches = better coverage
ANALYST_MAX_ITER    = 6
WRITER_MAX_ITER     = 5

# ── Memory ────────────────────────────────────────────────────────────────────
CHROMA_DB_PATH      = "./chroma_db"
EMBEDDING_MODEL     = "all-MiniLM-L6-v2"      # ~80 MB, cached after first run
MEMORY_TOP_K        = 5                        # docs returned per recall query

# ── Report Output ─────────────────────────────────────────────────────────────
OUTPUT_DIR          = "./output"
REPORT_WORD_TARGET  = (700, 1000)

# ── Retry / Rate-limit ────────────────────────────────────────────────────────
RETRY_ATTEMPTS      = 3
RETRY_BASE_SLEEP    = 2.0   # seconds; doubles on each retry

# ── LLM temperature presets ──────────────────────────────────────────────────
TEMP_FACTUAL  = 0.2   # research / analysis — deterministic
TEMP_CREATIVE = 0.5   # writer — slightly more expressive


@dataclass
class AgentConfig:
    """
    Passed into each agent so they're fully self-contained and testable.
    """
    model: str          = PRIMARY_MODEL
    temperature: float  = TEMP_FACTUAL
    max_tokens: int     = 4096
    max_iterations: int = RESEARCHER_MAX_ITER
    verbose: bool       = True


# Convenience singletons used by agents/
RESEARCHER_CFG = AgentConfig(
    model=PRIMARY_MODEL,
    temperature=TEMP_FACTUAL,
    max_tokens=4096,
    max_iterations=RESEARCHER_MAX_ITER,
)

ANALYST_CFG = AgentConfig(
    model=PRIMARY_MODEL,
    temperature=TEMP_FACTUAL,
    max_tokens=2048,
    max_iterations=ANALYST_MAX_ITER,
)

WRITER_CFG = AgentConfig(
    model=PRIMARY_MODEL,
    temperature=TEMP_CREATIVE,
    max_tokens=4096,
    max_iterations=WRITER_MAX_ITER,
)
