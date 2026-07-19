from __future__ import annotations

from typing import Any, Optional

from .base import BaseAdapter, AdapterMessage, AdapterRequest, AdapterResponse
from .openai_adapter import OpenAIAdapter, AnthropicAdapter, OllamaAdapter
from .openrouter_adapter import OpenRouterAdapter


def get_adapter(
    adapter_type: str = "openai",
    model: Optional[str] = None,
    **kwargs: Any,
) -> BaseAdapter:
    adapter_type = adapter_type.lower()
    registry = {
        "openai": OpenAIAdapter,
        "anthropic": AnthropicAdapter,
        "ollama": OllamaAdapter,
        "openrouter": OpenRouterAdapter,
    }
    if adapter_type not in registry:
        raise ValueError(
            f"Unknown adapter '{adapter_type}'. Choose from: {list(registry.keys())}"
        )
    return registry[adapter_type](model=model or "", **kwargs)


__all__ = [
    "BaseAdapter",
    "AdapterMessage",
    "AdapterRequest",
    "AdapterResponse",
    "OpenAIAdapter",
    "AnthropicAdapter",
    "OllamaAdapter",
    "OpenRouterAdapter",
    "get_adapter",
]
