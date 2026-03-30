"""
main.py — CLI entry point for the Research & Report Agent.

Usage:
    python main.py "Impact of LLMs on software engineering"
    python main.py "Quantum computing 2025" --keep-memory
    python main.py --help
"""

import sys
import argparse
from chains.report_chain import run_research_pipeline


def parse_args():
    parser = argparse.ArgumentParser(
        description="Research & Report Agent — LangChain + Groq + ChromaDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py "Impact of large language models on software engineering"
  python main.py "Microservices best practices 2025" --keep-memory
  python main.py "Quantum computing current state" --session my-quantum-run
        """,
    )
    parser.add_argument(
        "topic",
        nargs="?",
        default="Agentic AI trends 2025",
        help="Research topic (wrap in quotes if multi-word)",
    )
    parser.add_argument(
        "--keep-memory",
        action="store_true",
        help="Keep the ChromaDB collection after the run (useful for debugging)",
    )
    parser.add_argument(
        "--session",
        default=None,
        help="Custom session ID for memory isolation (auto-generated if not set)",
    )
    parser.add_argument(
        "--preview-chars",
        type=int,
        default=1500,
        help="How many characters of the report to preview in terminal (default: 1500)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print("\n" + "═" * 64)
    print("  🤖  Research & Report Agent")
    print("═" * 64)
    print(f"  Topic   : {args.topic}")
    print(f"  Session : {args.session or '(auto)'}")
    print("═" * 64 + "\n")

    result = run_research_pipeline(
        topic=args.topic,
        session_id=args.session,
        keep_memory=args.keep_memory,
    )

    # ── Summary ───────────────────────────────────────────────────────────────
    t = result["timings"]
    print("\n" + "═" * 64)
    print("  ✅  Pipeline Complete")
    print("═" * 64)
    print(f"  Searches run : {result['searches']}")
    print(f"  Research     : {t.get('research', '?')}s")
    print(f"  Analysis     : {t.get('analysis', '?')}s")
    print(f"  Writing      : {t.get('writing', '?')}s")
    print(f"  Total        : {t.get('total', '?')}s")
    print(f"  Saved to     : {result['saved_to']}")
    print("═" * 64)

    preview = result["report"][: args.preview_chars]
    print(f"\n{'─' * 64}\n📄  REPORT PREVIEW\n{'─' * 64}\n")
    print(preview)
    if len(result["report"]) > args.preview_chars:
        print(f"\n  … [{len(result['report']) - args.preview_chars} more chars in file]")
    print()


if __name__ == "__main__":
    main()
