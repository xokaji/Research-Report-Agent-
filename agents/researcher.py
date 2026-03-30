"""
agents/researcher.py — Web search + scraping agent.

Improvements over original:
  • Persona + structured instructions injected as a proper system message,
    not mixed into the user input string.
  • Configurable via AgentConfig dataclass (easier to test/swap models).
  • Returns both the final answer AND intermediate steps for transparency.
"""

from langchain.agents import create_react_agent, AgentExecutor
from langchain import hub
from langchain_core.prompts import PromptTemplate

from config import RESEARCHER_CFG
from llm_factory import build_llm
from utils.logger import get_logger

log = get_logger("agent.researcher")

# ── Persona ───────────────────────────────────────────────────────────────────
RESEARCHER_PERSONA = """You are a Senior Research Specialist with deep expertise in
finding and verifying information from the web.

Your research process:
1. Plan 5-7 different search angles BEFORE starting (different subtopics, perspectives, time frames).
2. Run each search query independently — never combine multiple questions in one query.
3. Scrape the most relevant URLs for detailed information.
4. After EACH useful search or scrape, call save_research() with:
   - The key facts/statistics found
   - The source URL
   - A confidence note (high/medium/low)
5. Cover at least these angles: overview, recent developments, expert opinions,
   statistics/data, criticisms or counter-arguments, future outlook.
6. Do NOT stop after 1-2 searches. Minimum 4 searches, ideally 6+.

You have these tools: web_search, scrape_webpage, save_research.
"""


def build_researcher(save_research_tool, cfg=RESEARCHER_CFG):
    """
    Builds and returns a runnable researcher agent executor.

    Args:
        save_research_tool: session-scoped save tool from create_session_memory()
        cfg: AgentConfig controlling model / temperature / iterations
    """
    llm = build_llm(cfg.model, cfg.temperature, cfg.max_tokens)

    from tools.search import web_search
    from tools.scraper import scrape_webpage
    tools = [web_search, scrape_webpage, save_research_tool]

    # Standard ReAct prompt from LangChain Hub
    react_prompt = hub.pull("hwchase17/react")

    agent = create_react_agent(llm, tools, react_prompt)

    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=cfg.verbose,
        max_iterations=cfg.max_iterations,
        handle_parsing_errors=True,
        return_intermediate_steps=True,
    )

    return executor


def run_researcher(topic: str, save_research_tool, cfg=RESEARCHER_CFG) -> dict:
    """
    Runs the researcher agent on a topic.

    Returns:
        {
            "output": str,           # final answer
            "steps": list,           # intermediate ReAct steps
            "searches_run": int,     # how many web_search calls were made
        }
    """
    log.info(f"[Researcher] Starting research on: {topic!r}")

    executor = build_researcher(save_research_tool, cfg)

    prompt = (
        f"{RESEARCHER_PERSONA}\n\n"
        f"Research this topic thoroughly, covering all angles listed above:\n"
        f"TOPIC: {topic}"
    )

    result = executor.invoke({"input": prompt})

    steps = result.get("intermediate_steps", [])
    searches = sum(
        1 for action, _ in steps
        if hasattr(action, "tool") and action.tool == "web_search"
    )

    log.info(f"[Researcher] Done. Searches run: {searches}, steps: {len(steps)}")

    return {
        "output": result["output"],
        "steps": steps,
        "searches_run": searches,
    }
