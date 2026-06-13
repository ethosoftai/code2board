"""Circuit agent: builds the internal circuit model for the selected template."""

from __future__ import annotations

from .. import board_profiles, circuit_generator
from ..schemas import Circuit, MaterialList, PlannerResult
from .base_agent import BaseAgent


class CircuitAgent(BaseAgent):
    name = "circuit_agent"

    def run(self, plan: PlannerResult, material: MaterialList, seed: int = 1337) -> Circuit:
        board = board_profiles.get_board(plan.selected_board)
        circuit = circuit_generator.build_circuit(plan, material, board=board, seed=seed)
        self.say(f"built circuit with {len(circuit.components)} components and "
                 f"{len(circuit.connections)} connections")
        return circuit
