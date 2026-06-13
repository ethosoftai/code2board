"""Pin-level validation: do the chosen pins exist and have the right capability?"""

from __future__ import annotations

from typing import List, Optional

from ..schemas import Circuit, Firmware, PlannerResult, ValidationIssue
from .base import Validator

# Constant-name hints about what capability a pin needs.
_PWM_HINTS = ("ENA", "ENB", "PWMA", "PWMB", "SERVO")
_ANALOG_HINTS = ("LDR", "SOIL", "POT", "ANALOG", "AOUT")


class PinValidator(Validator):
    name = "pin_validator"

    def validate(self, circuit: Circuit, firmware: Optional[Firmware] = None,
                 plan: Optional[PlannerResult] = None) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        board = circuit.board
        seen_assignments: dict = {}

        for const, pin in circuit.pin_map.items():
            # exists?
            if not board.has_pin(pin):
                issues.append(self.error(
                    "pin_not_on_board",
                    f"{const} is mapped to pin '{pin}', which does not exist on {board.name}.",
                    hint=f"Valid pins include: {', '.join(board.all_pins()[:12])}...",
                ))
                continue

            # PWM capability
            if any(h in const for h in _PWM_HINTS) and not board.is_pwm(pin):
                issues.append(self.error(
                    "pwm_required",
                    f"{const} needs a PWM-capable pin but '{pin}' is not PWM on {board.name}.",
                    hint=f"PWM pins: {', '.join(board.pwm_pins)}",
                ))

            # Analog capability
            if any(h in const for h in _ANALOG_HINTS) and not board.is_analog(pin):
                issues.append(self.error(
                    "analog_required",
                    f"{const} reads an analog value but '{pin}' is not an analog input on {board.name}.",
                    hint=f"Analog pins: {', '.join(board.analog_pins)}",
                ))

            # duplicate exclusive assignment
            if pin in seen_assignments:
                issues.append(self.error(
                    "pin_conflict",
                    f"Pin '{pin}' is assigned to both {seen_assignments[pin]} and {const}.",
                    hint="Each signal pin can drive only one function.",
                ))
            else:
                seen_assignments[pin] = const

            # serial pin warning
            if pin in board.uart_pins.values():
                issues.append(self.warn(
                    "serial_pin_used",
                    f"{const} uses pin '{pin}', which is the hardware serial {board.uart_pins}.",
                    hint="This can interfere with Serial debugging/upload. Move it if possible.",
                ))

        # I2C sanity: if I2C constants present, ensure they match board's I2C pins
        if "I2C_SDA" in circuit.pin_map:
            if circuit.pin_map["I2C_SDA"] != board.i2c_pins.get("sda"):
                issues.append(self.warn(
                    "i2c_pin_mismatch",
                    f"I2C_SDA '{circuit.pin_map['I2C_SDA']}' differs from the board's hardware "
                    f"SDA '{board.i2c_pins.get('sda')}'.",
                    hint="Most boards only do hardware I2C on specific pins.",
                ))

        if board.wokwi_support == "none":
            issues.append(self.info(
                "board_pinout_approximate",
                f"{board.name} pin mapping is APPROXIMATE; verify against your exact variant.",
            ))
        return issues
