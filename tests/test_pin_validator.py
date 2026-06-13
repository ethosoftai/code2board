from robomentor.board_profiles import get_board
from robomentor.schemas import Circuit
from robomentor.validators.pin_validator import PinValidator


def _circuit(pin_map):
    board = get_board("arduino_uno")
    return Circuit(board=board, components=[], connections=[], pin_map=pin_map)


def test_invalid_pin_is_error():
    issues = PinValidator().validate(_circuit({"FOO_PIN": "99"}))
    assert any(i.code == "pin_not_on_board" and i.severity == "error" for i in issues)


def test_pwm_required_on_non_pwm_pin():
    # Pin 2 exists on the Uno but is NOT PWM; ENA needs PWM.
    issues = PinValidator().validate(_circuit({"ENA": "2"}))
    assert any(i.code == "pwm_required" for i in issues)


def test_pwm_ok_on_pwm_pin():
    issues = PinValidator().validate(_circuit({"ENA": "9"}))
    assert not any(i.code == "pwm_required" for i in issues)


def test_duplicate_pin_conflict():
    issues = PinValidator().validate(_circuit({"A_PIN": "5", "B_PIN": "5"}))
    assert any(i.code == "pin_conflict" for i in issues)


def test_analog_required():
    issues = PinValidator().validate(_circuit({"LDR_PIN": "7"}))
    assert any(i.code == "analog_required" for i in issues)
