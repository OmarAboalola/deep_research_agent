"""
Deep Research — a 4-agent pipeline (Planner -> Search -> Writer -> Email)
built on the OpenAI Agents SDK.

Production entry point:

    from deep_research import run_deep_research
    report = await run_deep_research("Most popular AI agent frameworks in 2026")
"""

from .research_manager import run_deep_research

__all__ = ["run_deep_research"]
