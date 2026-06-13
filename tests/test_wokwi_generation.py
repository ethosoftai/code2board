import json

from robomentor import circuit_generator, planner
from robomentor.board_profiles import get_board
from robomentor.material_parser import parse_material_dict
from robomentor.validators.wokwi_validator import WokwiValidator


def _line_follower_circuit():
    data = {
        "available_boards": [{"type": "arduino_uno"}],
        "parts": [{"type": "ir_line_sensor", "quantity": 2},
                  {"type": "dc_motor", "quantity": 2},
                  {"type": "l298n_motor_driver", "quantity": 1},
                  {"type": "battery_pack", "quantity": 1}],
    }
    material, _ = parse_material_dict(data)
    plan = planner.plan(material, "follow the line", board="arduino_uno")
    return plan, circuit_generator.build_circuit(plan, material, get_board("arduino_uno"))


def test_planner_selects_line_follower():
    plan, _ = _line_follower_circuit()
    assert plan.selected_project == "line_follower"
    assert plan.template_id == "arduino_line_follower_v1"
    assert not plan.missing_required_parts


def test_diagram_is_valid_json_with_required_keys():
    _, circuit = _line_follower_circuit()
    diagram = circuit_generator.to_wokwi_diagram(circuit)
    # round-trips through JSON
    reparsed = json.loads(json.dumps(diagram))
    for key in ("version", "author", "parts", "connections"):
        assert key in reparsed
    assert len(reparsed["parts"]) >= 1
    assert len(reparsed["connections"]) >= 10


def test_wokwi_validator_no_dangling_endpoints():
    _, circuit = _line_follower_circuit()
    issues = WokwiValidator().validate(circuit)
    assert not any(i.code in ("wokwi_dangling_endpoint", "wokwi_bad_endpoint",
                              "wokwi_missing_key") for i in issues)


def test_demo_exact_pins():
    _, circuit = _line_follower_circuit()
    pm = circuit.pin_map
    assert pm["LEFT_SENSOR_PIN"] == "2"
    assert pm["RIGHT_SENSOR_PIN"] == "3"
    assert pm["IN1"] == "5" and pm["IN4"] == "8"
    assert pm["ENA"] == "9" and pm["ENB"] == "10"
