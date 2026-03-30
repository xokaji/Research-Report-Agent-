"""
tools/scraper.py — Fetch and extract clean text from a URL.

Improvements over original:
  • Smarter content extraction: prefers <article> / <main> over full body.
  • Returns metadata (title, url) alongside content.
  • Hard timeout + user-agent rotation.
"""

import random
import re
from langchain.tools import tool
import requests
from bs4 import BeautifulSoup
from utils.logger import get_logger

log = get_logger("tool.scraper")

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
]

_NOISE_TAGS = ["script", "style", "nav", "footer", "header", "aside",
               "form", "noscript", "iframe", "ads", "advertisement"]

MAX_CHARS = 4000  # ~1000 tokens — enough detail without blowing context


@tool
def scrape_webpage(url: str) -> str:
    """
    Fetch and extract readable text from a specific web page URL.
    Use when you have a URL returned from web_search and need full details.
    Input: a full URL starting with https://
    Returns: page title + clean body text (truncated to ~4000 chars).
    """
    log.debug(f"scrape_webpage: {url}")
    if not url.startswith("http"):
        return f"Invalid URL: {url!r}. Must start with https://"

    try:
        headers = {"User-Agent": random.choice(_USER_AGENTS)}
        resp = requests.get(url, headers=headers, timeout=12)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        title = soup.title.string.strip() if soup.title else "No title"

        # Remove noise
        for tag in soup(_NOISE_TAGS):
            tag.decompose()

        # Prefer semantic content containers
        body = (
            soup.find("article")
            or soup.find("main")
            or soup.find(id=re.compile(r"content|article|post", re.I))
            or soup.body
        )

        text = body.get_text(separator="\n", strip=True) if body else ""

        # Collapse excessive blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)

        if len(text) > MAX_CHARS:
            text = text[:MAX_CHARS] + "\n\n[… content truncated …]"

        return f"SOURCE: {url}\nTITLE: {title}\n\n{text}"

    except requests.exceptions.Timeout:
        return f"Timeout fetching {url}. Try a different source."
    except Exception as e:
        log.error(f"Scrape failed for {url}: {e}")
        return f"Could not scrape {url}: {e}"
