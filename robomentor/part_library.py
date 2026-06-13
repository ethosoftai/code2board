"""Library of electronic parts known to RoboMentor.

Each entry carries the metadata the planner, generators and validators need:
required/optional pins, power needs, simulation availability, a Wokwi part id
(when one is known) plus an educational explanation and the mistakes students
most often make with that part.
"""

from __future__ import annotations

from typing import Dict, List

from .schemas import PartProfile


def _parts() -> Dict[str, PartProfile]:
    parts: List[PartProfile] = [
        PartProfile(
            type="led",
            name="LED",
            category="actuator",
            required_pins=["anode", "cathode"],
            power={"voltage": 2.0, "current_ma": 20, "needs_external": False},
            simulation_available="full",
            wokwi_id="wokwi-led",
            explanation="A light-emitting diode. Lights up when current flows from anode (+) to cathode (-).",
            common_mistakes=[
                "Forgetting the current-limiting resistor (220-330 ohm) — the LED can burn out.",
                "Reversing the legs: the long leg is the anode (+).",
            ],
            libraries=[],
        ),
        PartProfile(
            type="rgb_led",
            name="RGB LED",
            category="actuator",
            required_pins=["red", "green", "blue", "common"],
            power={"voltage": 2.0, "current_ma": 60, "needs_external": False},
            needs_pwm=True,
            simulation_available="full",
            wokwi_id="wokwi-rgb-led",
            explanation="Three LEDs (red/green/blue) in one package. Use PWM pins to mix colours.",
            common_mistakes=[
                "Mixing up common-anode and common-cathode wiring.",
                "Each colour still needs its own resistor.",
            ],
        ),
        PartProfile(
            type="resistor_220",
            name="Resistor 220Ω",
            category="passive",
            required_pins=["a", "b"],
            power={"needs_external": False},
            simulation_available="full",
            wokwi_id="wokwi-resistor",
            explanation="Limits current. 220-330 ohm is the classic value for protecting an LED on 5V.",
            common_mistakes=["Using too large a value makes the LED very dim."],
        ),
        PartProfile(
            type="resistor",
            name="Resistor (generic)",
            category="passive",
            required_pins=["a", "b"],
            simulation_available="full",
            wokwi_id="wokwi-resistor",
            explanation="Generic resistor. Value chosen for the job (pull-up, current limiting...).",
            common_mistakes=["Reading the colour bands in the wrong direction."],
        ),
        PartProfile(
            type="button",
            name="Push button",
            category="sensor",
            required_pins=["pin1", "pin2"],
            power={"needs_external": False},
            simulation_available="full",
            wokwi_id="wokwi-pushbutton",
            explanation="Momentary switch. Use INPUT_PULLUP so you don't need an external resistor.",
            common_mistakes=[
                "Floating input (no pull-up/pull-down) causes random readings.",
                "Not debouncing in software leads to multiple triggers.",
            ],
        ),
        PartProfile(
            type="potentiometer",
            name="Potentiometer",
            category="sensor",
            required_pins=["vcc", "wiper", "gnd"],
            needs_analog=True,
            power={"voltage": 5.0, "needs_external": False},
            simulation_available="full",
            wokwi_id="wokwi-potentiometer",
            explanation="Variable resistor. The wiper gives an analog voltage you read with analogRead().",
            common_mistakes=["Connecting the wiper to a digital-only pin."],
        ),
        PartProfile(
            type="buzzer",
            name="Buzzer",
            category="actuator",
            required_pins=["pos", "neg"],
            power={"voltage": 5.0, "current_ma": 30, "needs_external": False},
            simulation_available="full",
            wokwi_id="wokwi-buzzer",
            explanation="Makes sound. A passive buzzer uses tone(); an active buzzer just needs HIGH/LOW.",
            common_mistakes=["Driving a large buzzer straight from a pin can exceed the current limit."],
        ),
        PartProfile(
            type="servo_sg90",
            name="SG90 Micro Servo",
            category="actuator",
            required_pins=["signal", "vcc", "gnd"],
            needs_pwm=True,
            power={"voltage": 5.0, "current_ma": 250, "needs_external": True,
                   "note": "Stall current can spike; power from 5V rail, not a logic pin."},
            simulation_available="full",
            wokwi_id="wokwi-servo",
            explanation="A small positional servo controlled by a PWM pulse (0-180 degrees).",
            common_mistakes=[
                "Powering the servo from the board's 3.3V pin — it needs 5V and real current.",
                "No common ground between servo supply and the board.",
            ],
            libraries=["Servo"],
        ),
        PartProfile(
            type="dc_motor",
            name="DC Motor",
            category="actuator",
            required_pins=["term1", "term2"],
            power={"voltage": 6.0, "current_ma": 500, "needs_external": True,
                   "note": "Must be driven through a motor driver, never directly from a GPIO."},
            simulation_available="partial",
            wokwi_id="wokwi-dc-motor",
            explanation="Spins when voltage is applied. Always driven through an H-bridge driver.",
            common_mistakes=[
                "Connecting a motor straight to an Arduino pin — it will damage the board.",
                "No flyback protection / wrong driver wiring.",
            ],
        ),
        PartProfile(
            type="l298n_motor_driver",
            name="L298N Dual H-Bridge Motor Driver",
            category="actuator",
            required_pins=["IN1", "IN2", "IN3", "IN4", "ENA", "ENB",
                           "OUT1", "OUT2", "OUT3", "OUT4", "VCC", "GND", "5V"],
            optional_pins=["5V"],
            needs_pwm=True,
            power={"voltage": 12.0, "current_ma": 2000, "needs_external": True,
                   "note": "Motor supply (VCC) is separate from logic. ENA/ENB want PWM pins."},
            simulation_available="partial",
            wokwi_id=None,
            explanation="Dual H-bridge: drives two DC motors with direction (IN pins) and speed (EN pins, PWM).",
            common_mistakes=[
                "Forgetting to share ground between the L298N and the microcontroller.",
                "Driving ENA/ENB from non-PWM pins (no speed control).",
                "Leaving the on-board 5V jumper in place while also feeding 5V externally.",
            ],
        ),
        PartProfile(
            type="tb6612fng_motor_driver",
            name="TB6612FNG Dual Motor Driver",
            category="actuator",
            required_pins=["AIN1", "AIN2", "BIN1", "BIN2", "PWMA", "PWMB", "STBY",
                           "VM", "VCC", "GND", "AO1", "AO2", "BO1", "BO2"],
            needs_pwm=True,
            power={"voltage": 6.0, "current_ma": 1200, "needs_external": True,
                   "note": "More efficient than L298N. STBY must be HIGH to enable."},
            simulation_available="partial",
            wokwi_id=None,
            explanation="Efficient dual motor driver. Direction via AIN/BIN, speed via PWMA/PWMB, enable via STBY.",
            common_mistakes=[
                "Leaving STBY low (motors stay off).",
                "Not sharing ground with the controller.",
            ],
        ),
        PartProfile(
            type="ir_line_sensor",
            name="IR Line Sensor (TCRT5000-style)",
            category="sensor",
            required_pins=["OUT", "VCC", "GND"],
            optional_pins=["A_OUT"],
            power={"voltage": 5.0, "current_ma": 25, "needs_external": False},
            simulation_available="partial",
            wokwi_id=None,
            explanation="Detects black/white surface by reflected IR light. Digital OUT goes HIGH or LOW over a line.",
            common_mistakes=[
                "Not adjusting the on-board potentiometer threshold.",
                "Ambient light interfering with readings.",
            ],
        ),
        PartProfile(
            type="ultrasonic_hc_sr04",
            name="HC-SR04 Ultrasonic Distance Sensor",
            category="sensor",
            required_pins=["TRIG", "ECHO", "VCC", "GND"],
            power={"voltage": 5.0, "current_ma": 15, "needs_external": False,
                   "note": "ECHO outputs 5V; on a 3.3V board use a voltage divider on ECHO."},
            simulation_available="full",
            wokwi_id="wokwi-hc-sr04",
            explanation="Measures distance using an ultrasonic ping. TRIG starts a pulse, ECHO returns the time of flight.",
            common_mistakes=[
                "Feeding the 5V ECHO straight into a 3.3V board pin.",
                "Forgetting the pulseIn timeout when nothing is in range.",
            ],
        ),
        PartProfile(
            type="dht22",
            name="DHT22 Temperature/Humidity Sensor",
            category="sensor",
            required_pins=["DATA", "VCC", "GND"],
            power={"voltage": 5.0, "current_ma": 5, "needs_external": False},
            simulation_available="full",
            wokwi_id="wokwi-dht22",
            explanation="Digital temperature + humidity sensor on a single data line.",
            common_mistakes=[
                "Reading faster than once every 2 seconds.",
                "Missing the 10k pull-up resistor on the DATA line.",
            ],
            libraries=["DHT sensor library"],
        ),
        PartProfile(
            type="ldr",
            name="LDR / Photoresistor",
            category="sensor",
            required_pins=["a", "b"],
            needs_analog=True,
            power={"voltage": 5.0, "needs_external": False},
            simulation_available="full",
            wokwi_id="wokwi-photoresistor-sensor",
            explanation="Resistance changes with light. Wire as a voltage divider and read with analogRead().",
            common_mistakes=["Forgetting the fixed resistor that forms the divider."],
        ),
        PartProfile(
            type="soil_moisture",
            name="Soil Moisture Sensor (placeholder)",
            category="sensor",
            required_pins=["AOUT", "VCC", "GND"],
            needs_analog=True,
            power={"voltage": 5.0, "needs_external": False},
            simulation_available="partial",
            wokwi_id=None,
            explanation="Analog probe whose reading tracks soil water content. Often substituted by an LDR/pot in sim.",
            common_mistakes=["Leaving the probe permanently powered causes corrosion."],
        ),
        PartProfile(
            type="oled_i2c",
            name="0.96\" OLED Display (SSD1306, I2C)",
            category="display",
            required_pins=["SDA", "SCL", "VCC", "GND"],
            uses_i2c=True,
            power={"voltage": 3.3, "current_ma": 20, "needs_external": False},
            simulation_available="full",
            wokwi_id="board-ssd1306",
            explanation="128x64 OLED on the I2C bus (usually address 0x3C).",
            common_mistakes=["Wrong I2C address.", "Swapping SDA and SCL."],
            libraries=["Adafruit SSD1306", "Adafruit GFX"],
        ),
        PartProfile(
            type="lcd_16x2",
            name="16x2 LCD (with I2C backpack)",
            category="display",
            required_pins=["SDA", "SCL", "VCC", "GND"],
            uses_i2c=True,
            power={"voltage": 5.0, "current_ma": 30, "needs_external": False},
            simulation_available="full",
            wokwi_id="wokwi-lcd1602",
            explanation="Classic 16x2 character LCD; the I2C backpack reduces wiring to 4 pins.",
            common_mistakes=["Contrast pot not adjusted.", "Wrong I2C address (0x27 vs 0x3F)."],
            libraries=["LiquidCrystal_I2C"],
        ),
        PartProfile(
            type="mpu6050",
            name="MPU6050 6-axis IMU",
            category="sensor",
            required_pins=["SDA", "SCL", "VCC", "GND"],
            uses_i2c=True,
            power={"voltage": 3.3, "current_ma": 4, "needs_external": False},
            simulation_available="partial",
            wokwi_id="wokwi-mpu6050",
            explanation="Accelerometer + gyroscope on I2C. Great for balancing/tilt projects.",
            common_mistakes=["No sensor fusion — raw gyro drifts over time."],
            libraries=["Adafruit MPU6050"],
        ),
        PartProfile(
            type="breadboard",
            name="Breadboard",
            category="board_support",
            simulation_available="full",
            wokwi_id="wokwi-breadboard-half",
            explanation="Solderless prototyping board. Power rails run along the edges.",
            common_mistakes=["Assuming the centre channel rows are connected across the gap."],
        ),
        PartProfile(
            type="jumper_wires",
            name="Jumper wires",
            category="board_support",
            simulation_available="full",
            wokwi_id=None,
            explanation="The wires that connect everything. Colour-code them: red=power, black=ground.",
            common_mistakes=["Loose connections causing intermittent faults."],
        ),
        PartProfile(
            type="battery_pack",
            name="Battery pack",
            category="power",
            required_pins=["pos", "neg"],
            power={"voltage": 6.0, "needs_external": True},
            simulation_available="partial",
            wokwi_id="wokwi-battery-9v",
            explanation="Provides motor/system power. Keep its ground common with the controller's ground.",
            common_mistakes=["Reversing polarity.", "Trying to power motors from USB only."],
        ),
        PartProfile(
            type="power_rail",
            name="VCC/GND power rail",
            category="power",
            required_pins=["vcc", "gnd"],
            simulation_available="full",
            wokwi_id=None,
            explanation="Shared positive (VCC) and ground (GND) rails that every component connects to.",
            common_mistakes=["Forgetting a common ground between subsystems."],
        ),
    ]
    return {p.type: p for p in parts}


_PART_TABLE = _parts()

# Aliases so material lists can be a little loose.
_ALIASES = {
    "ir_sensor": "ir_line_sensor",
    "line_sensor": "ir_line_sensor",
    "hc_sr04": "ultrasonic_hc_sr04",
    "ultrasonic": "ultrasonic_hc_sr04",
    "servo": "servo_sg90",
    "sg90": "servo_sg90",
    "l298n": "l298n_motor_driver",
    "tb6612": "tb6612fng_motor_driver",
    "tb6612fng": "tb6612fng_motor_driver",
    "photoresistor": "ldr",
    "oled": "oled_i2c",
    "ssd1306": "oled_i2c",
    "lcd": "lcd_16x2",
    "lcd1602": "lcd_16x2",
    "imu": "mpu6050",
    "resistor_330": "resistor_220",
    "battery": "battery_pack",
}


def resolve_part_type(part_type: str) -> str:
    key = (part_type or "").strip().lower()
    if key in _PART_TABLE:
        return key
    return _ALIASES.get(key, key)


def get_part(part_type: str) -> PartProfile:
    resolved = resolve_part_type(part_type)
    if resolved not in _PART_TABLE:
        raise KeyError(f"Unknown part '{part_type}'. Use list-parts to see known parts.")
    return _PART_TABLE[resolved]


def has_part(part_type: str) -> bool:
    return resolve_part_type(part_type) in _PART_TABLE


def all_parts() -> Dict[str, PartProfile]:
    return dict(_PART_TABLE)


def part_types() -> List[str]:
    return list(_PART_TABLE.keys())
