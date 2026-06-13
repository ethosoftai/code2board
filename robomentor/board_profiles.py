"""Board profiles for the microcontrollers RoboMentor supports.

Pin data is drawn from public datasheets and the Arduino/MicroPython/Wokwi
ecosystems.  Where a board's exact Wokwi part id or behaviour is uncertain the
profile sets ``wokwi_support="partial"`` and adds an explanatory note instead of
overclaiming exactness (see project requirement #24).
"""

from __future__ import annotations

from typing import Dict, List

from .schemas import BoardProfile


def _arduino_uno() -> BoardProfile:
    digital = [str(i) for i in range(0, 14)]
    analog = [f"A{i}" for i in range(0, 6)]
    return BoardProfile(
        id="arduino_uno",
        name="Arduino Uno (ATmega328P)",
        mcu="ATmega328P",
        logic_voltage=5.0,
        digital_pins=digital + analog,  # A0-A5 double as digital
        analog_pins=analog,
        pwm_pins=["3", "5", "6", "9", "10", "11"],
        i2c_pins={"sda": "A4", "scl": "A5"},
        spi_pins={"mosi": "11", "miso": "12", "sck": "13", "ss": "10"},
        uart_pins={"tx": "1", "rx": "0"},
        power_pins=["5V", "3V3", "GND", "VIN"],
        languages=["arduino_cpp"],
        wokwi_id="wokwi-arduino-uno",
        wokwi_support="full",
        safe_current_note="~20 mA per I/O pin, 200 mA total across all pins. Never drive motors directly.",
        notes=[
            "Pins 0/1 are shared with USB serial; avoid them for sensors during debugging.",
            "A4/A5 are the only hardware I2C pins.",
        ],
    )


def _arduino_nano() -> BoardProfile:
    digital = [str(i) for i in range(0, 14)]
    analog = [f"A{i}" for i in range(0, 8)]  # Nano exposes A0-A7
    return BoardProfile(
        id="arduino_nano",
        name="Arduino Nano (ATmega328P)",
        mcu="ATmega328P",
        logic_voltage=5.0,
        digital_pins=digital + [f"A{i}" for i in range(0, 6)],
        analog_pins=analog,
        pwm_pins=["3", "5", "6", "9", "10", "11"],
        i2c_pins={"sda": "A4", "scl": "A5"},
        spi_pins={"mosi": "11", "miso": "12", "sck": "13", "ss": "10"},
        uart_pins={"tx": "1", "rx": "0"},
        power_pins=["5V", "3V3", "GND", "VIN"],
        languages=["arduino_cpp"],
        wokwi_id="wokwi-arduino-nano",
        wokwi_support="full",
        safe_current_note="Same ATmega328P limits as the Uno: ~20 mA/pin.",
        notes=[
            "A6/A7 are analog-input only (no digital write).",
        ],
    )


def _arduino_mega() -> BoardProfile:
    digital = [str(i) for i in range(0, 54)]
    analog = [f"A{i}" for i in range(0, 16)]
    pwm = [str(i) for i in range(2, 14)] + ["44", "45", "46"]
    return BoardProfile(
        id="arduino_mega",
        name="Arduino Mega 2560",
        mcu="ATmega2560",
        logic_voltage=5.0,
        digital_pins=digital + analog,
        analog_pins=analog,
        pwm_pins=pwm,
        i2c_pins={"sda": "20", "scl": "21"},
        spi_pins={"mosi": "51", "miso": "50", "sck": "52", "ss": "53"},
        uart_pins={"tx": "1", "rx": "0"},
        power_pins=["5V", "3V3", "GND", "VIN"],
        languages=["arduino_cpp"],
        wokwi_id="wokwi-arduino-mega",
        wokwi_support="full",
        safe_current_note="~20 mA per pin. Many pins, but the same 'no direct motor drive' rule applies.",
        notes=["Has 4 hardware UARTs and lots of PWM pins — great for bigger robots."],
    )


def _esp32_devkit() -> BoardProfile:
    # GPIOs commonly broken out on DevKit V1. 34-39 are input-only.
    usable = [str(i) for i in [2, 4, 5, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23, 25, 26, 27, 32, 33]]
    input_only = ["34", "35", "36", "39"]
    analog = ["32", "33", "34", "35", "36", "39", "25", "26", "27", "2", "4", "12", "13", "14", "15"]
    return BoardProfile(
        id="esp32_devkit_v1",
        name="ESP32 DevKit V1 (38-pin)",
        mcu="ESP32-WROOM-32",
        logic_voltage=3.3,
        digital_pins=usable + input_only,
        analog_pins=analog,
        # Almost all output-capable GPIOs support PWM (LEDC) on ESP32.
        pwm_pins=usable,
        i2c_pins={"sda": "21", "scl": "22"},
        spi_pins={"mosi": "23", "miso": "19", "sck": "18", "ss": "5"},
        uart_pins={"tx": "1", "rx": "3"},
        power_pins=["5V", "3V3", "GND", "VIN"],
        languages=["arduino_cpp", "micropython"],
        wokwi_id="wokwi-esp32-devkit-v1",
        wokwi_support="full",
        safe_current_note="3.3V logic! ~12 mA/pin recommended. 5V sensors may need a level shifter.",
        notes=[
            "GPIO 34/35/36/39 are INPUT ONLY (no output, no internal pull-ups).",
            "GPIO 6-11 are used by flash — never use them.",
            "PWM is via the LEDC peripheral; any output pin can be a PWM channel.",
        ],
    )


def _pico() -> BoardProfile:
    gp = [f"GP{i}" for i in range(0, 23)] + [f"GP{i}" for i in range(26, 29)]
    analog = ["GP26", "GP27", "GP28"]
    return BoardProfile(
        id="raspberry_pi_pico",
        name="Raspberry Pi Pico (RP2040)",
        mcu="RP2040",
        logic_voltage=3.3,
        digital_pins=gp,
        analog_pins=analog,
        pwm_pins=[p for p in gp],  # every GPIO has a PWM slice
        i2c_pins={"sda": "GP4", "scl": "GP5"},   # I2C0 default
        spi_pins={"mosi": "GP19", "miso": "GP16", "sck": "GP18", "ss": "GP17"},
        uart_pins={"tx": "GP0", "rx": "GP1"},
        power_pins=["3V3", "VSYS", "VBUS", "GND"],
        languages=["arduino_cpp", "micropython"],
        wokwi_id="wokwi-pi-pico",
        wokwi_support="full",
        safe_current_note="3.3V logic. ~12 mA/pin recommended, ADC pins GP26-28 only.",
        notes=[
            "ADC is only on GP26/27/28.",
            "No 5V logic tolerance — use a level shifter for 5V sensors.",
        ],
    )


def _pico_w() -> BoardProfile:
    base = _pico()
    base.id = "raspberry_pi_pico_w"
    base.name = "Raspberry Pi Pico W (RP2040 + WiFi)"
    base.wokwi_id = "wokwi-pi-pico-w"
    base.notes = base.notes + ["On-board LED is driven through the WiFi chip (CYW43), not a plain GPIO."]
    return base


def _stm32_nucleo() -> BoardProfile:
    # Use Arduino-style Dn / An labels exposed by the Nucleo headers (STM32duino).
    digital = [f"D{i}" for i in range(0, 16)]
    analog = [f"A{i}" for i in range(0, 6)]
    return BoardProfile(
        id="stm32_nucleo_basic",
        name="STM32 Nucleo (generic, STM32duino headers)",
        mcu="STM32F103/F4xx (board dependent)",
        logic_voltage=3.3,
        digital_pins=digital + analog,
        analog_pins=analog,
        pwm_pins=["D3", "D5", "D6", "D9", "D10", "D11"],
        i2c_pins={"sda": "D14", "scl": "D15"},
        spi_pins={"mosi": "D11", "miso": "D12", "sck": "D13", "ss": "D10"},
        uart_pins={"tx": "D1", "rx": "D0"},
        power_pins=["5V", "3V3", "GND", "VIN"],
        languages=["arduino_cpp", "c_cpp"],
        wokwi_id=None,
        wokwi_support="none",
        safe_current_note="3.3V logic. Per-pin current is low (~8-20 mA depending on family).",
        notes=[
            "APPROXIMATE: exact pin mapping depends on the specific Nucleo board.",
            "Wokwi has limited/experimental STM32 support — RoboMentor renders locally and "
            "generates an Arduino-core (STM32duino) sketch plus a bare-metal C/C++ skeleton.",
            "Verify the pinout against your specific Nucleo variant before wiring.",
        ],
    )


_BUILDERS = {
    "arduino_uno": _arduino_uno,
    "arduino_nano": _arduino_nano,
    "arduino_mega": _arduino_mega,
    "esp32_devkit_v1": _esp32_devkit,
    "raspberry_pi_pico": _pico,
    "raspberry_pi_pico_w": _pico_w,
    "stm32_nucleo_basic": _stm32_nucleo,
}

# Friendly aliases students might type.
_ALIASES = {
    "uno": "arduino_uno",
    "arduino": "arduino_uno",
    "nano": "arduino_nano",
    "mega": "arduino_mega",
    "esp32": "esp32_devkit_v1",
    "esp32_devkit": "esp32_devkit_v1",
    "pico": "raspberry_pi_pico",
    "pico_w": "raspberry_pi_pico_w",
    "picow": "raspberry_pi_pico_w",
    "stm32": "stm32_nucleo_basic",
    "nucleo": "stm32_nucleo_basic",
}


def board_ids() -> List[str]:
    return list(_BUILDERS.keys())


def resolve_board_id(name: str) -> str:
    key = (name or "").strip().lower()
    return _ALIASES.get(key, key)


def get_board(board_id: str) -> BoardProfile:
    """Return a fresh :class:`BoardProfile` for ``board_id`` (or alias)."""
    resolved = resolve_board_id(board_id)
    if resolved not in _BUILDERS:
        raise KeyError(
            f"Unknown board '{board_id}'. Known boards: {', '.join(board_ids())}"
        )
    return _BUILDERS[resolved]()


def all_boards() -> Dict[str, BoardProfile]:
    return {bid: builder() for bid, builder in _BUILDERS.items()}
