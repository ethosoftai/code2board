"""Wokwi CLI simulation backend.

Detects ``wokwi-cli`` on PATH and, if present, runs it against the generated
project directory.  A missing CLI is *not* an error — :meth:`is_available`
simply returns ``False`` and the orchestrator falls back to the static backend.

NOTE: the real Wokwi CLI also needs a compiled firmware binary (.hex/.elf/.uf2)
and a ``WOKWI_CLI_TOKEN``.  RoboMentor does not compile firmware itself, so this
backend runs the CLI if a build artifact is already present and otherwise
reports a clear, non-fatal "skipped" status.  This avoids overclaiming a
successful simulation (requirement #24).
"""

from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

from ..schemas import SimulationResult
from .base import SimulatorBackend

_BUILD_GLOBS = ("*.hex", "*.elf", "*.uf2", "*.bin")


class WokwiCliBackend(SimulatorBackend):
    name = "wokwi_cli"

    def __init__(self) -> None:
        self.binary = shutil.which("wokwi-cli")

    def is_available(self) -> bool:
        return self.binary is not None

    def _find_build_artifact(self, project_dir: Path) -> Path | None:
        for pattern in _BUILD_GLOBS:
            for match in project_dir.rglob(pattern):
                return match
        return None

    def run(self, project_dir: Path, timeout_sec: int = 30) -> SimulationResult:
        start = time.time()
        project_dir = Path(project_dir)

        if not self.is_available():
            return SimulationResult(
                backend=self.name, success=False, available=False,
                message="wokwi-cli not found on PATH; simulation skipped.",
                status={"skipped": True, "reason": "cli_not_found"},
            )

        sim_dir = project_dir / "simulation"
        artifact = self._find_build_artifact(project_dir)
        if artifact is None:
            return SimulationResult(
                backend=self.name, success=False, available=True,
                message=("wokwi-cli is installed but no compiled firmware (.hex/.elf/.uf2) was "
                         "found. Compile the sketch (Arduino CLI / PlatformIO) into the project "
                         "first, then re-run simulation. Static validation was used instead."),
                status={"skipped": True, "reason": "no_build_artifact",
                        "hint": "RoboMentor generates source, not binaries."},
                duration_sec=round(time.time() - start, 4),
            )

        cmd = [self.binary, "--timeout", str(timeout_sec * 1000), str(sim_dir)]
        try:
            proc = subprocess.run(
                cmd, cwd=str(project_dir), capture_output=True, text=True,
                timeout=timeout_sec + 10,
            )
            serial = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
            success = proc.returncode == 0
            return SimulationResult(
                backend=self.name, success=success, available=True,
                serial_output=serial,
                status={"returncode": proc.returncode, "command": " ".join(cmd),
                        "artifact": str(artifact)},
                message="wokwi-cli finished." if success else "wokwi-cli reported a non-zero exit.",
                duration_sec=round(time.time() - start, 4),
            )
        except subprocess.TimeoutExpired:
            return SimulationResult(
                backend=self.name, success=False, available=True,
                message=f"wokwi-cli timed out after {timeout_sec}s.",
                status={"timeout": True},
                duration_sec=round(time.time() - start, 4),
            )
        except Exception as exc:  # never crash the whole program
            return SimulationResult(
                backend=self.name, success=False, available=True,
                message=f"wokwi-cli failed to run: {exc}",
                status={"error": str(exc)},
                duration_sec=round(time.time() - start, 4),
            )
