"""LLM provider registry. Default is the offline heuristic provider."""

from __future__ import annotations

from .anthropic_provider import AnthropicProvider
from .base import LLMProvider
from .groq_provider import GroqProvider
from .heuristic_llm import HeuristicLLMProvider
from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider

__all__ = [
    "LLMProvider",
    "HeuristicLLMProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "GroqProvider",
    "OllamaProvider",
    "get_provider",
]

_PROVIDERS = {
    "heuristic": HeuristicLLMProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "groq": GroqProvider,
    "ollama": OllamaProvider,
}


def get_provider(name: str = "heuristic") -> LLMProvider:
    """Return the requested provider, transparently falling back to heuristic
    mode if the chosen cloud provider has no key / isn't reachable."""
    name = (name or "heuristic").lower()
    cls = _PROVIDERS.get(name, HeuristicLLMProvider)
    provider = cls()
    if not provider.is_available():
        return HeuristicLLMProvider()
    return provider
