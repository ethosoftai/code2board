"""Abstract simulator backend interface."""

from __future__ import annotations

from pathlib import Path

from ..schemas import SimulationResult


class SimulatorBackend:
    name: str = "base"

    def is_available(self) -> bool:  # pragma: no cover - interface
        raise NotImplementedError

    def run(self, project_dir: Path, timeout_sec: int = 30) -> SimulationResult:  # pragma: no cover
        raise NotImplementedError
