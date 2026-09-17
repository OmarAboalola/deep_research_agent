"""
Builds the AsyncOpenAI-compatible client and Agents-SDK model wrapper for
whichever provider is selected via MODEL_PROVIDER.

The notebook built all three clients/models unconditionally, even though it
only ever used one (`google_model`) and left a warning comment saying not to
use the other two. In production we only construct what we're actually
going to use — one less thing to misconfigure, one less set of credentials
that has to be present.
"""

from __future__ import annotations

from agents import OpenAIChatCompletionsModel
from openai import AsyncOpenAI

from . import config


def get_model() -> OpenAIChatCompletionsModel:
    """Return the Agents-SDK model for the configured MODEL_PROVIDER."""
    if config.MODEL_PROVIDER == "google":
        client = AsyncOpenAI(base_url=config.GOOGLE_BASE_URL, api_key=config.GOOGLE_API_KEY)
        return OpenAIChatCompletionsModel(model=config.GOOGLE_MODEL_NAME, openai_client=client)

    if config.MODEL_PROVIDER == "groq":
        client = AsyncOpenAI(base_url=config.GROQ_BASE_URL, api_key=config.GROQ_API_KEY)
        return OpenAIChatCompletionsModel(model=config.GROQ_MODEL_NAME, openai_client=client)

    if config.MODEL_PROVIDER == "openrouter":
        client = AsyncOpenAI(base_url=config.OPENROUTER_BASE_URL, api_key=config.OPENROUTER_API_KEY)
        return OpenAIChatCompletionsModel(model=config.OPENROUTER_MODEL_NAME, openai_client=client)

    raise ValueError(f"Unknown MODEL_PROVIDER: {config.MODEL_PROVIDER!r}")
