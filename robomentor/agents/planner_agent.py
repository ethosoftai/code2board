"""Planner agent: deterministic plan + optional LLM-enriched reasoning summary."""

from __future__ import annotations

from typing import Optional

from .. import planner
from ..schemas import MaterialList, PlannerResult
from .base_agent import BaseAgent


class PlannerAgent(BaseAgent):
    name = "planner_agent"

    def run(self, material: MaterialList, request_text: str, board: str = "auto",
            project_hint: Optional[str] = None) -> PlannerResult:
        result = planner.plan(material, request_text, board=board, project_hint=project_hint)
        self.say(f"selected '{result.selected_project}' on '{result.selected_board}' "
                 f"(confidence {result.confidence:.2f})")

        # LLM may only refine the human-readable summary; feasibility is fixed.
        enriched = self.llm.generate_plan({"reasoning_summary": result.reasoning_summary})
        summary = enriched.get("reasoning_summary")
        if summary and summary != result.reasoning_summary:
            result.reasoning_summary = summary
            self.say("reasoning summary enriched by LLM provider")
        return result
