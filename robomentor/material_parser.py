"""Parse a student's material list (JSON, or YAML when PyYAML is available).

The parser is forgiving: it accepts loose part names (resolved via the part
library aliases), missing quantities (default 1), and missing sections.  It
records any normalisation/unknown-part issues as warnings rather than failing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from . import board_profiles, part_library
from .schemas import BoardEntry, MaterialList, PartEntry
from .utils import HAS_YAML


def _load_raw(path: Path) -> Dict[str, Any]:
    text = Path(path).read_text(encoding="utf-8")
    suffix = Path(path).suffix.lower()
    if suffix in (".yaml", ".yml"):
        if not HAS_YAML:
            raise RuntimeError(
                f"'{path}' is YAML but PyYAML is not installed. "
                "Install with `pip install PyYAML` or provide a JSON file."
            )
        import yaml  # type: ignore

        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("Material file must contain a JSON/YAML object at the top level.")
    return data


def parse_material_dict(data: Dict[str, Any]) -> Tuple[MaterialList, List[str]]:
    """Parse an already-loaded material dict. Returns (MaterialList, warnings)."""
    warnings: List[str] = []

    student_level = str(data.get("student_level", "beginner")).lower()

    boards: List[BoardEntry] = []
    for entry in data.get("available_boards", []) or []:
        if isinstance(entry, str):
            entry = {"type": entry, "quantity": 1}
        btype = board_profiles.resolve_board_id(str(entry.get("type", "")))
        qty = int(entry.get("quantity", 1) or 1)
        if btype not in board_profiles.board_ids():
            warnings.append(f"Unknown board '{entry.get('type')}' — keeping it but it may not be usable.")
        boards.append(BoardEntry(type=btype, quantity=qty))

    parts: List[PartEntry] = []
    for entry in data.get("parts", []) or []:
        if isinstance(entry, str):
            entry = {"type": entry, "quantity": 1}
        raw_type = str(entry.get("type", ""))
        ptype = part_library.resolve_part_type(raw_type)
        qty = int(entry.get("quantity", 1) or 1)
        if not part_library.has_part(ptype):
            warnings.append(f"Unknown part '{raw_type}' — ignored by the planner (kept in raw list).")
        parts.append(PartEntry(type=ptype, quantity=qty))

    constraints = data.get("constraints", {}) or {}
    if not isinstance(constraints, dict):
        warnings.append("'constraints' was not an object — ignoring it.")
        constraints = {}

    material = MaterialList(
        student_level=student_level,
        available_boards=boards,
        parts=parts,
        constraints=constraints,
        raw=data,
    )
    return material, warnings


def parse_material_file(path: Path) -> Tuple[MaterialList, List[str]]:
    data = _load_raw(Path(path))
    return parse_material_dict(data)
