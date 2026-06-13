"""Local static "pseudo-simulation" backend.

Always available. It does **not** perform electrical simulation — it statically
inspects the generated firmware + diagram and produces a believable status
report plus a synthesised serial transcript so the demo always has something to
show, even with no internet and no Wokwi installed.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

from ..schemas import SimulationResult
from ..utils import read_json, read_text
from .base import SimulatorBackend


class LocalStaticBackend(SimulatorBackend):
    name = "local_static"

    def is_available(self) -> bool:
        return True

    def run(self, project_dir: Path, timeout_sec: int = 30) -> SimulationResult:
        start = time.time()
        project_dir = Path(project_dir)
        sketch_path = project_dir / "firmware" / "sketch.ino"
        diagram_path = project_dir / "simulation" / "diagram.json"

        firmware_ok = sketch_path.exists()
        diagram_ok = diagram_path.exists()
        source = read_text(sketch_path) if firmware_ok else ""

        has_loop = "void loop()" in source
        has_setup = "void setup()" in source
        has_serial = "Serial.begin" in source
        defines = re.findall(r"#define\s+([A-Z0-9_]+)\s+\S+", source)

        diagram_valid = False
        n_parts = n_conns = 0
        if diagram_ok:
            try:
                diagram = read_json(diagram_path)
                diagram_valid = all(k in diagram for k in ("version", "parts", "connections"))
                n_parts = len(diagram.get("parts", []))
                n_conns = len(diagram.get("connections", []))
            except Exception:
                diagram_valid = False

        warnings = []
        if not has_loop:
            warnings.append("No loop() found in firmware.")
        if not has_serial:
            warnings.append("No Serial output detected; static serial transcript will be generic.")

        status = {
            "static_validation_passed": firmware_ok and diagram_valid and has_loop and has_setup,
            "firmware_generated": firmware_ok,
            "diagram_generated": diagram_ok,
            "diagram_valid": diagram_valid,
            "has_setup": has_setup,
            "has_loop": has_loop,
            "has_serial_output": has_serial,
            "num_pin_constants": len(defines),
            "num_diagram_parts": n_parts,
            "num_diagram_connections": n_conns,
            "warnings": warnings,
            "note": "Static pseudo-simulation only; not an electrical simulation.",
        }

        serial = self._synth_serial(source)
        success = status["static_validation_passed"]

        return SimulationResult(
            backend=self.name,
            success=success,
            available=True,
            serial_output=serial,
            status=status,
            message="Static validation completed (no real electrical simulation performed).",
            duration_sec=round(time.time() - start, 4),
        )

    # ------------------------------------------------------------------ #
    def _synth_serial(self, source: str) -> str:
        """Pull the literal strings the sketch prints and replay a few cycles."""
        prints = re.findall(r'(?:Serial\.print(?:ln)?)\(\s*F?\(?\s*"([^"]*)"', source)
        lines = ["[RoboMentor static simulator] Synthesised serial transcript",
                 "[RoboMentor static simulator] (illustrative output, not measured)"]
        startup = next((p for p in prints if "starting" in p.lower()), None)
        if startup:
            lines.append(startup)
        loop_msgs = [p for p in prints if p and "starting" not in p.lower()][:6]
        if not loop_msgs:
            loop_msgs = ["loop tick"]
        for cycle in range(3):
            for msg in loop_msgs:
                lines.append(f"{msg}")
        lines.append("[RoboMentor static simulator] transcript end")
        return "\n".join(lines) + "\n"
