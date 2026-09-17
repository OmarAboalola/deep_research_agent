"""
Orchestrates the four agents end to end.

Production hardening vs. the notebook version:
- Planner retry logic is preserved but generalized into `_run_with_retries`
  and applied to every agent call, not just the planner.
- `asyncio.gather(..., return_exceptions=True)` for the parallel searches:
  one failed search no longer aborts the whole research run — we just
  proceed with whatever succeeded, and log the rest.
- The report is written to disk BEFORE the email step, so a broken email
  integration never loses a finished report.
- `run_deep_research()` is the single public function other code (a CLI, a
  web endpoint, a scheduled job) should call.
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from typing import Callable, Optional

from agents import Runner, trace

from .agents_setup import build_agents
from .config import MAX_RETRIES, REPORTS_DIR, logger, validate_config
from .schemas import ReportData, WebSearchItem

# Optional progress hook: (stage, message) -> None. Stages: "planning",
# "searching", "writing", "saving", "emailing", "done". Callers (e.g. a web
# server driving a progress bar) pass this in; the CLI and library callers
# who don't care can ignore it entirely — default is a no-op.
StatusCallback = Callable[[str, str], None]


def _noop(_stage: str, _message: str) -> None:
    return None


async def _run_with_retries(agent, message: str, *, label: str):
    """Run an agent with simple retry-on-exception, since LLM APIs are flaky."""
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return await Runner.run(agent, message)
        except Exception as exc:
            last_error = exc
            logger.warning("%s attempt %s/%s failed: %s", label, attempt, MAX_RETRIES, exc)
    logger.error("%s exhausted all retries", label)
    raise last_error


async def _perform_search(agent, item: WebSearchItem) -> str | None:
    """Run a single planned search; return None (not raise) on failure."""
    input_message = f"Search term: {item.query}\nReason for searching: {item.reason}"
    try:
        result = await _run_with_retries(agent, input_message, label=f"search[{item.query!r}]")
        return result.final_output
    except Exception:
        logger.error("Search permanently failed for query=%r — continuing without it", item.query)
        return None


async def _run_searches(agents: dict, query: str, on_status: StatusCallback) -> list[str]:
    logger.info("Planning searches for query=%r", query)
    on_status("planning", "Planning the research…")
    plan_result = await _run_with_retries(agents["planner"], f"Query: {query}", label="planner")
    searches = plan_result.final_output.searches
    logger.info("Planner produced %s searches", len(searches))
    on_status("searching", f"Searching the web ({len(searches)} queries)…")

    tasks = [_perform_search(agents["research"], item) for item in searches]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    results = []
    for item, result in zip(searches, raw_results):
        if isinstance(result, Exception) or result is None:
            logger.warning("Dropping failed search: %r", item.query)
            continue
        results.append(result)

    if not results:
        raise RuntimeError("All planned searches failed — cannot write a report with no data.")

    logger.info("Finished searching: %s/%s succeeded", len(results), len(searches))
    return results


async def _write_report(
    agents: dict, query: str, search_results: list[str], on_status: StatusCallback
) -> ReportData:
    logger.info("Writing report...")
    on_status("writing", "Writing the report…")
    input_message = f"Original query: {query}\nSummarized search results: {search_results}"
    result = await _run_with_retries(agents["writer"], input_message, label="writer")
    logger.info("Finished writing report")
    return result.final_output


def _save_report_to_disk(query: str, report: ReportData) -> str:
    """Persist the report locally regardless of email outcome."""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_slug = "".join(c if c.isalnum() else "_" for c in query)[:50]
    path = os.path.join(REPORTS_DIR, f"{timestamp}_{safe_slug}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# {query}\n\n{report.markdown_report}\n")
    logger.info("Report saved to %s", path)
    return path


async def _send_report_email(agents: dict, report: ReportData, on_status: StatusCallback) -> None:
    logger.info("Sending report email...")
    on_status("emailing", "Sending the report…")
    try:
        await _run_with_retries(agents["email"], report.markdown_report, label="email")
        logger.info("Email step complete")
    except Exception:
        # Deliberately non-fatal: the report is already saved to disk by this point.
        logger.exception("Email sending failed — report was still saved to disk")


async def run_deep_research(
    query: str, on_status: Optional[StatusCallback] = None
) -> ReportData:
    """Run the full pipeline for one query and return the structured report.

    Raises only if the pipeline could not produce a report at all (bad
    config, or every single search failing). Email failures are logged but
    do not raise, since the report itself has already been produced/saved.

    `on_status`, if given, is called as on_status(stage, message) at each
    step transition — handy for a UI progress indicator (e.g. the bundled
    web frontend). It is never required: callers that don't pass it get
    identical behavior to before.
    """
    status = on_status or _noop
    validate_config()
    agents = build_agents()

    with trace("Deep research run"):
        search_results = await _run_searches(agents, query, status)
        report = await _write_report(agents, query, search_results, status)
        status("saving", "Saving the report…")
        _save_report_to_disk(query, report)
        await _send_report_email(agents, report, status)

    status("done", "Done.")
    logger.info("Deep research run complete for query=%r", query)
    return report
