"""Deterministic circuit generator.

Builds an internal :class:`~robomentor.schemas.Circuit` for the selected template
and board, then exports it to every artifact format RoboMentor produces:

* Wokwi ``diagram.json``
* CSV wiring table
* Graphviz DOT
* JSON pin map
* Markdown wiring explanation

Pin choices are **deterministic**: each template declares preferred pins (which
match the classic Arduino wiring used in the demo) and a :class:`PinAllocator`
fills in anything else in a stable order.  A ``seed`` is accepted for API
symmetry but the default behaviour is fully reproducible without randomness.
"""

from __future__ import annotations

import csv
import io
from typing import Dict, List, Optional, Tuple

from . import board_profiles, part_library, planner
from .schemas import (
    BoardProfile,
    Circuit,
    ComponentInstance,
    Connection,
    MaterialList,
    PlannerResult,
)
from .utils import net_color

# Pins that exist on a board but must not be used as outputs (or at all).
_NON_OUTPUT_PINS: Dict[str, set] = {
    "esp32_devkit_v1": {"34", "35", "36", "39"},  # input-only
}
_FORBIDDEN_PINS: Dict[str, set] = {
    "esp32_devkit_v1": {"6", "7", "8", "9", "10", "11"},  # flash pins
}


class PinAllocator:
    """Hands out free pins in a stable order, honouring preferred pins."""

    def __init__(self, board: BoardProfile) -> None:
        self.board = board
        self.used: set = set(board.uart_pins.values())  # reserve serial by default
        self.used |= _FORBIDDEN_PINS.get(board.id, set())

    def _ok_kind(self, pin: str, kind: str, output: bool) -> bool:
        if kind == "pwm" and not self.board.is_pwm(pin):
            return False
        if kind == "analog" and not self.board.is_analog(pin):
            return False
        if output and pin in _NON_OUTPUT_PINS.get(self.board.id, set()):
            return False
        return True

    def take(self, preferred: Optional[str] = None, kind: str = "digital",
             output: bool = False) -> str:
        if (preferred and self.board.has_pin(preferred) and preferred not in self.used
                and self._ok_kind(preferred, kind, output)):
            self.used.add(preferred)
            return preferred

        if kind == "pwm":
            pool = self.board.pwm_pins
        elif kind == "analog":
            pool = self.board.analog_pins
        else:
            pool = self.board.digital_pins
        for p in pool:
            if p not in self.used and self._ok_kind(p, kind, output):
                self.used.add(p)
                return p
        # last resort: any free pin at all (keeps generation from crashing)
        for p in self.board.all_pins():
            if p not in self.used:
                self.used.add(p)
                return p
        raise RuntimeError(f"Ran out of free pins on board '{self.board.id}'.")


# --------------------------------------------------------------------------- #
# Connection helpers
# --------------------------------------------------------------------------- #
def _conn(frm_part: str, frm_pin: str, to_part: str, to_pin: str,
          net: str = "signal", note: str = "") -> Connection:
    return Connection(
        from_part=frm_part, from_pin=frm_pin, to_part=to_part, to_pin=to_pin,
        net=net, color=net_color(net), note=note,
    )


def _comp(comp_id: str, part_type: str, label: str) -> ComponentInstance:
    part = part_library.get_part(part_type)
    return ComponentInstance(
        id=comp_id, part_type=part_type, label=label,
        category=part.category, wokwi_id=part.wokwi_id,
        wokwi_support=part.simulation_available,
    )


def _choose_motor_driver(material: MaterialList) -> str:
    if material.has_part("tb6612fng_motor_driver"):
        return "tb6612fng_motor_driver"
    return "l298n_motor_driver"


# --------------------------------------------------------------------------- #
# Template builders
# --------------------------------------------------------------------------- #
def _build_line_follower(board: BoardProfile, material: MaterialList) -> Circuit:
    alloc = PinAllocator(board)
    components: List[ComponentInstance] = []
    connections: List[Connection] = []
    pin_map: Dict[str, str] = {}

    driver_type = _choose_motor_driver(material)
    has_battery = material.has_part("battery_pack")

    # Sensors (digital inputs) — preferred D2/D3 to match the classic wiring.
    left_pin = alloc.take("2", kind="digital")
    right_pin = alloc.take("3", kind="digital")
    pin_map["LEFT_SENSOR_PIN"] = left_pin
    pin_map["RIGHT_SENSOR_PIN"] = right_pin

    components.append(_comp("ir_left", "ir_line_sensor", "Left IR sensor"))
    components.append(_comp("ir_right", "ir_line_sensor", "Right IR sensor"))
    components.append(_comp("driver", driver_type,
                            "Motor driver (" + ("TB6612FNG" if "tb6612" in driver_type else "L298N") + ")"))
    components.append(_comp("motor_left", "dc_motor", "Left DC motor"))
    components.append(_comp("motor_right", "dc_motor", "Right DC motor"))
    if has_battery:
        components.append(_comp("battery", "battery_pack", "Motor battery pack"))

    # Sensor signal lines
    connections.append(_conn("board", left_pin, "ir_left", "OUT", "signal"))
    connections.append(_conn("board", right_pin, "ir_right", "OUT", "signal"))

    # Motor driver control lines
    if "tb6612" in driver_type:
        pin_map["AIN1"] = alloc.take("5", kind="digital", output=True)
        pin_map["AIN2"] = alloc.take("6", kind="digital", output=True)
        pin_map["BIN1"] = alloc.take("7", kind="digital", output=True)
        pin_map["BIN2"] = alloc.take("8", kind="digital", output=True)
        pin_map["PWMA"] = alloc.take("9", kind="pwm", output=True)
        pin_map["PWMB"] = alloc.take("10", kind="pwm", output=True)
        pin_map["STBY"] = alloc.take("4", kind="digital", output=True)
        for name in ("AIN1", "AIN2", "BIN1", "BIN2", "PWMA", "PWMB", "STBY"):
            net = "pwm" if name.startswith("PWM") else "signal"
            connections.append(_conn("board", pin_map[name], "driver", name, net))
    else:  # L298N
        pin_map["IN1"] = alloc.take("5", kind="digital", output=True)
        pin_map["IN2"] = alloc.take("6", kind="digital", output=True)
        pin_map["IN3"] = alloc.take("7", kind="digital", output=True)
        pin_map["IN4"] = alloc.take("8", kind="digital", output=True)
        pin_map["ENA"] = alloc.take("9", kind="pwm", output=True)
        pin_map["ENB"] = alloc.take("10", kind="pwm", output=True)
        for name in ("IN1", "IN2", "IN3", "IN4"):
            connections.append(_conn("board", pin_map[name], "driver", name, "signal"))
        connections.append(_conn("board", pin_map["ENA"], "driver", "ENA", "pwm"))
        connections.append(_conn("board", pin_map["ENB"], "driver", "ENB", "pwm"))

    # Motor outputs
    connections.append(_conn("driver", "OUT1", "motor_left", "term1", "power"))
    connections.append(_conn("driver", "OUT2", "motor_left", "term2", "power"))
    connections.append(_conn("driver", "OUT3", "motor_right", "term1", "power"))
    connections.append(_conn("driver", "OUT4", "motor_right", "term2", "power"))

    # Sensor power
    connections.append(_conn("board", "5V", "ir_left", "VCC", "power"))
    connections.append(_conn("board", "5V", "ir_right", "VCC", "power"))
    connections.append(_conn("board", "GND", "ir_left", "GND", "ground"))
    connections.append(_conn("board", "GND", "ir_right", "GND", "ground"))

    # Common ground + motor supply
    connections.append(_conn("board", "GND", "driver", "GND", "ground",
                             note="Common ground between Arduino and motor driver"))
    if has_battery:
        connections.append(_conn("battery", "pos", "driver", "VCC", "power",
                                 note="External motor supply (do NOT power motors from the board)"))
        connections.append(_conn("battery", "neg", "driver", "GND", "ground"))
        connections.append(_conn("battery", "neg", "board", "GND", "ground",
                                 note="Tie battery ground to the board ground"))

    return Circuit(board=board, components=components, connections=connections, pin_map=pin_map)


def _build_obstacle_avoider(board: BoardProfile, material: MaterialList) -> Circuit:
    alloc = PinAllocator(board)
    components: List[ComponentInstance] = []
    connections: List[Connection] = []
    pin_map: Dict[str, str] = {}

    driver_type = _choose_motor_driver(material)
    has_servo = material.has_part("servo_sg90")
    has_battery = material.has_part("battery_pack")

    pin_map["TRIG_PIN"] = alloc.take("9", kind="digital", output=True)
    pin_map["ECHO_PIN"] = alloc.take("10", kind="digital")
    components.append(_comp("ultrasonic", "ultrasonic_hc_sr04", "HC-SR04 ultrasonic sensor"))
    components.append(_comp("driver", driver_type, "Motor driver"))
    components.append(_comp("motor_left", "dc_motor", "Left DC motor"))
    components.append(_comp("motor_right", "dc_motor", "Right DC motor"))

    connections.append(_conn("board", pin_map["TRIG_PIN"], "ultrasonic", "TRIG", "signal"))
    connections.append(_conn("board", pin_map["ECHO_PIN"], "ultrasonic", "ECHO", "signal",
                             note="On 3.3V boards add a voltage divider on ECHO"))
    connections.append(_conn("board", "5V", "ultrasonic", "VCC", "power"))
    connections.append(_conn("board", "GND", "ultrasonic", "GND", "ground"))

    if "tb6612" in driver_type:
        names = [("AIN1", "5", "digital"), ("AIN2", "6", "digital"),
                 ("BIN1", "7", "digital"), ("BIN2", "8", "digital"),
                 ("PWMA", "3", "pwm"), ("PWMB", "11", "pwm"), ("STBY", "4", "digital")]
    else:
        names = [("IN1", "5", "digital"), ("IN2", "6", "digital"),
                 ("IN3", "7", "digital"), ("IN4", "8", "digital"),
                 ("ENA", "3", "pwm"), ("ENB", "11", "pwm")]
    for name, pref, kind in names:
        pin_map[name] = alloc.take(pref, kind=kind, output=True)
        net = "pwm" if kind == "pwm" else "signal"
        connections.append(_conn("board", pin_map[name], "driver", name, net))

    connections.append(_conn("driver", "OUT1", "motor_left", "term1", "power"))
    connections.append(_conn("driver", "OUT2", "motor_left", "term2", "power"))
    connections.append(_conn("driver", "OUT3", "motor_right", "term1", "power"))
    connections.append(_conn("driver", "OUT4", "motor_right", "term2", "power"))
    connections.append(_conn("board", "GND", "driver", "GND", "ground",
                             note="Common ground"))

    if has_servo:
        pin_map["SERVO_PIN"] = alloc.take("12", kind="pwm", output=True)
        components.append(_comp("servo", "servo_sg90", "Scanning servo"))
        connections.append(_conn("board", pin_map["SERVO_PIN"], "servo", "signal", "pwm"))
        connections.append(_conn("board", "5V", "servo", "vcc", "power"))
        connections.append(_conn("board", "GND", "servo", "gnd", "ground"))

    if has_battery:
        components.append(_comp("battery", "battery_pack", "Motor battery pack"))
        connections.append(_conn("battery", "pos", "driver", "VCC", "power",
                                 note="External motor supply"))
        connections.append(_conn("battery", "neg", "driver", "GND", "ground"))
        connections.append(_conn("battery", "neg", "board", "GND", "ground"))

    return Circuit(board=board, components=components, connections=connections, pin_map=pin_map)


def _build_traffic_light(board: BoardProfile, material: MaterialList) -> Circuit:
    alloc = PinAllocator(board)
    components: List[ComponentInstance] = []
    connections: List[Connection] = []
    pin_map: Dict[str, str] = {}

    has_button = material.has_part("button")
    has_buzzer = material.has_part("buzzer")

    led_defs = [("RED_PIN", "led_red", "Red LED", "11"),
                ("YELLOW_PIN", "led_yellow", "Yellow LED", "12"),
                ("GREEN_PIN", "led_green", "Green LED", "13")]
    for const, cid, label, pref in led_defs:
        pin_map[const] = alloc.take(pref, kind="digital", output=True)
        components.append(_comp(cid, "led", label))
        components.append(_comp(cid + "_r", "resistor_220", label + " resistor"))
        # board -> resistor -> LED anode -> GND
        connections.append(_conn("board", pin_map[const], cid + "_r", "a", "signal"))
        connections.append(_conn(cid + "_r", "b", cid, "anode", "signal"))
        connections.append(_conn(cid, "cathode", "board", "GND", "ground"))

    if has_button:
        pin_map["BUTTON_PIN"] = alloc.take("2", kind="digital")
        components.append(_comp("button", "button", "Pedestrian button"))
        connections.append(_conn("board", pin_map["BUTTON_PIN"], "button", "pin1", "signal",
                                 note="Use INPUT_PULLUP"))
        connections.append(_conn("button", "pin2", "board", "GND", "ground"))

    if has_buzzer:
        pin_map["BUZZER_PIN"] = alloc.take("8", kind="digital", output=True)
        components.append(_comp("buzzer", "buzzer", "Crossing buzzer"))
        connections.append(_conn("board", pin_map["BUZZER_PIN"], "buzzer", "pos", "signal"))
        connections.append(_conn("buzzer", "neg", "board", "GND", "ground"))

    return Circuit(board=board, components=components, connections=connections, pin_map=pin_map)


def _build_smart_greenhouse(board: BoardProfile, material: MaterialList) -> Circuit:
    alloc = PinAllocator(board)
    components: List[ComponentInstance] = []
    connections: List[Connection] = []
    pin_map: Dict[str, str] = {}

    has_dht = material.has_part("dht22")
    has_ldr = material.has_part("ldr")
    has_soil = material.has_part("soil_moisture")
    has_oled = material.has_part("oled_i2c")
    has_lcd = material.has_part("lcd_16x2")
    has_buzzer = material.has_part("buzzer")
    has_led = material.has_part("led")

    if has_dht:
        pin_map["DHT_PIN"] = alloc.take("2", kind="digital")
        components.append(_comp("dht", "dht22", "DHT22 temp/humidity"))
        connections.append(_conn("board", pin_map["DHT_PIN"], "dht", "DATA", "signal"))
        connections.append(_conn("board", "5V", "dht", "VCC", "power"))
        connections.append(_conn("board", "GND", "dht", "GND", "ground"))

    if has_ldr:
        pin_map["LDR_PIN"] = alloc.take("A0", kind="analog")
        components.append(_comp("ldr", "ldr", "Light sensor (LDR)"))
        components.append(_comp("ldr_r", "resistor_220", "LDR divider resistor"))
        connections.append(_conn("board", "5V", "ldr", "a", "power"))
        connections.append(_conn("ldr", "b", "board", pin_map["LDR_PIN"], "signal"))
        connections.append(_conn("board", pin_map["LDR_PIN"], "ldr_r", "a", "signal"))
        connections.append(_conn("ldr_r", "b", "board", "GND", "ground"))

    if has_soil:
        pin_map["SOIL_PIN"] = alloc.take("A1", kind="analog")
        components.append(_comp("soil", "soil_moisture", "Soil moisture probe"))
        connections.append(_conn("board", pin_map["SOIL_PIN"], "soil", "AOUT", "signal"))
        connections.append(_conn("board", "5V", "soil", "VCC", "power"))
        connections.append(_conn("board", "GND", "soil", "GND", "ground"))

    display = None
    if has_oled:
        display = ("oled", "oled_i2c", "OLED display")
    elif has_lcd:
        display = ("lcd", "lcd_16x2", "16x2 LCD")
    if display:
        cid, ptype, label = display
        components.append(_comp(cid, ptype, label))
        connections.append(_conn("board", board.i2c_pins.get("sda", "A4"), cid, "SDA", "i2c"))
        connections.append(_conn("board", board.i2c_pins.get("scl", "A5"), cid, "SCL", "i2c"))
        connections.append(_conn("board", "5V", cid, "VCC", "power"))
        connections.append(_conn("board", "GND", cid, "GND", "ground"))
        pin_map["I2C_SDA"] = board.i2c_pins.get("sda", "A4")
        pin_map["I2C_SCL"] = board.i2c_pins.get("scl", "A5")

    if has_buzzer:
        pin_map["BUZZER_PIN"] = alloc.take("8", kind="digital", output=True)
        components.append(_comp("buzzer", "buzzer", "Alert buzzer"))
        connections.append(_conn("board", pin_map["BUZZER_PIN"], "buzzer", "pos", "signal"))
        connections.append(_conn("buzzer", "neg", "board", "GND", "ground"))

    if has_led:
        pin_map["STATUS_LED_PIN"] = alloc.take("13", kind="digital", output=True)
        components.append(_comp("status_led", "led", "Status LED"))
        components.append(_comp("status_led_r", "resistor_220", "Status LED resistor"))
        connections.append(_conn("board", pin_map["STATUS_LED_PIN"], "status_led_r", "a", "signal"))
        connections.append(_conn("status_led_r", "b", "status_led", "anode", "signal"))
        connections.append(_conn("status_led", "cathode", "board", "GND", "ground"))

    return Circuit(board=board, components=components, connections=connections, pin_map=pin_map)


_BUILDERS = {
    "arduino_line_follower_v1": _build_line_follower,
    "obstacle_avoider_v1": _build_obstacle_avoider,
    "traffic_light_v1": _build_traffic_light,
    "smart_greenhouse_v1": _build_smart_greenhouse,
}


def build_circuit(plan_result: PlannerResult, material: MaterialList,
                  board: Optional[BoardProfile] = None, seed: int = 1337) -> Circuit:
    if board is None:
        board = board_profiles.get_board(plan_result.selected_board)
    builder = _BUILDERS.get(plan_result.template_id)
    if builder is None:
        raise KeyError(f"No circuit builder for template '{plan_result.template_id}'.")
    return builder(board, material)


# --------------------------------------------------------------------------- #
# Exporters
# --------------------------------------------------------------------------- #
def to_wokwi_diagram(circuit: Circuit) -> Dict:
    """Export to a Wokwi-compatible ``diagram.json`` structure.

    Where a part has no known Wokwi id the component is still emitted with a
    ``"wokwi_support": "partial"`` attribute so the Wokwi validator can flag it
    rather than silently claiming full simulation (requirement #24).
    """
    parts = [{
        "type": circuit.board.wokwi_id or "wokwi-arduino-uno",
        "id": "board",
        "top": 0, "left": 0,
        "attrs": {},
    }]
    # simple deterministic layout grid
    for idx, comp in enumerate(circuit.components):
        col = idx % 4
        row = idx // 4
        parts.append({
            "type": comp.wokwi_id or f"unknown-{comp.part_type}",
            "id": comp.id,
            "top": 120 + row * 120,
            "left": -200 + col * 160,
            "attrs": {},
            "robomentor_meta": {
                "part_type": comp.part_type,
                "label": comp.label,
                "wokwi_support": comp.wokwi_support,
            },
        })

    conns = []
    for c in circuit.connections:
        conns.append([
            f"{c.from_part}:{c.from_pin}",
            f"{c.to_part}:{c.to_pin}",
            c.color,
            [{"net": c.net, "note": c.note}],
        ])

    return {
        "version": 1,
        "author": "RoboMentor",
        "editor": "robomentor",
        "parts": parts,
        "connections": conns,
    }


def wiring_table(circuit: Circuit) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for c in circuit.connections:
        rows.append({
            "from_component": c.from_part,
            "from_pin": c.from_pin,
            "to_component": c.to_part,
            "to_pin": c.to_pin,
            "net": c.net,
            "color": c.color,
            "note": c.note,
        })
    return rows


def to_wiring_csv(circuit: Circuit) -> str:
    buf = io.StringIO()
    fieldnames = ["from_component", "from_pin", "to_component", "to_pin", "net", "color", "note"]
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for row in wiring_table(circuit):
        writer.writerow(row)
    return buf.getvalue()


def to_pin_map(circuit: Circuit) -> Dict:
    return {
        "board": circuit.board.id,
        "logic_voltage": circuit.board.logic_voltage,
        "firmware_constants": circuit.pin_map,
    }


def to_dot(circuit: Circuit) -> str:
    """Render the circuit as a Graphviz DOT string (used by graphviz_renderer)."""
    lines = ["digraph circuit {", "  rankdir=LR;", '  node [shape=box, style="rounded,filled", fontname="Helvetica"];',
             '  edge [fontname="Helvetica", fontsize=9];']
    # board node
    lines.append(f'  "board" [label="{circuit.board.name}", fillcolor="#34495e", fontcolor="white"];')
    from .utils import category_color
    for comp in circuit.components:
        color = category_color(comp.category)
        lines.append(f'  "{comp.id}" [label="{comp.label}\\n({comp.part_type})", fillcolor="{color}", fontcolor="white"];')
    for c in circuit.connections:
        label = f"{c.from_pin}->{c.to_pin}"
        lines.append(f'  "{c.from_part}" -> "{c.to_part}" [label="{label}", color="{c.color}"];')
    lines.append("}")
    return "\n".join(lines)


def to_markdown(circuit: Circuit) -> str:
    lines = [f"# Wiring — {circuit.board.name}", ""]
    lines.append("## Pin map (firmware constant → board pin)")
    lines.append("")
    lines.append("| Constant | Board pin |")
    lines.append("|----------|-----------|")
    for name, pin in circuit.pin_map.items():
        lines.append(f"| `{name}` | `{pin}` |")
    lines.append("")
    lines.append("## Connections")
    lines.append("")
    lines.append("| From | Pin | To | Pin | Net | Note |")
    lines.append("|------|-----|----|-----|-----|------|")
    for c in circuit.connections:
        lines.append(f"| {c.from_part} | {c.from_pin} | {c.to_part} | {c.to_pin} | {c.net} | {c.note} |")
    lines.append("")
    return "\n".join(lines)
