"""Base agent: holds the LLM provider and a small structured activity log."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from ..llm import LLMProvider, HeuristicLLMProvider


@dataclass
class AgentLog:
    entries: List[str] = field(default_factory=list)

    def add(self, agent: str, message: str) -> None:
        self.entries.append(f"[{agent}] {message}")


class BaseAgent:
    name = "agent"

    def __init__(self, llm: LLMProvider | None = None, log: AgentLog | None = None) -> None:
        self.llm = llm or HeuristicLLMProvider()
        self.log = log or AgentLog()

    def say(self, message: str) -> None:
        self.log.add(self.name, message)
