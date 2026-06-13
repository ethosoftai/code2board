"""Default, fully-offline heuristic "LLM" provider.

It produces deterministic, template-driven text. This is what makes RoboMentor
work with zero API keys and zero internet — the cloud providers only swap in
richer prose.
"""

from __future__ import annotations

from typing import Any, Dict

from .base import LLMProvider


class HeuristicLLMProvider(LLMProvider):
    name = "heuristic"

    def is_available(self) -> bool:
        return True

    def generate_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        # The deterministic planner already produced the plan; we just pass a
        # human-friendly summary through unchanged.
        return {
            "reasoning_summary": context.get("reasoning_summary", ""),
            "source": "heuristic",
        }

    def generate_code(self, context: Dict[str, Any]) -> str:
        # The deterministic code generator owns the firmware; heuristic mode
        # returns it untouched.
        return context.get("firmware_source", "")

    def generate_explanation(self, context: Dict[str, Any]) -> str:
        project = context.get("project_name", "this project")
        board = context.get("board_name", "your board")
        parts = context.get("used_parts", [])
        objectives = context.get("learning_objectives", [])
        steps = context.get("wiring_steps", [])

        lines = [f"# How {project} works", ""]
        lines.append(
            f"In this project you build **{project}** using **{board}**. "
            "Let's walk through it the way you'd explain it to a friend in the robotics club."
        )
        lines.append("")
        lines.append("## The big idea")
        lines.append(context.get("big_idea",
                                 "The microcontroller reads its sensors, makes a decision, and "
                                 "controls its outputs — over and over, many times per second."))
        lines.append("")
        if parts:
            lines.append("## The parts and their jobs")
            for p in parts:
                lines.append(f"- **{p}**")
            lines.append("")
        if steps:
            lines.append("## How it's wired (step by step)")
            for i, s in enumerate(steps, 1):
                lines.append(f"{i}. {s}")
            lines.append("")
        lines.append("## The loop: sense → think → act")
        lines.append(context.get("loop_explanation",
                                 "Inside `loop()`, the board reads inputs, decides what to do, then "
                                 "drives its outputs. `Serial.print` lets you watch those decisions."))
        lines.append("")
        if objectives:
            lines.append("## What you'll learn")
            for o in objectives:
                lines.append(f"- {o}")
            lines.append("")
        lines.append("## Try it yourself")
        lines.append("- Open the Serial Monitor at 9600 baud and watch the messages.")
        lines.append("- Change one tunable value (like a speed or threshold) and see what happens.")
        lines.append("- Set `SELF_TEST` to 1 to check your wiring before the full program runs.")
        return "\n".join(lines)
