"""Runtime configuration for a RoboMentor generation run.

A single :class:`RunConfig` dataclass is threaded through the pipeline so every
component (planner, generators, validators, simulators, renderers) sees the same
options.  Defaults are chosen so the tool runs fully offline with no API keys.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# Simulation modes
SIM_AUTO = "auto"
SIM_STATIC = "static"
SIM_WOKWI = "wokwi"
SIM_NONE = "none"

# Render levels
RENDER_NONE = "none"
RENDER_BASIC = "basic"
RENDER_HIGH = "high"


@dataclass
class RunConfig:
    materials_path: Optional[Path] = None
    request_path: Optional[Path] = None
    request_text: str = ""
    out_dir: Path = Path("outputs/robomentor_run")
    board: str = "auto"           # board id, alias, or "auto"
    simulate: str = SIM_AUTO      # auto | static | wokwi | none
    render: str = RENDER_HIGH     # none | basic | high
    llm_provider: str = "heuristic"  # heuristic | openai | anthropic | groq | ollama
    seed: int = 1337              # deterministic pin/layout choices
    timeout_sec: int = 30
    project_hint: Optional[str] = None  # force a template, e.g. "line_follower"
    verbose: bool = True

    def __post_init__(self) -> None:
        self.out_dir = Path(self.out_dir)

    # Convenience accessors -------------------------------------------------- #
    @property
    def wants_render(self) -> bool:
        return self.render in (RENDER_BASIC, RENDER_HIGH)

    @property
    def high_render(self) -> bool:
        return self.render == RENDER_HIGH
