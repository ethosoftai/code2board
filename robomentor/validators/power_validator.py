"""Power / electrical-safety validation.

Checks the things that most often damage hardware or confuse beginners:
common ground, direct motor drive, servo power, 5V sensors on 3.3V boards,
missing LED resistors and missing motor-driver supply.
"""

from __future__ import annotations

from typing import List, Optional

from .. import part_library
from ..schemas import Circuit, Firmware, PlannerResult, ValidationIssue
from .base import Validator


class PowerValidator(Validator):
    name = "power_validator"

    def validate(self, circuit: Circuit, firmware: Optional[Firmware] = None,
                 plan: Optional[PlannerResult] = None) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        board = circuit.board

        # Index connections
        ground_nets = [c for c in circuit.connections if c.net == "ground"]
        comp_by_id = {c.id: c for c in circuit.components}

        # --- common ground -------------------------------------------------
        if circuit.components and not ground_nets:
            issues.append(self.error(
                "no_common_ground",
                "No ground (GND) connections were found. Every component needs a common ground.",
                hint="Connect each component's GND to the board GND.",
            ))

        # --- motor driven directly from a GPIO ----------------------------
        for c in circuit.connections:
            frm = comp_by_id.get(c.from_part)
            to = comp_by_id.get(c.to_part)
            for comp, other_id in ((frm, c.to_part), (to, c.from_part)):
                if comp and comp.part_type == "dc_motor" and other_id == "board":
                    issues.append(self.error(
                        "motor_direct_drive",
                        f"DC motor '{comp.id}' appears wired directly to the board.",
                        hint="Motors must go through a motor driver (L298N/TB6612), never a GPIO pin.",
                    ))

        # --- motor driver external supply ---------------------------------
        drivers = [c for c in circuit.components if "motor_driver" in c.part_type]
        for drv in drivers:
            has_supply = any(
                (c.to_part == drv.id and c.to_pin in ("VCC", "VM")) or
                (c.from_part == drv.id and c.from_pin in ("VCC", "VM"))
                for c in circuit.connections if c.net == "power"
            )
            if not has_supply:
                issues.append(self.warn(
                    "motor_driver_no_external_power",
                    f"Motor driver '{drv.id}' has no external motor supply wired (VCC/VM).",
                    hint="Power motors from a battery pack, not from the board's 5V rail.",
                ))
            issues.append(self.info(
                "motor_driver_supply_note",
                f"Remember: '{drv.id}' needs its own battery for the motors; share GND with the board.",
            ))

        # --- servo power ---------------------------------------------------
        for comp in circuit.components:
            if comp.part_type == "servo_sg90":
                issues.append(self.warn(
                    "servo_power",
                    f"Servo '{comp.id}' can draw 250mA+ on stall.",
                    hint="Power it from the 5V rail/battery, not a logic pin, and share ground.",
                ))

        # --- 5V sensors on a 3.3V board -----------------------------------
        if board.logic_voltage < 5.0:
            for comp in circuit.components:
                try:
                    part = part_library.get_part(comp.part_type)
                except KeyError:
                    continue
                volt = part.power.get("voltage")
                if comp.part_type == "ultrasonic_hc_sr04":
                    issues.append(self.warn(
                        "hcsr04_voltage",
                        f"HC-SR04 ECHO outputs 5V but {board.name} is {board.logic_voltage}V logic.",
                        hint="Add a resistor voltage divider on ECHO (e.g. 1k/2k) to protect the pin.",
                    ))
                elif volt and volt >= 5.0:
                    issues.append(self.warn(
                        "level_mismatch",
                        f"'{comp.id}' is a {volt}V part on a {board.logic_voltage}V board.",
                        hint="Check whether a level shifter is needed for its signal line.",
                    ))

        # --- LED resistor --------------------------------------------------
        for comp in circuit.components:
            if comp.part_type in ("led", "rgb_led"):
                # is there a resistor in series on its anode path?
                anode_conns = [c for c in circuit.connections
                               if (c.to_part == comp.id and c.to_pin in ("anode", "red", "green", "blue"))
                               or (c.from_part == comp.id and c.from_pin in ("anode",))]
                touches_resistor = any(
                    "resistor" in (comp_by_id.get(c.from_part).part_type if comp_by_id.get(c.from_part) else "")
                    or "resistor" in (comp_by_id.get(c.to_part).part_type if comp_by_id.get(c.to_part) else "")
                    for c in anode_conns
                )
                if not touches_resistor:
                    issues.append(self.warn(
                        "led_no_resistor",
                        f"LED '{comp.id}' may be missing a current-limiting resistor.",
                        hint="Add a 220-330 ohm resistor in series to protect the LED and pin.",
                    ))

        return issues
