"""Explanation agent: builds the student-facing educational write-up.

Produces learning objectives, a troubleshooting checklist and wiring steps for
the project, then asks the LLM provider to turn them into a friendly Markdown
explanation (heuristic mode does this fully offline).
"""

from __future__ import annotations

from typing import Dict, List

from ..schemas import Circuit, PlannerResult
from .base_agent import BaseAgent

_OBJECTIVES: Dict[str, List[str]] = {
    "line_follower": [
        "Read digital sensors with digitalRead().",
        "Understand how two sensors give a robot left/right awareness.",
        "Control DC motor direction and speed with an H-bridge and PWM.",
        "Write simple if/else decision logic inside loop().",
        "Use the Serial Monitor to debug a robot's decisions.",
    ],
    "obstacle_avoider": [
        "Measure distance with an ultrasonic sensor and pulseIn().",
        "Convert echo time into centimetres.",
        "Make a robot react to its environment (stop, reverse, turn).",
        "Tune thresholds and observe the effect.",
    ],
    "traffic_light": [
        "Drive multiple LEDs with current-limiting resistors.",
        "Sequence outputs with timing (delay / state changes).",
        "Read a button safely with INPUT_PULLUP.",
        "Model a real-world system (a traffic intersection) in code.",
    ],
    "smart_greenhouse": [
        "Read environmental sensors (temperature, humidity, light, moisture).",
        "Use analog inputs and thresholds to make decisions.",
        "Drive an alert (LED/buzzer) when a condition is met.",
        "Respect sensor timing limits (e.g. DHT22 every 2s).",
    ],
}

_TROUBLESHOOTING: Dict[str, List[str]] = {
    "line_follower": [
        "If the robot spins in place, swap the two motor wires or flip a motor's direction in code.",
        "If it ignores the line, adjust the IR sensor potentiometer and check ON_LINE matches your module.",
        "If a wheel doesn't move, check the ENA/ENB PWM wiring and the motor driver power.",
        "Confirm there is a common ground between Arduino, sensors and driver.",
    ],
    "obstacle_avoider": [
        "If distance always reads 999, check TRIG/ECHO wiring and the pulseIn timeout.",
        "On a 3.3V board, verify the ECHO voltage divider is present.",
        "If the robot never stops, lower STOP_DISTANCE_CM and re-test.",
    ],
    "traffic_light": [
        "If an LED never lights, check its resistor and that the long leg (anode) faces the pin.",
        "If colours are swapped, re-check which pin goes to which LED.",
        "If the button does nothing, confirm INPUT_PULLUP and that it ties to GND when pressed.",
    ],
    "smart_greenhouse": [
        "If readings are 'nan', check the DHT data pin and that you wait 2s between reads.",
        "Calibrate analog thresholds against real dry/wet readings from your probe.",
        "If the display is blank, verify the I2C address and SDA/SCL wiring.",
    ],
}


class ExplanationAgent(BaseAgent):
    name = "explanation_agent"

    def learning_objectives(self, project: str) -> List[str]:
        return _OBJECTIVES.get(project, ["Build, wire and program a working microcontroller project."])

    def troubleshooting(self, project: str) -> List[str]:
        base = _TROUBLESHOOTING.get(project, [])
        return base + ["Re-run `robomentor validate` after any wiring change."]

    def wiring_steps(self, circuit: Circuit) -> List[str]:
        steps: List[str] = []
        for c in circuit.connections:
            verb = {"power": "Power", "ground": "Ground", "i2c": "I2C", "pwm": "PWM signal"}.get(
                c.net, "Connect")
            steps.append(f"{verb}: {c.from_part} {c.from_pin} → {c.to_part} {c.to_pin}"
                         + (f"  ({c.note})" if c.note else ""))
        return steps

    def run(self, plan: PlannerResult, circuit: Circuit) -> Dict:
        objectives = self.learning_objectives(plan.selected_project)
        troubleshooting = self.troubleshooting(plan.selected_project)
        steps = self.wiring_steps(circuit)

        context = {
            "project_name": plan.selected_project.replace("_", " ").title(),
            "board_name": circuit.board.name,
            "used_parts": [c.label for c in circuit.components],
            "learning_objectives": objectives,
            "wiring_steps": steps,
        }
        explanation_md = self.llm.generate_explanation(context)
        self.say("generated educational explanation")
        return {
            "explanation_md": explanation_md,
            "learning_objectives": objectives,
            "troubleshooting": troubleshooting,
            "wiring_steps": steps,
        }
