"""Validator registry and the ``run_all`` entry point."""

from __future__ import annotations

from typing import List, Optional

from ..schemas import Circuit, Firmware, PlannerResult, ValidationReport
from .base import Validator
from .code_circuit_validator import CodeCircuitValidator
from .educational_safety_validator import EducationalSafetyValidator
from .pin_validator import PinValidator
from .power_validator import PowerValidator
from .wokwi_validator import WokwiValidator

__all__ = [
    "Validator",
    "PinValidator",
    "PowerValidator",
    "CodeCircuitValidator",
    "WokwiValidator",
    "EducationalSafetyValidator",
    "default_validators",
    "run_all",
]


def default_validators() -> List[Validator]:
    return [
        PinValidator(),
        PowerValidator(),
        CodeCircuitValidator(),
        WokwiValidator(),
        EducationalSafetyValidator(),
    ]


def run_all(circuit: Circuit, firmware: Optional[Firmware] = None,
            plan: Optional[PlannerResult] = None) -> ValidationReport:
    report = ValidationReport()
    for validator in default_validators():
        try:
            report.extend(validator.validate(circuit, firmware, plan))
        except Exception as exc:  # validators must never break the pipeline
            from ..schemas import Severity, ValidationIssue

            report.add(ValidationIssue(
                Severity.WARNING.value,
                "validator_crashed",
                f"Validator '{validator.name}' raised: {exc}",
                validator.name,
                hint="This is a RoboMentor bug; the rest of the report is still valid.",
            ))
    return report
