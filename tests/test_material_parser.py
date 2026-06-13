import json

from robomentor.material_parser import parse_material_dict, parse_material_file
from robomentor.schemas import MaterialList


def test_parses_basic_dict():
    data = {
        "student_level": "beginner",
        "available_boards": [{"type": "arduino_uno", "quantity": 1}],
        "parts": [{"type": "ir_line_sensor", "quantity": 2},
                  {"type": "dc_motor", "quantity": 2}],
        "constraints": {"avoid_soldering": True},
    }
    material, warnings = parse_material_dict(data)
    assert isinstance(material, MaterialList)
    assert material.student_level == "beginner"
    assert material.board_types() == ["arduino_uno"]
    assert material.has_part("ir_line_sensor", 2)
    assert material.part_quantities()["dc_motor"] == 2
    assert material.constraints["avoid_soldering"] is True


def test_aliases_and_loose_strings():
    data = {"available_boards": ["uno"], "parts": ["ir_sensor", {"type": "l298n"}]}
    material, warnings = parse_material_dict(data)
    assert material.board_types() == ["arduino_uno"]
    # 'ir_sensor' alias -> ir_line_sensor, 'l298n' -> l298n_motor_driver
    assert material.has_part("ir_line_sensor")
    assert material.has_part("l298n_motor_driver")


def test_unknown_part_warns_but_parses():
    data = {"parts": [{"type": "flux_capacitor", "quantity": 1}]}
    material, warnings = parse_material_dict(data)
    assert any("flux_capacitor" in w for w in warnings)


def test_parse_file(tmp_path):
    p = tmp_path / "mats.json"
    p.write_text(json.dumps({"available_boards": [{"type": "esp32"}], "parts": []}))
    material, _ = parse_material_file(p)
    assert material.board_types() == ["esp32_devkit_v1"]
