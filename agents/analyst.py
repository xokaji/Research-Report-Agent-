"""
agents/analyst.py — Synthesis and insight extraction agent.

Improvements over original:
  • Structured output format enforced in the prompt (JSON-like sections).
  • Confidence rating scheme is explicit and consistent.
  • Contradiction detection is an explicit step.
  • Uses fast model since it only reads memory (no web calls needed).
"""

from langchain.agents import create_react_agent, AgentExecutor
from langchain import hub

from config import ANALYST_CFG
from llm_factory import build_llm
from utils.logger import get_logger

log = get_logger("agent.analyst")

ANALYST_PERSONA = """You are a Senior Research Analyst specialising in synthesising
multi-source research into clear, actionable intelligence.

Your analysis process:
1. Call recall_research() at least 3 times with DIFFERENT queries to retrieve
   all stored findings from multiple angles.
2. Save any new synthesis insight using save_research() so the writer can access it.
3. Produce a structured analysis with EXACTLY these sections:

---
## ANALYST REPORT

### Key Insights (rank by importance, include confidence: HIGH/MEDIUM/LOW)
1. [insight] — Confidence: HIGH — Sources: [urls]
...

### Themes Identified
• [theme name]: [short description]
...

### Contradictions & Gaps
• [describe any conflicting data or missing information]

### Data & Statistics Found
• [list every concrete number, percentage, or metric found]

### Confidence Summary
Overall research confidence: [HIGH/MEDIUM/LOW]
Reasoning: [1-2 sentences]
---

Be analytical, not descriptive. Every claim must reference what was found in memory.
"""


def run_analyst(topic: str, recall_tool, save_tool, cfg=ANALYST_CFG) -> str:
    """
    Runs the analyst agent.

    Args:
        topic: the research topic
        recall_tool: session-scoped recall tool
        save_tool: session-scoped save tool (to persist synthesis for the writer)
        cfg: AgentConfig

    Returns:
        str — the structured analyst report
    """
    log.info(f"[Analyst] Analysing findings for: {topic!r}")

    llm = build_llm(cfg.model, cfg.temperature, cfg.max_tokens)
    tools = [recall_tool, save_tool]

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
            f"{ANALYST_PERSONA}\n\n"
            f"Analyse ALL stored research findings on this topic: {topic}"
        )
    })

    log.info("[Analyst] Analysis complete.")
    return result["output"]
