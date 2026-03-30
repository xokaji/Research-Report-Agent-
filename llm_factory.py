"""
llm_factory.py — Builds ChatGroq instances with automatic retry on rate limits.

Usage:
    from llm_factory import build_llm
    llm = build_llm(model="llama-3.3-70b-versatile", temperature=0.3)
"""

from langchain_groq import ChatGroq
from config import GROQ_API_KEY, RETRY_ATTEMPTS, RETRY_BASE_SLEEP
from utils.logger import get_logger

log = get_logger("llm_factory")


def build_llm(
    model: str,
    temperature: float = 0.3,
    max_tokens: int = 4096,
) -> ChatGroq:
    """
    Returns a ChatGroq instance.
    Wraps the invoke method with exponential-backoff retry for 429s.
    """
    if not GROQ_API_KEY:
        raise EnvironmentError(
            "GROQ_API_KEY is not set. Add it to your .env file.\n"
            "Get a free key at https://console.groq.com"
        )

    llm = ChatGroq(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        groq_api_key=GROQ_API_KEY,
    )

    # Use LangChain's runnable retry wrapper (safe with pydantic models).
    return llm.with_retry(
        stop_after_attempt=RETRY_ATTEMPTS,
        wait_exponential_jitter=True,
        exponential_jitter_params={"initial": RETRY_BASE_SLEEP},
    )
