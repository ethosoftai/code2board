"""Agents package + the top-level RoboMentor generation pipeline.

``run_generation(config)`` is the single entry point the CLI calls. It wires the
individual agents together, writes every artifact, runs validation (with one
automatic debug/repair retry), simulates, renders and reports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .. import material_parser, metrics as metrics_mod, project_io, report as report_mod, validators
from ..config import RunConfig
from ..llm import get_provider
from ..schemas import (
    Circuit,
    Firmware,
    MaterialList,
    PlannerResult,
    SimulationResult,
    ValidationReport,
)
from ..simulators import simulate
from ..renderers import circuit_plotter, graphviz_renderer
from .base_agent import AgentLog
from .circuit_agent import CircuitAgent
from .code_agent import CodeAgent
from .debug_agent import DebugAgent
from .explanation_agent import ExplanationAgent
from .planner_agent import PlannerAgent

__all__ = [
    "PlannerAgent", "CircuitAgent", "CodeAgent", "DebugAgent", "ExplanationAgent",
    "GenerationResult", "run_generation",
]


@dataclass
class GenerationResult:
    out_dir: Path
    plan: PlannerResult
    circuit: Circuit
    firmware: Firmware
    validation: ValidationReport
    sim: SimulationResult
    renders: Dict[str, str] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    messages: List[str] = field(default_factory=list)
    agent_log: List[str] = field(default_factory=list)
    material_warnings: List[str] = field(default_factory=list)


def _resolve_request_text(cfg: RunConfig) -> str:
    if cfg.request_text:
        return cfg.request_text
    if cfg.request_path and Path(cfg.request_path).exists():
        return Path(cfg.request_path).read_text(encoding="utf-8")
    return ""


def run_generation(cfg: RunConfig) -> GenerationResult:
    log = AgentLog()
    messages: List[str] = []
    out_dir = Path(cfg.out_dir)

    # --- inputs --------------------------------------------------------------
    if cfg.materials_path:
        material, mat_warnings = material_parser.parse_material_file(Path(cfg.materials_path))
    else:
        material, mat_warnings = MaterialList(), []
    request_text = _resolve_request_text(cfg)

    llm = get_provider(cfg.llm_provider)
    messages.append(f"LLM provider: {llm.name}"
                    + ("" if llm.name == cfg.llm_provider else f" (requested '{cfg.llm_provider}', "
                       "fell back to offline heuristic)"))

    # --- plan ----------------------------------------------------------------
    plan = PlannerAgent(llm, log).run(material, request_text, board=cfg.board,
                                      project_hint=cfg.project_hint)
    messages.append(f"Planner selected '{plan.selected_project}' on '{plan.selected_board}' "
                    f"(confidence {plan.confidence:.2f}).")

    # --- circuit + code ------------------------------------------------------
    circuit = CircuitAgent(llm, log).run(plan, material, seed=cfg.seed)
    firmware = CodeAgent(llm, log).run(plan, circuit)

    # --- validate (with one automatic repair retry) --------------------------
    validation = validators.run_all(circuit, firmware, plan)
    debug = DebugAgent(llm, log)
    if not validation.passed and debug.needs_fixing(validation):
        messages.append("Validation found fixable pin errors — debug agent is repairing the circuit.")
        circuit, changes = debug.fix(circuit)
        from .. import code_generator
        firmware = code_generator.generate_firmware(plan, circuit)
        validation = validators.run_all(circuit, firmware, plan)
        if changes:
            messages.append("Debug agent remapped: " + "; ".join(changes))

    # --- write core artifacts ------------------------------------------------
    project_io.write_plan(out_dir, plan)
    project_io.write_bom(out_dir, circuit)
    project_io.write_circuit_artifacts(out_dir, circuit)
    project_io.write_firmware(out_dir, firmware)
    project_io.write_validation(out_dir, validation)
    messages.append("Files generated successfully.")
    if validation.passed:
        messages.append(f"Static validation completed: PASSED "
                        f"({len(validation.warnings)} warnings, {len(validation.infos)} notes).")
    else:
        messages.append(f"Static validation completed: {len(validation.errors)} errors remain "
                        "(see validation/validation_report.md).")

    # --- simulate ------------------------------------------------------------
    sim = simulate(out_dir, mode=cfg.simulate, timeout_sec=cfg.timeout_sec)
    project_io.write_simulation_logs(out_dir, sim)
    if not sim.available and sim.backend in ("wokwi_cli", "none"):
        messages.append("Simulation skipped because Wokwi CLI was not found; "
                        "local static validation was used instead.")
    else:
        messages.append(f"Simulation backend: {sim.backend} "
                        f"({'success' if sim.success else 'fallback/partial'}).")

    # --- renders -------------------------------------------------------------
    renders: Dict[str, str] = {}
    if cfg.wants_render:
        renders.update(circuit_plotter.render_all(circuit, project_io.paths(out_dir)["renders"],
                                                  level=cfg.render))
        renders.update(graphviz_renderer.render_graphviz(circuit, project_io.paths(out_dir)["renders"]))
        messages.append(f"Renders generated: {len(renders)} files in renders/.")
    else:
        messages.append("Rendering skipped (--render none).")

    # --- explanation + reports ----------------------------------------------
    explanation = ExplanationAgent(llm, log).run(plan, circuit)
    report_mod.write_reports(plan, circuit, firmware, validation, sim, renders, explanation,
                             out_dir, llm_provider=llm.name)
    messages.append("Report written: report/report.md, report/report.html, "
                    "report/educational_explanation.md.")

    # --- metrics -------------------------------------------------------------
    metrics = metrics_mod.build_metrics(plan, circuit, firmware, validation, sim, renders)
    project_io.write_metrics(out_dir, metrics)

    return GenerationResult(
        out_dir=out_dir, plan=plan, circuit=circuit, firmware=firmware,
        validation=validation, sim=sim, renders=renders, metrics=metrics,
        messages=messages, agent_log=log.entries, material_warnings=mat_warnings,
    )
