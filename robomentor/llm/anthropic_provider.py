"""Optional Anthropic (Claude) provider (reads ANTHROPIC_API_KEY).

Never raises; falls back to heuristic mode when unavailable.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from ..utils import HAS_REQUESTS
from .base import LLMProvider
from .heuristic_llm import HeuristicLLMProvider


class AnthropicProvider(LLMProvider):
    name = "anthropic"
    API_URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, model: str = "claude-opus-4-8") -> None:
        self.model = os.environ.get("ANTHROPIC_MODEL", model)
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        self._fallback = HeuristicLLMProvider()

    def is_available(self) -> bool:
        return bool(self.api_key) and HAS_REQUESTS

    def _message(self, system: str, user: str, max_tokens: int = 1024) -> str:
        import requests  # type: ignore

        resp = requests.post(
            self.API_URL,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            data=json.dumps({
                "model": self.model,
                "max_tokens": max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            }),
            timeout=40,
        )
        resp.raise_for_status()
        data = resp.json()
        return "".join(block.get("text", "") for block in data.get("content", [])).strip()

    def generate_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return self._fallback.generate_plan(context)

    def generate_code(self, context: Dict[str, Any]) -> str:
        return context.get("firmware_source", "")

    def generate_explanation(self, context: Dict[str, Any]) -> str:
        if not self.is_available():
            return self._fallback.generate_explanation(context)
        try:
            system = ("You are RoboMentor, a friendly robotics teacher for high-school students. "
                      "Explain step by step in Markdown, accurately and encouragingly, with "
                      "practical safety notes and no dangerous instructions.")
            user = (
                f"Project: {context.get('project_name')}\n"
                f"Board: {context.get('board_name')}\n"
                f"Parts: {', '.join(context.get('used_parts', []))}\n"
                f"Wiring steps: {context.get('wiring_steps')}\n"
                f"Learning objectives: {context.get('learning_objectives')}\n\n"
                "Write the educational explanation."
            )
            return self._message(system, user)
        except Exception:
            return self._fallback.generate_explanation(context)
