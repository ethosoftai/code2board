"""Optional OpenAI provider (reads OPENAI_API_KEY).

Falls back to the heuristic provider for anything it can't do, and never raises:
if the key or ``requests`` is missing, :meth:`is_available` returns ``False`` and
the orchestrator uses heuristic mode instead.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from ..utils import HAS_REQUESTS
from .base import LLMProvider
from .heuristic_llm import HeuristicLLMProvider


class OpenAIProvider(LLMProvider):
    name = "openai"
    API_URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        self.model = os.environ.get("OPENAI_MODEL", model)
        self.api_key = os.environ.get("OPENAI_API_KEY")
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
        # Keep the validated, deterministic firmware. We do not let the LLM
        # rewrite firmware that has already passed validation.
        return context.get("firmware_source", "")

    def generate_explanation(self, context: Dict[str, Any]) -> str:
        if not self.is_available():
            return self._fallback.generate_explanation(context)
        try:
            system = ("You are RoboMentor, a friendly robotics teacher for high-school students. "
                      "Explain clearly, step by step, in Markdown. Be encouraging and accurate. "
                      "Do not include dangerous instructions; include practical safety notes.")
            user = (
                f"Project: {context.get('project_name')}\n"
                f"Board: {context.get('board_name')}\n"
                f"Parts: {', '.join(context.get('used_parts', []))}\n"
                f"Wiring steps: {context.get('wiring_steps')}\n"
                f"Learning objectives: {context.get('learning_objectives')}\n\n"
                "Write an educational explanation a 15-year-old can follow."
            )
            return self._chat(system, user)
        except Exception:
            return self._fallback.generate_explanation(context)
