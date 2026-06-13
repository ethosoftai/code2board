from robomentor.board_profiles import get_board
from robomentor.schemas import Circuit, Firmware
from robomentor.validators.code_circuit_validator import CodeCircuitValidator


def _circuit(pin_map):
    return Circuit(board=get_board("arduino_uno"), components=[], connections=[], pin_map=pin_map)


def test_missing_define_detected():
    circuit = _circuit({"LEFT_SENSOR_PIN": "2"})
    fw = Firmware(language="arduino_cpp", filename="sketch.ino",
                  source="void setup(){} void loop(){}", pin_constants={})
    issues = CodeCircuitValidator().validate(circuit, fw)
    assert any(i.code == "missing_define" for i in issues)


def test_pin_value_mismatch_detected():
    circuit = _circuit({"LEFT_SENSOR_PIN": "2"})
    fw = Firmware(language="arduino_cpp", filename="sketch.ino",
                  source="#define LEFT_SENSOR_PIN 7\n", pin_constants={})
    issues = CodeCircuitValidator().validate(circuit, fw)
    assert any(i.code == "pin_value_mismatch" for i in issues)


def test_consistent_code_passes():
    circuit = _circuit({"LEFT_SENSOR_PIN": "2", "ENA": "9"})
    src = "#define LEFT_SENSOR_PIN 2\n#define ENA 9\nvoid setup(){}\nvoid loop(){}\n"
    fw = Firmware(language="arduino_cpp", filename="sketch.ino", source=src, pin_constants={})
    issues = CodeCircuitValidator().validate(circuit, fw)
    assert not any(i.severity == "error" for i in issues)
