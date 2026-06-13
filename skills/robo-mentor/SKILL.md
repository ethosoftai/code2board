---
name: RoboMentor
description: >
  Generate feasible, material-aware microcontroller robotics projects for
  high-school students. Use when a student provides a list of electronics parts
  (Arduino/ESP32/Pico/STM32 + sensors/actuators) and a natural-language project
  idea, and wants firmware, a wiring/circuit diagram, validation, simulation
  files, visual renders, and a step-by-step educational explanation.
---

# RoboMentor

RoboMentor is a toolchain that turns **"here are my parts + here's what I want to
build"** into a complete, validated, simulation-ready microcontroller project
with firmware, a Wokwi-compatible circuit diagram, circuit renders, a validation
report, and a student-friendly explanation.

It runs **fully offline** with no API keys (deterministic heuristic mode). Wokwi
CLI, optional LLM providers, and Matplotlib/Graphviz only enhance the output.

## When to use this skill

Use RoboMentor when the user:

- Lists robotics/electronics materials and asks what they can build, **or**
- Describes a project idea (line follower, obstacle avoider, traffic light,
  greenhouse/plant monitor, etc.) and wants working firmware + wiring, **or**
- Needs a reproducible, demo-friendly project bundle for a workshop/paper
  (RoboCup Junior / WEROB style).

Do **not** use it for general (non-embedded) software questions.

## Required inputs

1. **Materials list** — a JSON (or YAML) file describing available boards, parts
   and constraints. Example:

   ```json
   {
     "student_level": "beginner",
     "available_boards": [{"type": "arduino_uno", "quantity": 1}],
     "parts": [
       {"type": "ir_line_sensor", "quantity": 2},
       {"type": "dc_motor", "quantity": 2},
       {"type": "l298n_motor_driver", "quantity": 1}
     ],
     "constraints": {"avoid_soldering": true, "prefer_simulation": true}
   }
   ```

2. **Project request** — a short natural-language `.txt` (or inline text), e.g.
   *"a robot that follows a black line and prints debug info"*.

If the user hasn't given a material list, **ask for one** or infer a reasonable
beginner kit and state the assumption. Convert the user's idea into a concise
request string before running.

## Expected outputs

A project folder containing:

```
project_plan.json   bill_of_materials.json   wiring_table.csv   pin_map.json
firmware/sketch.ino
simulation/diagram.json   simulation/wokwi.toml
validation/validation_report.{json,md}
simulation_logs/serial_output.txt   simulation_logs/simulator_status.json
renders/circuit_diagram.svg  renders/breadboard_style.svg  (+ PNGs with matplotlib)
report/report.md  report/report.html  report/educational_explanation.md
metrics.json
```

## CLI commands

```bash
# Full generation (the main command)
python -m robomentor.cli generate \
  --materials materials.json \
  --request request.txt \
  --out outputs/demo \
  --board auto \
  --simulate auto \
  --render high

# Re-run after edits
python -m robomentor.cli validate  --project outputs/demo
python -m robomentor.cli simulate  --project outputs/demo --backend auto
python -m robomentor.cli render    --project outputs/demo --style all
python -m robomentor.cli explain   --project outputs/demo

# Discovery
python -m robomentor.cli list-boards
python -m robomentor.cli list-parts
```

`--board` accepts: `arduino_uno`, `arduino_nano`, `arduino_mega`,
`esp32_devkit_v1`, `raspberry_pi_pico`, `raspberry_pi_pico_w`,
`stm32_nucleo_basic`, or `auto`.

## Recommended workflow for Claude

1. **Get materials.** Ask for or infer the material list; write it to a JSON file.
2. **Frame the request.** Turn the student's idea into a one-paragraph request.
3. **Generate.** Run `robomentor generate ... --simulate auto --render high`.
4. **Inspect validation.** Read `validation/validation_report.md` and `metrics.json`.
5. **If validation FAILED** (errors > 0): the debug agent already attempted a
   repair; if errors remain they are almost always *missing required parts* —
   tell the student exactly which part to add, or re-run with a different
   `--board`/`--project`. Do not present a project as working if validation
   failed.
6. **Present the result** clearly:
   - project summary + selected board,
   - required parts (bill of materials),
   - the wiring table,
   - firmware path (`firmware/sketch.ino`),
   - diagram + render paths,
   - simulation result (which backend, success/fallback),
   - warnings and safety notes,
   - next steps (open the HTML report, try `SELF_TEST`, tweak a tunable value).

## Validation policy

- Always read the validation report before claiming success.
- Treat ERRORS as blocking; WARNINGS and INFO are teaching points to mention.
- Never silently ignore a `motor_direct_drive`, `no_common_ground`, or
  `pin_conflict` error.

## Simulation policy

- `auto` uses Wokwi CLI **if installed and a compiled binary exists**, otherwise
  falls back to the local static backend. RoboMentor generates firmware *source*,
  not binaries, so full Wokwi runs may require the student to compile first.
- Never claim a "successful simulation" when only static validation ran — report
  the actual backend (`simulator_status.json`).

## Rendering policy

- SVG renders are always produced (no dependencies).
- PNG renders require Matplotlib/NetworkX; if missing, point the user to the SVGs
  and mention `pip install matplotlib networkx` for PNGs.

## Educational explanation policy

- Explanations target ~15-year-olds: clear, encouraging, step-by-step.
- Always include the "sense → think → act" loop framing and practical safety.
- Provide learning objectives and a troubleshooting checklist.

## Limitations

- Pin maps for STM32 Nucleo and exotic boards are **approximate**; verify against
  the exact variant.
- Some parts (motor drivers, IR sensors, soil probe) have **partial** Wokwi
  support — local renders work but full simulation may need substitute parts.
- RoboMentor does not compile firmware; it generates source + project files.

## Safety notes

- Motors/batteries deliver real current — build with power off, share a common
  ground, never drive motors directly from a GPIO, and always use a resistor with
  an LED. Simulation is a guide, not a guarantee of real-world behaviour.
