"""Debug agent: attempts to automatically repair pin-level validation errors.

If validation finds a pin that doesn't exist, lacks PWM/analog capability, or
collides with another assignment, the debug agent remaps that firmware constant
to a valid free pin and rewrites the matching wires. It then signals that the
firmware should be regenerated so code and circuit stay in sync.

The deterministic generators usually produce valid circuits already, so this
agent is a safety net that makes the system robust on exotic board/material
combinations.
"""

from __future__ import annotations

from typing import List, Tuple

from ..circuit_generator import PinAllocator
from ..schemas import Circuit, ValidationReport
from .base_agent import BaseAgent

_PWM_HINTS = ("ENA", "ENB", "PWMA", "PWMB", "SERVO")
_ANALOG_HINTS = ("LDR", "SOIL", "POT", "ANALOG", "AOUT")


def _kind_for(const: str) -> str:
    if any(h in const for h in _PWM_HINTS):
        return "pwm"
    if any(h in const for h in _ANALOG_HINTS):
        return "analog"
    return "digital"


class DebugAgent(BaseAgent):
    name = "debug_agent"

    def needs_fixing(self, report: ValidationReport) -> bool:
        fixable = {"pin_not_on_board", "pwm_required", "analog_required", "pin_conflict"}
        return any(i.code in fixable for i in report.errors)

    def fix(self, circuit: Circuit) -> Tuple[Circuit, List[str]]:
        """Remap invalid/conflicting pins in-place. Returns (circuit, changes)."""
        board = circuit.board
        alloc = PinAllocator(board)
        changes: List[str] = []

        # First pass: keep valid, unique, capability-correct assignments.
        taken: set = set()
        keep: dict = {}
        for const, pin in circuit.pin_map.items():
            kind = _kind_for(const)
            valid = (board.has_pin(pin) and pin not in taken
                     and (kind != "pwm" or board.is_pwm(pin))
                     and (kind != "analog" or board.is_analog(pin)))
            if valid:
                keep[const] = pin
                taken.add(pin)

        # Pre-load allocator with the kept pins so it won't reissue them.
        alloc.used |= taken

        # Second pass: reassign the rest.
        for const, old_pin in list(circuit.pin_map.items()):
            if const in keep:
                continue
            kind = _kind_for(const)
            new_pin = alloc.take(kind=kind, output=(kind != "analog"))
            circuit.pin_map[const] = new_pin
            changes.append(f"{const}: {old_pin} -> {new_pin} ({kind})")
            # rewrite matching wires on the board endpoint
            for conn in circuit.connections:
                if conn.from_part == "board" and conn.from_pin == old_pin:
                    conn.from_pin = new_pin
                if conn.to_part == "board" and conn.to_pin == old_pin:
                    conn.to_pin = new_pin

        for const, pin in keep.items():
            circuit.pin_map[const] = pin

        if changes:
            self.say("remapped pins -> " + "; ".join(changes))
        else:
            self.say("no fixable pin issues found")
        return circuit, changes
