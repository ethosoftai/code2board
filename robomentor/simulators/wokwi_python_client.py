"""Optional Wokwi Python-client backend (feature-flagged).

If a Wokwi Python client package is installed (the import name is configurable),
this backend can be enabled.  It is disabled by default and skips gracefully
when the package is absent — RoboMentor never requires credentials to run.
"""

from __future__ import annotations

import importlib
import time
from pathlib import Path

from ..schemas import SimulationResult
from ..utils import has_module
from .base import SimulatorBackend

# Candidate import names for a community/official Wokwi python client.
_CANDIDATE_MODULES = ("wokwi", "wokwi_client", "pywokwi")


class WokwiPythonClientBackend(SimulatorBackend):
    name = "wokwi_python_client"

    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled
        self.module_name = next((m for m in _CANDIDATE_MODULES if has_module(m)), None)

    def is_available(self) -> bool:
        return self.enabled and self.module_name is not None

    def run(self, project_dir: Path, timeout_sec: int = 30) -> SimulationResult:
        start = time.time()
        if not self.enabled:
            return SimulationResult(
                backend=self.name, success=False, available=False,
                message="Wokwi python client backend is disabled (feature flag off).",
                status={"skipped": True, "reason": "disabled"},
            )
        if self.module_name is None:
            return SimulationResult(
                backend=self.name, success=False, available=False,
                message="No Wokwi python client package installed; skipped.",
                status={"skipped": True, "reason": "module_not_found",
                        "looked_for": list(_CANDIDATE_MODULES)},
            )
        try:
            importlib.import_module(self.module_name)
            # A real integration would create a session, upload diagram+firmware,
            # run and capture serial. We intentionally do not fabricate results.
            return SimulationResult(
                backend=self.name, success=False, available=True,
                message=(f"Found '{self.module_name}' but no verified integration is wired up; "
                         "skipping to avoid fabricating simulation output."),
                status={"skipped": True, "reason": "no_verified_integration",
                        "module": self.module_name},
                duration_sec=round(time.time() - start, 4),
            )
        except Exception as exc:
            return SimulationResult(
                backend=self.name, success=False, available=False,
                message=f"Wokwi python client failed to import: {exc}",
                status={"error": str(exc)},
            )
