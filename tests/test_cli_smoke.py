from pathlib import Path

from robomentor.cli import main


def test_generate_smoke(tmp_path):
    materials = tmp_path / "mats.json"
    materials.write_text(
        '{"available_boards":[{"type":"arduino_uno"}],'
        '"parts":[{"type":"ir_line_sensor","quantity":2},'
        '{"type":"dc_motor","quantity":2},'
        '{"type":"l298n_motor_driver","quantity":1},'
        '{"type":"battery_pack","quantity":1}]}'
    )
    request = tmp_path / "req.txt"
    request.write_text("build a line following robot")
    out = tmp_path / "demo"

    rc = main([
        "generate",
        "--materials", str(materials),
        "--request", str(request),
        "--out", str(out),
        "--board", "arduino_uno",
        "--simulate", "static",
        "--render", "high",
    ])
    assert rc == 0  # validation should pass for a complete kit

    # Core artifacts exist
    assert (out / "project_plan.json").exists()
    assert (out / "bill_of_materials.json").exists()
    assert (out / "wiring_table.csv").exists()
    assert (out / "pin_map.json").exists()
    assert (out / "firmware" / "sketch.ino").exists()
    assert (out / "simulation" / "diagram.json").exists()
    assert (out / "simulation" / "wokwi.toml").exists()
    assert (out / "validation" / "validation_report.json").exists()
    assert (out / "simulation_logs" / "serial_output.txt").exists()
    assert (out / "renders" / "circuit_diagram.svg").exists()
    assert (out / "report" / "report.html").exists()
    assert (out / "report" / "educational_explanation.md").exists()
    assert (out / "metrics.json").exists()

    sketch = (out / "firmware" / "sketch.ino").read_text()
    assert "#define LEFT_SENSOR_PIN 2" in sketch
    assert "void loop()" in sketch


def test_validate_and_list_commands(tmp_path):
    # list-boards / list-parts should run without error
    assert main(["list-boards"]) == 0
    assert main(["list-parts"]) == 0
