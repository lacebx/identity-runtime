from __future__ import annotations

from typing import Any, Optional

from .openai_adapter import OpenAIAdapter


class OpenRouterAdapter(OpenAIAdapter):
    """
    Adapter for OpenRouter — a unified API gateway to many LLM providers.

    OpenRouter exposes an OpenAI-compatible API at api.openrouter.ai/v1
    and supports seamless model switching across providers.

    Usage:
        adapter = OpenRouterAdapter(
            model="openai/gpt-4o",
            api_key="sk-or-v1-...",
        )
        runtime = IdentityRuntime(adapter=adapter)

    Environment variables:
        OPENROUTER_API_KEY  — your OpenRouter API key
        OPENROUTER_BASE_URL — optional custom base URL (default: https://openrouter.ai/api/v1)
    """

    def __init__(
        self,
        model: str = "openai/gpt-4o",
        api_key: Optional[str] = None,
        base_url: str = "https://openrouter.ai/api/v1",
        site_url: Optional[str] = None,
        site_name: Optional[str] = None,
        **kwargs: Any,
    ):
        super().__init__(
            model=model,
            api_key=api_key,
            base_url=base_url,
            **kwargs,
        )
        self.site_url = site_url
        self.site_name = site_name

    def _get_client(self):
        client = super()._get_client()
        if self.site_url or self.site_name:
            default_headers = {}
            if self.site_url:
                default_headers["HTTP-Referer"] = self.site_url
            if self.site_name:
                default_headers["X-Title"] = self.site_name
            if default_headers:
                client.default_headers = {
                    **(client.default_headers or {}),
                    **default_headers,
                }
        return client
