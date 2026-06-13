"""Assemble the report context and write report.md / report.html /
educational_explanation.md."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from . import circuit_generator
from .project_io import paths
from .renderers import html_report, markdown_report
from .schemas import Circuit, Firmware, PlannerResult, SimulationResult, ValidationReport
from .utils import ensure_dir, write_text


def _bom_rows(circuit: Circuit) -> List[Dict[str, str]]:
    from . import part_library

    rows = []
    for c in circuit.components:
        try:
            note = part_library.get_part(c.part_type).explanation
        except KeyError:
            note = ""
        rows.append({"component": c.label, "part_type": c.part_type,
                     "category": c.category, "note": note})
    return rows


def _md_to_html(md: str) -> str:
    """Tiny, dependency-free Markdown→HTML for the explanation block."""
    html: List[str] = []
    in_list = False
    for raw in md.splitlines():
        line = raw.rstrip()
        # inline bold/code
        line_html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", line)
        line_html = re.sub(r"`(.+?)`", r"<code>\1</code>", line_html)
        if line.startswith("### "):
            _close_list(html, in_list); in_list = False
            html.append(f"<h3>{line_html[4:]}</h3>")
        elif line.startswith("## "):
            _close_list(html, in_list); in_list = False
            html.append(f"<h2 style='color:inherit'>{line_html[3:]}</h2>")
        elif line.startswith("# "):
            _close_list(html, in_list); in_list = False
            html.append(f"<h2 style='color:inherit'>{line_html[2:]}</h2>")
        elif line.startswith("- "):
            if not in_list:
                html.append("<ul>"); in_list = True
            html.append(f"<li>{line_html[2:]}</li>")
        elif re.match(r"^\d+\.\s", line):
            if not in_list:
                html.append("<ul>"); in_list = True
            html.append(f"<li>{re.sub(chr(94)+r'\d+\.\s', '', line_html)}</li>")
        elif not line.strip():
            _close_list(html, in_list); in_list = False
        else:
            _close_list(html, in_list); in_list = False
            html.append(f"<p>{line_html}</p>")
    _close_list(html, in_list)
    return "\n".join(html)


def _close_list(html: List[str], in_list: bool) -> None:
    if in_list:
        html.append("</ul>")


def _relativize_for_report(artifacts: Dict[str, str], out_dir: Path) -> Dict[str, str]:
    """Rewrite render paths so they resolve from report/report.html."""
    rel: Dict[str, str] = {}
    report_dir = paths(out_dir)["report"]
    for name, path in artifacts.items():
        try:
            rel[name] = Path(path).resolve().relative_to(report_dir.resolve().parent).as_posix()
            rel[name] = "../" + rel[name] if not rel[name].startswith("..") else rel[name]
        except Exception:
            # fall back to a simple ../renders/<file>
            rel[name] = "../renders/" + Path(path).name
    return rel


def build_context(plan: PlannerResult, circuit: Circuit, firmware: Firmware,
                  validation: ValidationReport, sim: SimulationResult,
                  renders: Dict[str, str], explanation: Dict[str, Any],
                  out_dir: Path, llm_provider: str = "heuristic") -> Dict[str, Any]:
    project_title = plan.selected_project.replace("_", " ").title()
    artifacts_rel = _relativize_for_report(renders, out_dir)
    # include key file artifacts too
    artifacts_rel.update({
        "firmware": "../firmware/sketch.ino",
        "diagram_json": "../simulation/diagram.json",
        "wiring_table_csv": "../wiring_table.csv",
        "validation_report": "../validation/validation_report.md",
    })

    return {
        "title": f"{project_title} — RoboMentor project",
        "project_name": project_title,
        "board_name": circuit.board.name,
        "llm_provider": llm_provider,
        "plan": plan.to_dict(),
        "bom": _bom_rows(circuit),
        "wiring_rows": circuit_generator.wiring_table(circuit),
        "firmware_path": "firmware/sketch.ino",
        "firmware_lines": firmware.line_count,
        "firmware_libraries": firmware.libraries,
        "firmware_explanation": _firmware_explanation(circuit, firmware),
        "sim": sim.to_dict(),
        "validation": validation.to_dict(),
        "warnings": plan.warnings,
        "learning_objectives": explanation.get("learning_objectives", []),
        "troubleshooting": explanation.get("troubleshooting", []),
        "explanation_md": explanation.get("explanation_md", ""),
        "explanation_html": _md_to_html(explanation.get("explanation_md", "")),
        "artifacts": artifacts_rel,
    }


def _firmware_explanation(circuit: Circuit, firmware: Firmware) -> str:
    consts = ", ".join(f"`{k}`→`{v}`" for k, v in list(firmware.pin_constants.items())[:8])
    return (f"The sketch defines {len(firmware.pin_constants)} pin constants ({consts}...), "
            "each matching a wire in the diagram. It reads its inputs, decides what to do, and "
            "drives its outputs inside `loop()`, printing debug messages over Serial at 9600 baud. "
            "Set `SELF_TEST` to 1 to check the wiring before running the full program.")


def write_reports(plan: PlannerResult, circuit: Circuit, firmware: Firmware,
                  validation: ValidationReport, sim: SimulationResult,
                  renders: Dict[str, str], explanation: Dict[str, Any],
                  out_dir: Path, llm_provider: str = "heuristic") -> Dict[str, Path]:
    p = paths(out_dir)
    ensure_dir(p["report"])
    ctx = build_context(plan, circuit, firmware, validation, sim, renders, explanation,
                        out_dir, llm_provider)

    out: Dict[str, Path] = {}
    out["report_md"] = write_text(p["report"] / "report.md", markdown_report.build_markdown(ctx))
    out["report_html"] = write_text(p["report"] / "report.html", html_report.build_html(ctx))
    out["explanation_md"] = write_text(p["report"] / "educational_explanation.md",
                                       explanation.get("explanation_md", ""))
    return out
