"""
Central configuration for the Deep Research pipeline.

Everything the pipeline needs is read from environment variables (loaded from
a local .env file in dev, or real environment variables / secrets manager in
production). `validate_config()` is called once at startup so a missing key
raises one clear error immediately, instead of the pipeline dying three
network calls deep with a cryptic 401.
"""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv

load_dotenv(override=True)

# --- Logging ---------------------------------------------------------------
# Replaces the notebook's `print(...)` calls. Configurable via LOG_LEVEL so
# it can be turned down in production and up while debugging.
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
)
logger = logging.getLogger("deep_research")

# --- Provider credentials ---------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GOOGLE_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

# --- Pipeline behaviour ------------------------------------------------------
# The original notebook hardcoded MODEL_NAME = google_model. That's fine for
# a lab, but production code shouldn't require an edit + redeploy to switch
# providers. MODEL_PROVIDER picks which client/model pair is used everywhere.
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "google")  # "google" | "groq" | "openrouter"

# NOTE: verify this model id is currently valid for your Google AI Studio
# account before deploying — model names get deprecated/renamed over time.
GOOGLE_MODEL_NAME = os.getenv("GOOGLE_MODEL_NAME", "gemini-3.5-flash-lite")
GROQ_MODEL_NAME = os.getenv("GROQ_MODEL_NAME", "openai/gpt-oss-120b")
OPENROUTER_MODEL_NAME = os.getenv("OPENROUTER_MODEL_NAME", "openrouter/auto")

USE_EMAIL = os.getenv("USE_EMAIL", "true").lower() == "true"
HOW_MANY_SEARCHES = int(os.getenv("HOW_MANY_SEARCHES", "5"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_BACKOFF_SECONDS = float(os.getenv("RETRY_BACKOFF_SECONDS", "2"))

# Where to persist reports locally, independent of whether email succeeds.
REPORTS_DIR = os.getenv("REPORTS_DIR", "reports")

_REQUIRED_KEYS = {
    "google": ("GOOGLE_API_KEY", GOOGLE_API_KEY),
    "groq": ("GROQ_API_KEY", GROQ_API_KEY),
    "openrouter": ("OPENROUTER_API_KEY", OPENROUTER_API_KEY),
}


def validate_config() -> None:
    """Fail fast and loud if required configuration is missing.

    Call this once, at process startup, before any agent is built.
    """
    if MODEL_PROVIDER not in _REQUIRED_KEYS:
        raise ValueError(
            f"Unknown MODEL_PROVIDER={MODEL_PROVIDER!r}. "
            f"Expected one of {list(_REQUIRED_KEYS)}."
        )

    key_name, key_value = _REQUIRED_KEYS[MODEL_PROVIDER]
    if not key_value:
        raise EnvironmentError(
            f"MODEL_PROVIDER is '{MODEL_PROVIDER}' but {key_name} is not set. "
            "Add it to your .env file or environment before starting the app."
        )

    if USE_EMAIL:
        # We don't hard-require SMTP/SendGrid vars here because email_tool.py
        # degrades gracefully (falls back to a push/log) if they're missing —
        # but we warn loudly so that's a deliberate choice, not a surprise.
        logger.info("USE_EMAIL is true — email_tool will require your messenger "
                    "backend (e.g. SendGrid) to be configured.")

    logger.info("Config OK — provider=%s, searches_per_query=%s", MODEL_PROVIDER, HOW_MANY_SEARCHES)
