#!/usr/bin/env python3
"""
Web server for the Deep Research pipeline.

Wraps `deep_research.run_deep_research` behind a small job-based API so the
bundled frontend (frontend/index.html) can kick off a search and poll for
progress, instead of holding one long HTTP request open while four agents
run.

Run:
    pip install -r requirements.txt
    cp .env.example .env   # fill in your API key
    python server.py
    # open http://localhost:8000
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from deep_research import run_deep_research
from deep_research.config import logger, validate_config

BASE_DIR = Path(__file__).parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(title="Deep Research")

# In-memory job store. Fine for a single-process local/dev deployment; swap
# for Redis or a DB table if this ever needs to run behind multiple workers.
_jobs: dict[str, dict] = {}


class SearchRequest(BaseModel):
    query: str


class SearchResponse(BaseModel):
    job_id: str


def _new_job(query: str) -> str:
    job_id = uuid.uuid4().hex
    _jobs[job_id] = {
        "query": query,
        "stage": "queued",
        "message": "Queued…",
        "result": None,
        "error": None,
    }
    return job_id


def _make_status_callback(job_id: str):
    def _on_status(stage: str, message: str) -> None:
        job = _jobs.get(job_id)
        if job is not None:
            job["stage"] = stage
            job["message"] = message

    return _on_status


async def _run_job(job_id: str, query: str) -> None:
    job = _jobs[job_id]
    try:
        report = await run_deep_research(query, on_status=_make_status_callback(job_id))
        job["stage"] = "done"
        job["message"] = "Done."
        job["result"] = {
            "short_summary": report.short_summary,
            "markdown_report": report.markdown_report,
            "follow_up_questions": report.follow_up_questions,
        }
    except Exception as exc:  # noqa: BLE001 - surface any failure to the UI
        logger.exception("Research job %s failed for query=%r", job_id, query)
        job["stage"] = "error"
        job["message"] = "Something went wrong."
        job["error"] = str(exc)


@app.on_event("startup")
def _check_config() -> None:
    try:
        validate_config()
    except (ValueError, EnvironmentError) as exc:
        # Don't crash the server — let it boot so the frontend can render a
        # clear error, rather than a connection refused with no context.
        logger.error("Configuration error at startup: %s", exc)


@app.post("/api/search", response_model=SearchResponse)
async def start_search(payload: SearchRequest) -> SearchResponse:
    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    if len(query) > 500:
        raise HTTPException(status_code=400, detail="Query is too long.")

    job_id = _new_job(query)
    asyncio.create_task(_run_job(job_id, query))
    return SearchResponse(job_id=job_id)


@app.get("/api/status/{job_id}")
async def get_status(job_id: str) -> dict:
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown job id.")
    return job


# --- Static frontend --------------------------------------------------------
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="assets")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
