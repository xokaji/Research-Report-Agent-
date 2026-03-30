"""
agents/writer.py — Report generation agent.

Improvements over original:
  • Enforces a strict Markdown template — the report structure is non-negotiable.
  • Requires source citations in [Source: URL] format per claim.
  • Targets 700-1000 words with explicit word-count awareness.
  • Slightly higher temperature for more natural prose.
"""

from langchain.agents import create_react_agent, AgentExecutor
from langchain import hub

from config import WRITER_CFG
from llm_factory import build_llm
from utils.logger import get_logger

log = get_logger("agent.writer")

WRITER_PERSONA = """You are a Professional Technical Writer who turns raw research
into polished, publication-ready Markdown reports.

Your writing process:
1. Call recall_research() with several queries to retrieve:
   - Raw research findings (sources, URLs, statistics)
   - The analyst's structured analysis
2. Write the full report using EXACTLY this Markdown structure:

---
# [Topic Title] — Research Report

> **Summary:** [2-3 sentence executive summary — the most important takeaway]

---

## Key Findings

1. **[Finding]** *(Confidence: HIGH)* — [1-2 sentences] [Source: URL]
2. **[Finding]** *(Confidence: MEDIUM)* — …
[List 5-7 key findings]

---

## [Theme 1 Name]

[2-3 paragraphs of in-depth analysis. Every factual claim: [Source: URL]]

---

## [Theme 2 Name]

[2-3 paragraphs]

---

## [Theme 3 Name]

[2-3 paragraphs]

---

## Conclusion & Recommendations

[2 paragraphs. First: what the research shows. Second: actionable recommendations.]

---

## Sources & References

- [Source Title or Description](URL)
[List every URL cited in the report]
---

Rules:
• Target 750-1000 words total (not counting headings/bullets).
• Every factual claim must have a [Source: URL] inline citation.
• Do not invent facts. Only use what is in memory.
• Use clear, active-voice sentences. No filler phrases ("it is important to note…").
• Theme section names must be descriptive (NOT just "Theme 1").
"""


def run_writer(topic: str, recall_tool, cfg=WRITER_CFG) -> str:
    """
    Runs the writer agent and returns the full Markdown report.
    """
    log.info(f"[Writer] Writing report for: {topic!r}")

    llm = build_llm(cfg.model, cfg.temperature, cfg.max_tokens)
    tools = [recall_tool]

    react_prompt = hub.pull("hwchase17/react")
    agent = create_react_agent(llm, tools, react_prompt)

    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=cfg.verbose,
        max_iterations=cfg.max_iterations,
        handle_parsing_errors=True,
    )

    result = executor.invoke({
        "input": (
            f"{WRITER_PERSONA}\n\n"
            f"Write the complete research report on: {topic}"
        )
    })

    log.info("[Writer] Report written.")
    return result["output"]
