"""
Azure OpenAI chat model factory.

Environment variables:
  - AZURE_OPENAI_ENDPOINT
  - AZURE_OPENAI_API_KEY
  - AZURE_OPENAI_API_VERSION
  - AZURE_OPENAI_DEPLOYMENT
"""

from __future__ import annotations

import os

from langchain_openai import AzureChatOpenAI


def _require_env(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        raise RuntimeError(
            f"Missing {name}. Set it in Azure App Service Configuration (or your local env) before starting."
        )
    return val


def get_chat_model() -> AzureChatOpenAI:
    """
    Construct an Azure OpenAI chat model.

    Returns a LangChain `AzureChatOpenAI` instance that supports `.invoke()` and `.stream()`.
    """

    endpoint = _require_env("AZURE_OPENAI_ENDPOINT")
    api_key = _require_env("AZURE_OPENAI_API_KEY")
    api_version = _require_env("AZURE_OPENAI_API_VERSION")
    deployment = _require_env("AZURE_OPENAI_DEPLOYMENT")

    return AzureChatOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=api_version,
        azure_deployment=deployment,
        temperature=0.0,
    )


