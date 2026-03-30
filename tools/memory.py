"""
tools/memory.py — ChromaDB-backed vector memory with session isolation.

Key improvement over original:
  • Each pipeline run gets its own ChromaDB collection (keyed by session_id).
    This means concurrent runs don't pollute each other's memory.
  • Memory is cleared at the start of each new session (fresh research, not stale).
  • Factory function returns scoped save/recall tools bound to that session.
"""

import uuid
import chromadb
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.tools import tool
from config import CHROMA_DB_PATH, EMBEDDING_MODEL, MEMORY_TOP_K
from utils.logger import get_logger

log = get_logger("tool.memory")

# ── Shared embedding model (loaded once, reused across sessions) ──────────────
_embeddings = None


def _get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embeddings

_chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)


def create_session_memory(session_id: str | None = None):
    """
    Returns (save_tool, recall_tool) bound to an isolated ChromaDB collection.
    Call once per pipeline run and pass the tools to agents.

    Args:
        session_id: optional string; auto-generated UUID if not provided.

    Returns:
        session_id, save_research tool, recall_research tool
    """
    sid = session_id or uuid.uuid4().hex[:12]
    collection_name = f"research_{sid}"

    log.info(f"Creating memory session: {collection_name}")

    vectorstore = Chroma(
        client=_chroma_client,
        collection_name=collection_name,
        embedding_function=_get_embeddings(),
    )

    # ── Tools ─────────────────────────────────────────────────────────────────

    @tool
    def save_research(text: str) -> str:
        """
        Save an important research finding, fact, statistic, or quote to memory.
        Always call this after each web_search or scrape_webpage that yields
        useful information. Include the source URL in the text you save.
        Input: the text snippet to remember (include source URL).
        """
        try:
            vectorstore.add_texts([text])
            log.debug(f"[{sid}] Saved to memory: {text[:80]}…")
            return "Saved to memory."
        except Exception as e:
            log.error(f"Memory save failed: {e}")
            return f"Memory save failed: {e}"

    @tool
    def recall_research(query: str) -> str:
        """
        Retrieve the most relevant stored research findings from memory.
        Always call this at the start of analysis and writing phases to
        check what the researcher already found.
        Input: a topic, question, or keyword to search memory for.
        Returns: up to 5 relevant stored text chunks.
        """
        try:
            docs = vectorstore.similarity_search(query, k=MEMORY_TOP_K)
            if not docs:
                return "Nothing relevant found in memory yet."
            chunks = [f"[Memory {i+1}]\n{d.page_content}" for i, d in enumerate(docs)]
            return "\n\n---\n\n".join(chunks)
        except Exception as e:
            log.error(f"Memory recall failed: {e}")
            return f"Memory recall failed: {e}"

    def clear_session():
        """Call after pipeline completes to free up ChromaDB resources."""
        try:
            _chroma_client.delete_collection(collection_name)
            log.info(f"Memory session {sid} cleared.")
        except Exception:
            pass

    return sid, save_research, recall_research, clear_session
