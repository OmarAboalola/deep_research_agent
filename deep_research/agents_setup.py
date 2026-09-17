"""
Defines the four agents in the pipeline: Research, Planner, Writer, Email.

Instructions are kept as module-level constants (not f-strings built at
import time from mutable state) so they're easy to unit-test and diff in
code review.
"""

from __future__ import annotations

from agents import Agent

from .config import HOW_MANY_SEARCHES
from .email_tool import send_email_tool
from .llm_clients import get_model
from .schemas import ReportData, WebSearchPlan
from .search_tool import web_search

RESEARCH_INSTRUCTIONS = """
You are a research assistant.

You have ONE tool available: web_search.

When you need information from the web, ALWAYS use the web_search tool.

Do NOT use a tool named visit.
Do NOT use a tool named browse.
Do NOT use a tool named search.
Do NOT invent or call any other tools.

Use web_search with the search query provided by the user.
After receiving the search results, summarize the useful information.
"""

PLANNER_INSTRUCTIONS_TEMPLATE = """
You are a research assistant.

Given the user's query, create a research search plan.

You MUST return exactly {how_many_searches} search items.

Each search item must contain:
- reason: why this search is useful
- query: the exact web search query

Return ONLY valid JSON matching the WebSearchPlan schema.

Do not return Markdown.
Do not return explanations.
Do not return an empty response.
"""

WRITER_INSTRUCTIONS = """
You are a research report writer.

You will receive:
1. The original user query.
2. Summarized web search results.

Write a comprehensive, accurate research report based ONLY on the provided
research information.

Your output MUST conform exactly to the ReportData schema.

The output must contain exactly these three fields:
- short_summary: A concise 2-3 sentence summary.
- markdown_report: The complete report written in Markdown.
- follow_up_questions: A list of useful questions for further research.

IMPORTANT:
Return ONLY valid JSON.
Do NOT return Markdown directly.
Do NOT include ```json fences.
Do NOT include any text before or after the JSON object.

The markdown_report field itself may contain Markdown.
"""

EMAIL_INSTRUCTIONS = """
You are provided with a detailed report. Use your tool to send an email, converting the report into
a clean, well presented HTML email with an appropriate subject line.
"""


def build_agents() -> dict[str, Agent]:
    """Construct all four agents against the currently-configured model.

    Called once at startup (not per-request) — Agent objects are cheap and
    stateless, so this can be reused across many `run_deep_research` calls.
    """
    model = get_model()

    research_agent = Agent(
        name="Research Agent",
        instructions=RESEARCH_INSTRUCTIONS,
        model=model,
        tools=[web_search],
    )

    planner_agent = Agent(
        name="Planner Agent",
        instructions=PLANNER_INSTRUCTIONS_TEMPLATE.format(how_many_searches=HOW_MANY_SEARCHES),
        model=model,
        output_type=WebSearchPlan,
    )

    writer_agent = Agent(
        name="Writer Agent",
        instructions=WRITER_INSTRUCTIONS,
        model=model,
        output_type=ReportData,
    )

    email_agent = Agent(
        name="Email Agent",
        instructions=EMAIL_INSTRUCTIONS,
        tools=[send_email_tool],
        model=model,
    )

    return {
        "research": research_agent,
        "planner": planner_agent,
        "writer": writer_agent,
        "email": email_agent,
    }
