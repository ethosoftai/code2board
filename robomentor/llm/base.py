"""LLM provider interface.

RoboMentor never *requires* an LLM. Providers can enrich the reasoning summary,
firmware comments and educational explanation, but the deterministic generators
always produce a complete, valid project on their own.
"""

from __future__ import annotations

from typing import Any, Dict


class LLMProvider:
    name: str = "base"

    def is_available(self) -> bool:
        return True

    def generate_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:  # pragma: no cover
        raise NotImplementedError

    def generate_code(self, context: Dict[str, Any]) -> str:  # pragma: no cover
        raise NotImplementedError

    def generate_explanation(self, context: Dict[str, Any]) -> str:  # pragma: no cover
        raise NotImplementedError
