from robomentor.board_profiles import get_board
from robomentor.schemas import Circuit, ComponentInstance, Connection
from robomentor.validators.power_validator import PowerValidator


def test_motor_direct_drive_is_error():
    board = get_board("arduino_uno")
    comps = [ComponentInstance(id="m1", part_type="dc_motor", label="Motor", category="actuator")]
    conns = [Connection(from_part="board", from_pin="9", to_part="m1", to_pin="term1", net="signal")]
    issues = PowerValidator().validate(Circuit(board=board, components=comps, connections=conns))
    assert any(i.code == "motor_direct_drive" and i.severity == "error" for i in issues)


def test_missing_common_ground_is_error():
    board = get_board("arduino_uno")
    comps = [ComponentInstance(id="led1", part_type="led", label="LED", category="actuator")]
    conns = [Connection(from_part="board", from_pin="13", to_part="led1", to_pin="anode", net="signal")]
    issues = PowerValidator().validate(Circuit(board=board, components=comps, connections=conns))
    assert any(i.code == "no_common_ground" for i in issues)


def test_motor_driver_supply_note_emitted():
    board = get_board("arduino_uno")
    comps = [ComponentInstance(id="drv", part_type="l298n_motor_driver",
                               label="Driver", category="actuator")]
    conns = [Connection(from_part="board", from_pin="GND", to_part="drv", to_pin="GND", net="ground")]
    issues = PowerValidator().validate(Circuit(board=board, components=comps, connections=conns))
    assert any(i.code == "motor_driver_supply_note" for i in issues)


def test_hcsr04_voltage_warning_on_3v3_board():
    board = get_board("esp32_devkit_v1")
    comps = [ComponentInstance(id="us", part_type="ultrasonic_hc_sr04",
                               label="HC-SR04", category="sensor")]
    conns = [Connection(from_part="board", from_pin="GND", to_part="us", to_pin="GND", net="ground")]
    issues = PowerValidator().validate(Circuit(board=board, components=comps, connections=conns))
    assert any(i.code == "hcsr04_voltage" for i in issues)
