"""Educational safety validator.

Emits age-appropriate, practical safety reminders for a high-school audience.
It never contains dangerous instructions — only cautions and good practice.
"""

from __future__ import annotations

from typing import List, Optional

from ..schemas import Circuit, Firmware, PlannerResult, ValidationIssue
from .base import Validator


class EducationalSafetyValidator(Validator):
    name = "educational_safety_validator"

    def validate(self, circuit: Circuit, firmware: Optional[Firmware] = None,
                 plan: Optional[PlannerResult] = None) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        types = {c.part_type for c in circuit.components}

        if any("motor" in t for t in types):
            issues.append(self.info(
                "safety_motors",
                "Motors and batteries can deliver a lot of current. Disconnect power before "
                "rewiring, and keep fingers/hair away from spinning wheels.",
            ))
        if "battery_pack" in types:
            issues.append(self.info(
                "safety_battery",
                "Double-check battery polarity before connecting. A reversed battery can damage "
                "parts or overheat. Never short the battery terminals.",
            ))
        if "servo_sg90" in types:
            issues.append(self.info(
                "safety_servo",
                "Don't force the servo horn by hand while powered — it can strip the gears.",
            ))
        if any(t in types for t in ("led", "rgb_led")):
            issues.append(self.info(
                "safety_led",
                "Always use a resistor with an LED. Without it the LED (and the pin) can be damaged.",
            ))

        # Always-on reminders
        issues.append(self.info(
            "safety_short_circuit",
            "Build with the power OFF, then double-check there are no accidental wire-to-wire "
            "shorts before powering up.",
        ))
        issues.append(self.info(
            "sim_vs_hardware",
            "Simulation is a guide, not a guarantee. Real components have tolerances, contact "
            "resistance and current limits that a simulator may not model. Test gently on hardware.",
        ))
        return issues
