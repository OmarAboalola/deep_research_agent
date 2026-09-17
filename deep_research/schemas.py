"""Structured-output schemas shared by the Planner and Writer agents.

Keeping these in one module (rather than defined inline mid-notebook) means
every agent that needs `ReportData`, for example, imports the same
definition — no risk of two cells silently diverging.
"""

from pydantic import BaseModel, Field


class WebSearchItem(BaseModel):
    """A single planned web search."""

    reason: str = Field(description="Why this search is important to the query.")
    query: str = Field(description="The exact search term to use.")


class WebSearchPlan(BaseModel):
    """The Planner agent's full output: a list of searches to run."""

    searches: list[WebSearchItem] = Field(
        description="A list of web searches to perform to best answer the query."
    )


class ReportData(BaseModel):
    """The Writer agent's structured report output."""

    short_summary: str = Field(description="A concise 2-3 sentence summary of the findings.")
    markdown_report: str = Field(description="The complete report, written in Markdown.")
    follow_up_questions: list[str] = Field(description="Suggested topics to research further.")
