"""Project planner.

Given a free-text request plus a parsed material list, the planner chooses the
most feasible project *template* and a board.  It is fully deterministic and
needs no LLM — an LLM provider can only *refine* the reasoning summary, never
override feasibility.

The template registry lives here because both :mod:`circuit_generator` and
:mod:`code_generator` consume the same template metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from . import board_profiles
from .schemas import MaterialList, PlannerResult
from .utils import tokenize


# --------------------------------------------------------------------------- #
# Template registry
# --------------------------------------------------------------------------- #
@dataclass
class TemplateSpec:
    id: str
    project_key: str          # short key used in metrics / filenames
    name: str
    keywords: List[str]
    # (part_type, quantity) the template *cannot* work without:
    required: List[Tuple[str, int]] = field(default_factory=list)
    # alternative groups: at least one part from each group is required:
    required_any: List[List[str]] = field(default_factory=list)
    optional: List[str] = field(default_factory=list)
    supported_boards: List[str] = field(default_factory=list)
    difficulty: str = "beginner"
    description: str = ""


TEMPLATES: Dict[str, TemplateSpec] = {
    "arduino_line_follower_v1": TemplateSpec(
        id="arduino_line_follower_v1",
        project_key="line_follower",
        name="Line Follower Robot",
        keywords=["line", "follow", "follower", "track", "tracking", "path", "tape"],
        required=[("ir_line_sensor", 2), ("dc_motor", 2)],
        required_any=[["l298n_motor_driver", "tb6612fng_motor_driver"]],
        optional=["led", "buzzer", "battery_pack", "breadboard"],
        supported_boards=["arduino_uno", "arduino_nano", "arduino_mega",
                          "esp32_devkit_v1", "raspberry_pi_pico", "raspberry_pi_pico_w"],
        difficulty="beginner",
        description="A robot that uses two IR sensors to follow a line on the floor.",
    ),
    "obstacle_avoider_v1": TemplateSpec(
        id="obstacle_avoider_v1",
        project_key="obstacle_avoider",
        name="Obstacle Avoiding Robot",
        keywords=["obstacle", "avoid", "avoider", "ultrasonic", "distance", "collision", "bumper", "maze"],
        required=[("ultrasonic_hc_sr04", 1), ("dc_motor", 2)],
        required_any=[["l298n_motor_driver", "tb6612fng_motor_driver"]],
        optional=["servo_sg90", "led", "buzzer", "battery_pack"],
        supported_boards=["arduino_uno", "arduino_nano", "arduino_mega",
                          "esp32_devkit_v1", "raspberry_pi_pico", "raspberry_pi_pico_w"],
        difficulty="intermediate",
        description="A robot that uses an ultrasonic sensor to detect and steer around obstacles.",
    ),
    "traffic_light_v1": TemplateSpec(
        id="traffic_light_v1",
        project_key="traffic_light",
        name="Smart Traffic Light",
        keywords=["traffic", "light", "signal", "crossing", "intersection", "pedestrian", "stop"],
        required=[("led", 3)],
        optional=["button", "buzzer", "resistor_220"],
        supported_boards=["arduino_uno", "arduino_nano", "arduino_mega",
                          "esp32_devkit_v1", "raspberry_pi_pico", "raspberry_pi_pico_w",
                          "stm32_nucleo_basic"],
        difficulty="beginner",
        description="A traffic-light controller with red/yellow/green LEDs and an optional pedestrian button.",
    ),
    "smart_greenhouse_v1": TemplateSpec(
        id="smart_greenhouse_v1",
        project_key="smart_greenhouse",
        name="Smart Greenhouse / Plant Monitor",
        keywords=["greenhouse", "plant", "garden", "temperature", "humidity", "moisture",
                  "monitor", "soil", "climate", "weather"],
        required=[],
        required_any=[["dht22", "soil_moisture", "ldr"]],
        optional=["oled_i2c", "lcd_16x2", "buzzer", "led", "ldr", "soil_moisture", "dht22"],
        supported_boards=["arduino_uno", "arduino_nano", "arduino_mega",
                          "esp32_devkit_v1", "raspberry_pi_pico", "raspberry_pi_pico_w"],
        difficulty="intermediate",
        description="Monitors temperature/humidity/light and alerts when the plant needs attention.",
    ),
}


def list_templates() -> List[TemplateSpec]:
    return list(TEMPLATES.values())


# --------------------------------------------------------------------------- #
# Scoring
# --------------------------------------------------------------------------- #
def _keyword_score(request: str, spec: TemplateSpec) -> float:
    tokens = set(tokenize(request))
    if not tokens:
        return 0.0
    hits = sum(1 for kw in spec.keywords if kw in tokens)
    return hits / max(len(spec.keywords), 1)


def _material_feasibility(material: MaterialList, spec: TemplateSpec) -> Tuple[float, List[str], List[str], List[str]]:
    """Return (coverage 0..1, missing_required, missing_optional, used_parts)."""
    qty = material.part_quantities()
    missing_required: List[str] = []
    used: List[str] = []

    total_required = 0
    satisfied_required = 0

    for part_type, need in spec.required:
        total_required += 1
        have = qty.get(part_type, 0)
        if have >= need:
            satisfied_required += 1
            used.append(part_type)
        else:
            missing_required.append(f"{part_type} x{need}")

    for group in spec.required_any:
        total_required += 1
        found = next((p for p in group if qty.get(p, 0) > 0), None)
        if found:
            satisfied_required += 1
            used.append(found)
        else:
            missing_required.append(" or ".join(group))

    missing_optional: List[str] = []
    for opt in spec.optional:
        if qty.get(opt, 0) > 0:
            if opt not in used:
                used.append(opt)
        else:
            missing_optional.append(opt)

    coverage = satisfied_required / total_required if total_required else 1.0
    return coverage, missing_required, missing_optional, used


def _pick_board(material: MaterialList, spec: TemplateSpec, requested: str) -> Tuple[str, List[str]]:
    """Choose a board id. Honour an explicit request; otherwise auto-select."""
    warnings: List[str] = []
    available = material.board_types()

    if requested and requested != "auto":
        resolved = board_profiles.resolve_board_id(requested)
        if resolved not in spec.supported_boards:
            warnings.append(
                f"Requested board '{resolved}' is not ideal for this template; using it anyway."
            )
        if available and resolved not in available:
            warnings.append(
                f"Requested board '{resolved}' is not in your material list — assuming you have one."
            )
        return resolved, warnings

    # auto: prefer a board the student owns AND the template supports.
    for b in available:
        if b in spec.supported_boards:
            return b, warnings
    # else first supported board the student owns at all
    if available:
        warnings.append(
            f"No owned board is ideal for this template; defaulting to '{available[0]}'."
        )
        return available[0], warnings
    # else fall back to the template's first supported board
    default = spec.supported_boards[0] if spec.supported_boards else "arduino_uno"
    warnings.append(f"No boards listed in materials; defaulting to '{default}'.")
    return default, warnings


def plan(material: MaterialList, request_text: str, board: str = "auto",
         project_hint: Optional[str] = None) -> PlannerResult:
    """Select the best template + board and produce a structured plan."""
    candidates: List[Dict] = []

    for spec in TEMPLATES.values():
        kw = _keyword_score(request_text, spec)
        coverage, miss_req, miss_opt, used = _material_feasibility(material, spec)
        # feasibility dominates; keywords break ties / boost intent.
        hint_bonus = 0.0
        if project_hint and (project_hint == spec.id or project_hint == spec.project_key):
            hint_bonus = 1.0
        score = 0.6 * coverage + 0.4 * kw + hint_bonus
        candidates.append({
            "template_id": spec.id,
            "project": spec.project_key,
            "name": spec.name,
            "keyword_score": round(kw, 3),
            "material_coverage": round(coverage, 3),
            "score": round(score, 3),
            "missing_required": miss_req,
            "missing_optional": miss_opt,
            "used_parts": used,
            "feasible": len(miss_req) == 0,
        })

    candidates.sort(key=lambda c: (c["feasible"], c["score"]), reverse=True)
    best = candidates[0]
    spec = TEMPLATES[best["template_id"]]

    selected_board, board_warnings = _pick_board(material, spec, board)

    warnings: List[str] = list(board_warnings)
    if not best["feasible"]:
        warnings.append(
            "Selected project is missing required parts; firmware/circuit will be generated "
            "but flagged as INCOMPLETE until you add: " + ", ".join(best["missing_required"])
        )
    if selected_board not in spec.supported_boards:
        warnings.append(f"Board '{selected_board}' support for this template is approximate.")

    # confidence blends material coverage and keyword intent, clamped to [0,1]
    confidence = round(min(1.0, 0.55 * best["material_coverage"] + 0.45 * (best["keyword_score"] or 0.3)
                           + (0.2 if best["feasible"] else 0.0)), 3)

    reasoning = _reasoning_summary(spec, material, selected_board, best)

    return PlannerResult(
        selected_project=spec.project_key,
        selected_board=selected_board,
        confidence=confidence,
        reasoning_summary=reasoning,
        template_id=spec.id,
        used_parts=best["used_parts"],
        missing_required_parts=best["missing_required"],
        missing_optional_parts=best["missing_optional"],
        warnings=warnings,
        candidates=candidates,
    )


def _reasoning_summary(spec: TemplateSpec, material: MaterialList,
                       board: str, best: Dict) -> str:
    have = [p for p in best["used_parts"]]
    parts_str = ", ".join(have) if have else "the available parts"
    base = (
        f"The request best matches a {spec.name}. "
        f"The material list provides {parts_str} on a {board}, which covers "
        f"{int(best['material_coverage'] * 100)}% of the required parts."
    )
    if best["missing_required"]:
        base += " Missing required parts: " + ", ".join(best["missing_required"]) + "."
    return base
