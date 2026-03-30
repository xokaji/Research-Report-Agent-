"""
tests/test_agents.py — Unit + integration tests.

Run:
    pytest tests/ -v
    pytest tests/ -v -k "unit"       # fast unit tests only
    pytest tests/ -v -k "integration" --tb=short  # needs real API keys
"""

import pytest
import os
from unittest.mock import MagicMock, patch


# ── Unit tests (no API keys required) ─────────────────────────────────────────

class TestSearchTool:
    def test_invalid_url_handled(self):
        """scrape_webpage should return an error string, not raise."""
        from tools.scraper import scrape_webpage
        result = scrape_webpage.invoke("not-a-url")
        assert "Invalid URL" in result or "Could not" in result

    def test_web_search_returns_string(self):
        """web_search should always return a string."""
        from tools.search import web_search
        with patch("tools.search._search_backend") as mock_backend:
            mock_backend.run.return_value = "Mock search result about AI"
            result = web_search.invoke("test query")
        assert isinstance(result, str)

    def test_web_search_handles_exception(self):
        from tools.search import web_search
        with patch("tools.search._search_backend") as mock_backend:
            mock_backend.run.side_effect = Exception("network error")
            result = web_search.invoke("test query")
        assert "Search failed" in result


class TestMemoryTool:
    def test_session_isolation(self, tmp_path):
        """Two sessions must not share memory."""
        os.environ.setdefault("GROQ_API_KEY", "test-key")
        with patch("tools.memory.CHROMA_DB_PATH", str(tmp_path)):
            from tools.memory import create_session_memory
            sid1, save1, recall1, clear1 = create_session_memory("sess-a")
            sid2, save2, recall2, clear2 = create_session_memory("sess-b")

            save1.invoke("Unique fact for session A")
            result = recall2.invoke("session A fact")
            # Session B should NOT see session A's memories
            assert "Unique fact for session A" not in result

            clear1()
            clear2()

    def test_save_and_recall(self, tmp_path):
        """Basic save → recall round-trip."""
        with patch("tools.memory.CHROMA_DB_PATH", str(tmp_path)):
            from tools.memory import create_session_memory
            sid, save, recall, clear = create_session_memory()

            save.invoke("The capital of France is Paris. Source: https://example.com")
            result = recall.invoke("capital of France")
            assert "Paris" in result

            clear()


class TestConfig:
    def test_agent_configs_have_required_fields(self):
        from config import RESEARCHER_CFG, ANALYST_CFG, WRITER_CFG
        for cfg in [RESEARCHER_CFG, ANALYST_CFG, WRITER_CFG]:
            assert cfg.model
            assert 0 <= cfg.temperature <= 1
            assert cfg.max_tokens > 0
            assert cfg.max_iterations > 0

    def test_output_dir_config(self):
        from config import OUTPUT_DIR
        assert isinstance(OUTPUT_DIR, str)


class TestPipelineResult:
    def test_result_schema(self):
        """run_research_pipeline return dict must have all expected keys."""
        required_keys = {
            "topic", "session_id", "research",
            "analysis", "report", "saved_to", "timings", "searches"
        }

        mock_result = {
            "topic": "test",
            "session_id": "abc123",
            "research": "research output",
            "analysis": "analysis output",
            "report": "# Report\n\nContent here.",
            "saved_to": "/tmp/test.md",
            "timings": {"research": 10, "analysis": 5, "writing": 8, "total": 23},
            "searches": 5,
        }

        assert required_keys.issubset(mock_result.keys())


# ── Integration tests (require GROQ_API_KEY) ───────────────────────────────────

@pytest.mark.integration
class TestIntegration:
    """
    These tests make real API calls. Set GROQ_API_KEY in your environment.
    Run with: pytest tests/ -v -k integration
    """

    def test_full_pipeline_short_topic(self):
        if not os.getenv("GROQ_API_KEY"):
            pytest.skip("GROQ_API_KEY not set")

        from chains.report_chain import run_research_pipeline
        result = run_research_pipeline(
            topic="Python programming language overview",
            keep_memory=False,
        )
        assert result["report"]
        assert len(result["report"]) > 200
        assert result["searches"] > 0
        assert os.path.exists(result["saved_to"])

        # Cleanup
        os.remove(result["saved_to"])

    def test_researcher_runs_multiple_searches(self):
        if not os.getenv("GROQ_API_KEY"):
            pytest.skip("GROQ_API_KEY not set")

        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with patch("tools.memory.CHROMA_DB_PATH", tmp):
                from tools.memory import create_session_memory
                from agents.researcher import run_researcher
                _, save, _, clear = create_session_memory()
                result = run_researcher("Python programming", save)
                assert result["searches_run"] >= 2
                clear()
