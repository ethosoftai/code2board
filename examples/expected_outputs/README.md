# Expected outputs

This folder is a placeholder for committed reference outputs used in the
workshop paper and for regression comparison.

Generate the canonical line-follower demo into this folder with:

```bash
python -m robomentor.cli generate \
  --materials examples/materials/beginner_arduino_kit.json \
  --request examples/requests/line_follower.txt \
  --out examples/expected_outputs/line_follower_demo \
  --board arduino_uno \
  --simulate static \
  --render high
```

A generated project contains:

```
project_plan.json        bill_of_materials.json   wiring_table.csv   pin_map.json
firmware/sketch.ino
simulation/diagram.json  simulation/wokwi.toml
validation/validation_report.{json,md}
simulation_logs/serial_output.txt  simulation_logs/simulator_status.json
renders/circuit_diagram.svg  renders/breadboard_style.svg  (+ .png when matplotlib is installed)
report/report.md  report/report.html  report/educational_explanation.md
metrics.json
```

Outputs are git-ignored by default (see `.gitignore`); copy a run here and
remove it from the ignore list if you want to commit a reference snapshot.
