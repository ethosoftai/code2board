"""Core data structures for RoboMentor.

Everything here uses plain :mod:`dataclasses` so RoboMentor has **zero hard
dependencies**.  Each dataclass exposes a ``to_dict`` method so it can be
serialized to JSON deterministically (used for artifacts, metrics and tests).

If Pydantic is installed it is *not* required; dataclasses keep the project
runnable in a bare Python 3.10+ environment.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #
class Severity(str, Enum):
    """Severity levels for validation issues."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class StudentLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


# --------------------------------------------------------------------------- #
# Hardware description
# --------------------------------------------------------------------------- #
@dataclass
class BoardProfile:
    """Description of a supported microcontroller board.

    Pin numbers are stored as the *labels a student types in firmware* (e.g.
    ``"2"`` for Arduino digital pin 2, ``"A0"`` for analog 0, ``"GP15"`` for a
    Pico pin).  Where the real hardware behaviour is uncertain it is flagged in
    ``notes`` and the validators surface an "approximate" warning.
    """

    id: str
    name: str
    mcu: str
    logic_voltage: float
    digital_pins: List[str] = field(default_factory=list)
    analog_pins: List[str] = field(default_factory=list)
    pwm_pins: List[str] = field(default_factory=list)
    i2c_pins: Dict[str, str] = field(default_factory=dict)  # {"sda": "...", "scl": "..."}
    spi_pins: Dict[str, str] = field(default_factory=dict)  # mosi/miso/sck/ss
    uart_pins: Dict[str, str] = field(default_factory=dict)  # {"tx": "...", "rx": "..."}
    power_pins: List[str] = field(default_factory=list)      # e.g. ["5V", "3V3", "GND", "VIN"]
    languages: List[str] = field(default_factory=list)       # ["arduino_cpp", "micropython", ...]
    wokwi_id: Optional[str] = None
    wokwi_support: str = "partial"  # "full" | "partial" | "none"
    safe_current_note: str = ""
    notes: List[str] = field(default_factory=list)

    # ------------------------------------------------------------------ #
    def all_pins(self) -> List[str]:
        """Every named GPIO/analog pin on the board (no power rails)."""
        seen: List[str] = []
        for p in self.digital_pins + self.analog_pins:
            if p not in seen:
                seen.append(p)
        return seen

    def has_pin(self, pin: str) -> bool:
        return pin in self.all_pins() or pin in self.power_pins

    def is_pwm(self, pin: str) -> bool:
        return pin in self.pwm_pins

    def is_analog(self, pin: str) -> bool:
        return pin in self.analog_pins

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PartProfile:
    """Metadata about a single electronic part (sensor, actuator, passive...)."""

    type: str
    name: str
    category: str  # "sensor" | "actuator" | "passive" | "power" | "board_support" | "display"
    required_pins: List[str] = field(default_factory=list)   # logical pin names on the part
    optional_pins: List[str] = field(default_factory=list)
    power: Dict[str, Any] = field(default_factory=dict)      # voltage, current_ma, needs_external...
    simulation_available: str = "partial"  # "full" | "partial" | "none"
    wokwi_id: Optional[str] = None
    needs_pwm: bool = False
    needs_analog: bool = False
    uses_i2c: bool = False
    uses_spi: bool = False
    explanation: str = ""
    common_mistakes: List[str] = field(default_factory=list)
    libraries: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------- #
# Student input
# --------------------------------------------------------------------------- #
@dataclass
class BoardEntry:
    type: str
    quantity: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PartEntry:
    type: str
    quantity: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MaterialList:
    """Parsed representation of a student's available materials."""

    student_level: str = "beginner"
    available_boards: List[BoardEntry] = field(default_factory=list)
    parts: List[PartEntry] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict)

    def board_types(self) -> List[str]:
        return [b.type for b in self.available_boards]

    def part_quantities(self) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for p in self.parts:
            out[p.type] = out.get(p.type, 0) + p.quantity
        return out

    def has_part(self, part_type: str, qty: int = 1) -> bool:
        return self.part_quantities().get(part_type, 0) >= qty

    def to_dict(self) -> Dict[str, Any]:
        return {
            "student_level": self.student_level,
            "available_boards": [b.to_dict() for b in self.available_boards],
            "parts": [p.to_dict() for p in self.parts],
            "constraints": self.constraints,
        }


# --------------------------------------------------------------------------- #
# Planner
# --------------------------------------------------------------------------- #
@dataclass
class PlannerResult:
    selected_project: str
    selected_board: str
    confidence: float
    reasoning_summary: str
    template_id: str
    used_parts: List[str] = field(default_factory=list)
    missing_required_parts: List[str] = field(default_factory=list)
    missing_optional_parts: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    candidates: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------- #
# Circuit model
# --------------------------------------------------------------------------- #
@dataclass
class ComponentInstance:
    """A concrete instance of a part placed in a circuit."""

    id: str               # unique, e.g. "ir_left", "motor_driver"
    part_type: str        # references PartProfile.type
    label: str            # human-readable, e.g. "Left IR sensor"
    category: str = "sensor"
    wokwi_id: Optional[str] = None
    wokwi_support: str = "partial"
    attrs: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Connection:
    """A single wire between two endpoints.

    Endpoints are ``(component_id, pin_label)``.  The board itself uses the
    special component id ``"board"``.
    """

    from_part: str
    from_pin: str
    to_part: str
    to_pin: str
    net: str = "signal"     # "signal" | "power" | "ground" | "i2c" | "pwm"
    color: str = "#2c3e50"
    note: str = ""

    def endpoints(self) -> List[str]:
        return [f"{self.from_part}:{self.from_pin}", f"{self.to_part}:{self.to_pin}"]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Circuit:
    board: BoardProfile
    components: List[ComponentInstance] = field(default_factory=list)
    connections: List[Connection] = field(default_factory=list)
    pin_map: Dict[str, str] = field(default_factory=dict)  # firmware constant -> board pin

    def component(self, comp_id: str) -> Optional[ComponentInstance]:
        for c in self.components:
            if c.id == comp_id:
                return c
        return None

    def component_ids(self) -> List[str]:
        return ["board"] + [c.id for c in self.components]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "board": self.board.to_dict(),
            "components": [c.to_dict() for c in self.components],
            "connections": [c.to_dict() for c in self.connections],
            "pin_map": self.pin_map,
        }


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
@dataclass
class ValidationIssue:
    severity: str        # Severity value
    code: str
    message: str
    validator: str
    hint: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationReport:
    issues: List[ValidationIssue] = field(default_factory=list)

    def add(self, issue: ValidationIssue) -> None:
        self.issues.append(issue)

    def extend(self, issues: List[ValidationIssue]) -> None:
        self.issues.extend(issues)

    @property
    def errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.ERROR.value]

    @property
    def warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.WARNING.value]

    @property
    def infos(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.INFO.value]

    @property
    def passed(self) -> bool:
        """The design passes when there are no hard errors."""
        return len(self.errors) == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "num_errors": len(self.errors),
            "num_warnings": len(self.warnings),
            "num_infos": len(self.infos),
            "issues": [i.to_dict() for i in self.issues],
        }


# --------------------------------------------------------------------------- #
# Simulation
# --------------------------------------------------------------------------- #
@dataclass
class SimulationResult:
    backend: str
    success: bool
    available: bool
    serial_output: str = ""
    status: Dict[str, Any] = field(default_factory=dict)
    message: str = ""
    duration_sec: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------- #
# Firmware bundle
# --------------------------------------------------------------------------- #
@dataclass
class Firmware:
    language: str          # "arduino_cpp" | "micropython" | "c_cpp"
    filename: str          # e.g. "sketch.ino"
    source: str
    libraries: List[str] = field(default_factory=list)
    pin_constants: Dict[str, str] = field(default_factory=dict)  # NAME -> board pin

    @property
    def line_count(self) -> int:
        return len(self.source.splitlines())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "language": self.language,
            "filename": self.filename,
            "libraries": self.libraries,
            "pin_constants": self.pin_constants,
            "line_count": self.line_count,
        }
