"""Code agent: generates firmware that matches the circuit's pin map."""

from __future__ import annotations

from .. import code_generator
from ..schemas import Circuit, Firmware, PlannerResult
from .base_agent import BaseAgent


class CodeAgent(BaseAgent):
    name = "code_agent"

    def run(self, plan: PlannerResult, circuit: Circuit) -> Firmware:
        firmware = code_generator.generate_firmware(plan, circuit)
        # The LLM may inspect but not replace validated firmware; heuristic mode
        # returns it unchanged. (We keep firmware deterministic for safety.)
        _ = self.llm.generate_code({"firmware_source": firmware.source})
        self.say(f"generated {firmware.line_count}-line {firmware.language} sketch "
                 f"with {len(firmware.pin_constants)} pin constants")
        return firmware
