#!/usr/bin/env python3
"""
CLI entry point for the Deep Research pipeline.

Usage:
    python main.py "Most popular AI agent frameworks in 2026"

Exit codes:
    0  success
    1  configuration error (missing API key, bad MODEL_PROVIDER, etc.)
    2  the pipeline ran but failed to produce a report
"""

import asyncio
import sys

from deep_research import run_deep_research
from deep_research.config import logger, validate_config


def main() -> int:
    if len(sys.argv) < 2:
        print('Usage: python main.py "<your research question>"')
        return 1

    query = " ".join(sys.argv[1:])

    try:
        validate_config()
    except (ValueError, EnvironmentError) as exc:
        logger.error("Configuration error: %s", exc)
        return 1

    try:
        report = asyncio.run(run_deep_research(query))
    except Exception:
        logger.exception("Deep research run failed")
        return 2

    print("\n=== SHORT SUMMARY ===")
    print(report.short_summary)
    print("\n=== FOLLOW-UP QUESTIONS ===")
    for q in report.follow_up_questions:
        print(f"- {q}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
