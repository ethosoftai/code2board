"""Base class for validators.

A validator inspects some combination of (circuit, firmware, board, plan) and
returns a list of :class:`~robomentor.schemas.ValidationIssue`.  Validators must
never raise on bad input — they report problems as issues instead, so the
pipeline always produces a report.
"""

from __future__ import annotations

from typing import List, Optional

from ..schemas import (
    Circuit,
    Firmware,
    PlannerResult,
    Severity,
    ValidationIssue,
)


class Validator:
    name: str = "base"

    def validate(
        self,
        circuit: Circuit,
        firmware: Optional[Firmware] = None,
        plan: Optional[PlannerResult] = None,
    ) -> List[ValidationIssue]:  # pragma: no cover - interface
        raise NotImplementedError

    # convenience constructors ------------------------------------------- #
    def error(self, code: str, message: str, hint: str = "") -> ValidationIssue:
        return ValidationIssue(Severity.ERROR.value, code, message, self.name, hint)

    def warn(self, code: str, message: str, hint: str = "") -> ValidationIssue:
        return ValidationIssue(Severity.WARNING.value, code, message, self.name, hint)

    def info(self, code: str, message: str, hint: str = "") -> ValidationIssue:
        return ValidationIssue(Severity.INFO.value, code, message, self.name, hint)
