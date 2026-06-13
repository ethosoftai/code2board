"""Cross-check the firmware against the circuit.

Ensures the two artifacts agree: every pin constant in the sketch exists in the
circuit pin map (and vice versa), and required libraries for I2C/servo parts are
included.
"""

from __future__ import annotations

import re
from typing import List, Optional

from .. import part_library
from ..schemas import Circuit, Firmware, PlannerResult, ValidationIssue
from .base import Validator

_DEFINE_RE = re.compile(r"#define\s+([A-Z0-9_]+)\s+(\S+)")


class CodeCircuitValidator(Validator):
    name = "code_circuit_validator"

    def validate(self, circuit: Circuit, firmware: Optional[Firmware] = None,
                 plan: Optional[PlannerResult] = None) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        if firmware is None:
            issues.append(self.info("no_firmware", "No firmware supplied; skipping code-circuit check."))
            return issues

        defines = {m.group(1): m.group(2) for m in _DEFINE_RE.finditer(firmware.source)}

        # Every circuit pin constant must appear as a #define with the same pin.
        for const, pin in circuit.pin_map.items():
            if const not in defines:
                issues.append(self.error(
                    "missing_define",
                    f"Circuit constant '{const}' (pin {pin}) is not #defined in the firmware.",
                    hint="The firmware and diagram must reference the same pin names.",
                ))
            elif defines[const] != pin:
                issues.append(self.error(
                    "pin_value_mismatch",
                    f"'{const}' is pin {pin} in the circuit but {defines[const]} in the firmware.",
                ))

        # Every firmware pin define should map to a real circuit pin (unless tunable consts).
        for const, value in defines.items():
            if const in ("SELF_TEST", "DHTTYPE"):
                continue
            # only treat it as a pin if it matches a board pin token
            looks_like_pin = circuit.board.has_pin(value)
            if looks_like_pin and const not in circuit.pin_map:
                issues.append(self.warn(
                    "extra_define",
                    f"Firmware defines pin constant '{const}'={value} not present in the circuit.",
                    hint="Either wire it in the diagram or remove it from the sketch.",
                ))

        # Library check: I2C/servo/dht parts need their library included.
        src = firmware.source
        for comp in circuit.components:
            try:
                part = part_library.get_part(comp.part_type)
            except KeyError:
                continue
            for lib in part.libraries:
                token = lib.split()[0]  # crude include marker
                if token not in src and token.lower() not in src.lower():
                    issues.append(self.warn(
                        "missing_library",
                        f"Part '{comp.id}' usually needs the '{lib}' library, not found in the sketch.",
                        hint=f"Add #include for {lib} (install it in the Arduino Library Manager).",
                    ))

        # Wokwi id sanity for components
        for comp in circuit.components:
            if comp.wokwi_id is None:
                issues.append(self.info(
                    "no_wokwi_id",
                    f"Component '{comp.id}' ({comp.part_type}) has no known Wokwi part id; "
                    "simulation support is partial.",
                ))

        return issues
