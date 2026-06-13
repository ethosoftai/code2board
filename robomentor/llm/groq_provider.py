"""Optional Groq provider (reads GROQ_API_KEY).

Groq exposes an OpenAI-compatible chat-completions API. Never raises; falls back
to heuristic mode when unavailable.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from ..utils import HAS_REQUESTS
from .base import LLMProvider
from .heuristic_llm import HeuristicLLMProvider


class GroqProvider(LLMProvider):
    name = "groq"
    API_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, model: str = "llama-3.1-8b-instant") -> None:
        self.model = os.environ.get("GROQ_MODEL", model)
        self.api_key = os.environ.get("GROQ_API_KEY")
        self._fallback = HeuristicLLMProvider()

    def is_available(self) -> bool:
        return bool(self.api_key) and HAS_REQUESTS

    def _chat(self, system: str, user: str, max_tokens: int = 900) -> str:
        import requests  # type: ignore

        resp = requests.post(
            self.API_URL,
            headers={"Authorization": f"Bearer {self.api_key}",
                     "Content-Type": "application/json"},
            data=json.dumps({
                "model": self.model,
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": user}],
                "temperature": 0.3,
                "max_tokens": max_tokens,
            }),
            timeout=40,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    def generate_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return self._fallback.generate_plan(context)

    def generate_code(self, context: Dict[str, Any]) -> str:
        return context.get("firmware_source", "")

    def generate_explanation(self, context: Dict[str, Any]) -> str:
        if not self.is_available():
            return self._fallback.generate_explanation(context)
        try:
            system = ("You are RoboMentor, a friendly high-school robotics teacher. Explain "
                      "step by step in Markdown with practical safety notes.")
            user = (
                f"Project: {context.get('project_name')} on {context.get('board_name')}.\n"
                f"Parts: {', '.join(context.get('used_parts', []))}.\n"
                f"Wiring steps: {context.get('wiring_steps')}.\n"
                "Write an educational explanation for a 15-year-old."
            )
            return self._chat(system, user)
        except Exception:
            return self._fallback.generate_explanation(context)
