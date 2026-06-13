"""Simulator selection and orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import List

from ..config import SIM_AUTO, SIM_NONE, SIM_STATIC, SIM_WOKWI
from ..schemas import SimulationResult
from .base import SimulatorBackend
from .local_static import LocalStaticBackend
from .wokwi_cli import WokwiCliBackend
from .wokwi_python_client import WokwiPythonClientBackend

__all__ = [
    "SimulatorBackend",
    "LocalStaticBackend",
    "WokwiCliBackend",
    "WokwiPythonClientBackend",
    "simulate",
]


def simulate(project_dir: Path, mode: str = SIM_AUTO, timeout_sec: int = 30) -> SimulationResult:
    """Run simulation according to ``mode``.

    * ``none``   — skip entirely.
    * ``static`` — always use the local static backend.
    * ``wokwi``  — try Wokwi CLI, then python client; fall back to static.
    * ``auto``   — try Wokwi CLI if present, else static (the default).
    """
    project_dir = Path(project_dir)

    if mode == SIM_NONE:
        return SimulationResult(
            backend="none", success=False, available=False,
            message="Simulation disabled (--simulate none).",
            status={"skipped": True},
        )

    static = LocalStaticBackend()

    if mode == SIM_STATIC:
        return static.run(project_dir, timeout_sec)

    # auto / wokwi: build the preference chain
    chain: List[SimulatorBackend] = [WokwiCliBackend()]
    if mode == SIM_WOKWI:
        chain.append(WokwiPythonClientBackend(enabled=True))

    notes = []
    for backend in chain:
        if backend.is_available():
            result = backend.run(project_dir, timeout_sec)
            if result.success or result.available:
                # If the backend ran but couldn't really simulate, still record it,
                # then ALSO run static so the demo has a populated status.
                if result.success:
                    return result
                notes.append(f"{backend.name}: {result.message}")
        else:
            notes.append(f"{backend.name}: not available")

    fallback = static.run(project_dir, timeout_sec)
    fallback.status.setdefault("fallback_from", notes)
    fallback.message = (
        "Wokwi backend(s) unavailable or could not run; "
        + fallback.message
    )
    return fallback
