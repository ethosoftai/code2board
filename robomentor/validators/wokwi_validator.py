"""Validate the generated Wokwi ``diagram.json`` structure.

Operates on the exported diagram dict (not the internal circuit) so it catches
real export bugs: missing keys, dangling connection endpoints and unknown part
ids.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..circuit_generator import to_wokwi_diagram
from ..schemas import Circuit, Firmware, PlannerResult, ValidationIssue
from .base import Validator


class WokwiValidator(Validator):
    name = "wokwi_validator"

    def validate(self, circuit: Circuit, firmware: Optional[Firmware] = None,
                 plan: Optional[PlannerResult] = None) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        diagram = to_wokwi_diagram(circuit)
        issues.extend(self.validate_diagram(diagram))
        return issues

    def validate_diagram(self, diagram: Dict[str, Any]) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []

        for key in ("version", "author", "parts", "connections"):
            if key not in diagram:
                issues.append(self.error(
                    "wokwi_missing_key",
                    f"diagram.json is missing required key '{key}'.",
                ))

        parts = diagram.get("parts", [])
        part_ids = set()
        for p in parts:
            pid = p.get("id")
            if not pid:
                issues.append(self.error("wokwi_part_no_id", "A part in diagram.json has no id."))
                continue
            part_ids.add(pid)
            ptype = p.get("type", "")
            if ptype.startswith("unknown-"):
                issues.append(self.warn(
                    "wokwi_unknown_part",
                    f"Part '{pid}' ({ptype}) has no known Wokwi type — simulation support is PARTIAL.",
                    hint="Local renders still work; full Wokwi sim may need a substitute part.",
                ))

        for conn in diagram.get("connections", []):
            if not isinstance(conn, list) or len(conn) < 2:
                issues.append(self.error("wokwi_bad_connection",
                                         f"Malformed connection entry: {conn!r}"))
                continue
            for endpoint in conn[:2]:
                if not isinstance(endpoint, str) or ":" not in endpoint:
                    issues.append(self.error(
                        "wokwi_bad_endpoint",
                        f"Connection endpoint '{endpoint}' is not in 'partId:pin' form.",
                    ))
                    continue
                part = endpoint.split(":", 1)[0]
                if part not in part_ids:
                    issues.append(self.error(
                        "wokwi_dangling_endpoint",
                        f"Connection references part '{part}' which is not in 'parts'.",
                    ))

        return issues
