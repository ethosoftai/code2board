"""Build the research/demo metrics record (``metrics.json``)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from .schemas import Circuit, Firmware, PlannerResult, SimulationResult, ValidationReport


def build_metrics(plan: PlannerResult, circuit: Circuit, firmware: Firmware,
                  validation: ValidationReport, sim: SimulationResult,
                  renders: Dict[str, str]) -> Dict[str, Any]:
    return {
        "project_type": plan.selected_project,
        "template_id": plan.template_id,
        "board": plan.selected_board,
        "planner_confidence": plan.confidence,
        "num_parts_used": len(circuit.components),
        "num_connections": len(circuit.connections),
        "num_pin_constants": len(circuit.pin_map),
        "num_validation_errors": len(validation.errors),
        "num_validation_warnings": len(validation.warnings),
        "num_validation_infos": len(validation.infos),
        "validation_passed": validation.passed,
        "simulation_backend": sim.backend,
        "simulation_available": sim.available,
        "simulation_success": sim.success,
        "firmware_language": firmware.language,
        "firmware_lines": firmware.line_count,
        "diagram_generated": True,
        "renders_generated": bool(renders),
        "num_renders": len(renders),
        "missing_required_parts": plan.missing_required_parts,
        "missing_optional_parts": plan.missing_optional_parts,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
