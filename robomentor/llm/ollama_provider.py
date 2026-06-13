"""Optional local Ollama provider (HTTP, no API key).

Talks to a local Ollama server (default http://localhost:11434). If the server
isn't reachable, falls back to heuristic mode. Never raises.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from ..utils import HAS_REQUESTS
from .base import LLMProvider
from .heuristic_llm import HeuristicLLMProvider


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, model: str = "llama3.1") -> None:
        self.host = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
        self.model = os.environ.get("OLLAMA_MODEL", model)
        self._fallback = HeuristicLLMProvider()

    def is_available(self) -> bool:
        if not HAS_REQUESTS:
            return False
        try:
            import requests  # type: ignore

            r = requests.get(f"{self.host}/api/tags", timeout=2)
            return r.status_code == 200
        except Exception:
            return False

    def _generate(self, prompt: str) -> str:
        import requests  # type: ignore

        resp = requests.post(
            f"{self.host}/api/generate",
            data=json.dumps({"model": self.model, "prompt": prompt, "stream": False}),
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()

    def generate_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return self._fallback.generate_plan(context)

    def generate_code(self, context: Dict[str, Any]) -> str:
        return context.get("firmware_source", "")

    def generate_explanation(self, context: Dict[str, Any]) -> str:
        if not self.is_available():
            return self._fallback.generate_explanation(context)
        try:
            prompt = (
                "You are RoboMentor, a friendly high-school robotics teacher. "
                "Write a clear, step-by-step educational explanation in Markdown with practical "
                "safety notes (no dangerous instructions).\n\n"
                f"Project: {context.get('project_name')} on {context.get('board_name')}.\n"
                f"Parts: {', '.join(context.get('used_parts', []))}.\n"
                f"Wiring steps: {context.get('wiring_steps')}.\n"
            )
            return self._generate(prompt)
        except Exception:
            return self._fallback.generate_explanation(context)
