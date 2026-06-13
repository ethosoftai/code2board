# RoboMentor 🤖

**A material-aware LLM-agent toolchain that turns a box of electronics parts and a
sentence ("I want a robot that follows a line") into a complete, validated,
simulation-ready microcontroller project — firmware, circuit diagram, renders,
validation report, and a step-by-step explanation for high-school students.**

RoboMentor is built for **RoboCup Junior / WEROB-style educational robotics
workshops**: reproducible, demo-friendly, and research-friendly. It runs **fully
offline with no API keys** — optional Wokwi, LLM providers, and Matplotlib only
enhance the output.

---

## Why this matters for high-school robotics education

Most "AI Arduino code generators" hallucinate wiring, ignore the parts a student
actually owns, and never check whether the code matches the circuit. RoboMentor
is the opposite:

- **Material-aware** — it only designs with parts the student has, and explicitly
  flags any missing required/optional parts.
- **Validation-aware** — every project is checked for pin, power, code↔circuit and
  Wokwi-diagram consistency *before* it is presented.
- **Simulation-aware** — it emits Wokwi-compatible project files and runs a
  simulation backend (or a graceful static fallback).
- **Education-aware** — it explains the design like a patient club mentor, with
  learning objectives and a troubleshooting checklist.
- **Research-aware** — it logs metrics, validation results, and artifacts for a
  workshop paper.

## Features

- 🧩 Parses a JSON/YAML material list (boards, parts, constraints).
- 🧠 Deterministic **planner** that picks a feasible project + board.
- 🔌 **Circuit generator** with deterministic pin assignment → Wokwi `diagram.json`,
  CSV wiring table, Graphviz DOT, JSON pin map, Markdown wiring guide.
- 💾 **Firmware generator** (Arduino C++) whose pins exactly match the diagram,
  with serial debug, tunable speeds, and a `SELF_TEST` mode.
- ✅ Five serious **validators**: pin, power/safety, code↔circuit, Wokwi, and
  educational-safety.
- 🧪 **Simulation backends**: Wokwi CLI, optional Wokwi Python client, and an
  always-available local static backend.
- 🎨 **High-quality renders**: hand-rolled SVG (always) + Matplotlib/NetworkX PNGs
  (wiring graph + breadboard-style layout).
- 📄 Clean **HTML + Markdown reports** and an educational explanation.
- 🤝 A reusable **Claude Skill** (`skills/robo-mentor/SKILL.md`).
- 🔁 Pluggable **LLM providers**: heuristic (default, offline), OpenAI, Anthropic,
  Groq, Ollama.

## Supported boards & parts

**Boards:** `arduino_uno`, `arduino_nano`, `arduino_mega`, `esp32_devkit_v1`,
`raspberry_pi_pico`, `raspberry_pi_pico_w`, `stm32_nucleo_basic`.

**Parts (20+):** LEDs/RGB LED, resistors, button, potentiometer, buzzer, SG90
servo, DC motor, L298N & TB6612FNG drivers, IR line sensor, HC-SR04, DHT22, LDR,
soil moisture, OLED (I2C), 16x2 LCD, MPU6050, breadboard, jumpers, battery pack,
power rail.

Run `python -m robomentor.cli list-boards` / `list-parts` to see everything.

## Project templates

| Template | What it builds |
|----------|----------------|
| `arduino_line_follower_v1` | Two-IR-sensor line follower with motor driver |
| `obstacle_avoider_v1` | HC-SR04 obstacle avoider (+ optional scanning servo) |
| `traffic_light_v1` | Red/yellow/green traffic light (+ button/buzzer) |
| `smart_greenhouse_v1` | Temp/humidity/light/soil monitor with alerts/display |

## Installation

Requires **Python 3.10+**. RoboMentor runs with **zero** third-party packages.

```bash
git clone <this-repo>
cd robomentor

# Optional but recommended for PNG renders:
pip install matplotlib networkx

# Everything (renders, YAML, HTML templating, LLM providers, tests):
pip install -e ".[all]"
```

## Quickstart — the line-follower demo

```bash
python -m robomentor.cli generate \
  --materials examples/materials/beginner_arduino_kit.json \
  --request examples/requests/line_follower.txt \
  --out outputs/line_follower_demo \
  --board arduino_uno \
  --simulate static \
  --render high
```

This generates a complete Arduino line-follower package and prints a status
summary. **It never crashes if Wokwi isn't installed** — it says so and uses the
static backend instead.

### Conceptual wiring it produces

```
Arduino D2  -> Left  IR sensor OUT      5V  -> IR sensors VCC
Arduino D3  -> Right IR sensor OUT      GND -> IR sensors GND
Arduino D5/D6 -> L298N IN1/IN2          GND -> L298N GND (common ground)
Arduino D7/D8 -> L298N IN3/IN4          Battery+ -> L298N VCC (external motor power)
Arduino D9 (PWM) -> L298N ENA           Battery- -> L298N GND & Arduino GND
Arduino D10 (PWM) -> L298N ENB
```

## Generated outputs

```
outputs/line_follower_demo/
  project_plan.json        bill_of_materials.json   wiring_table.csv   pin_map.json
  firmware/sketch.ino
  simulation/diagram.json  simulation/wokwi.toml    simulation/circuit_internal.json
  validation/validation_report.{json,md}
  simulation_logs/serial_output.txt   simulation_logs/simulator_status.json
  renders/circuit_diagram.{svg,png}   renders/wiring_graph.png
  renders/breadboard_style.{svg,png}  renders/wiring_graph.dot
  report/report.md  report/report.html  report/educational_explanation.md
  metrics.json
```

## All CLI commands

```bash
python -m robomentor.cli generate    --materials M.json --request R.txt --out DIR [--board auto] [--simulate auto] [--render high] [--llm heuristic]
python -m robomentor.cli validate    --project DIR
python -m robomentor.cli simulate    --project DIR --backend auto
python -m robomentor.cli render      --project DIR --style all
python -m robomentor.cli explain     --project DIR
python -m robomentor.cli list-boards
python -m robomentor.cli list-parts
python -m robomentor.cli create-skill --out skills/robo-mentor
```

## Wokwi simulation

RoboMentor writes a Wokwi-compatible `simulation/diagram.json` plus a
`simulation/wokwi.toml`. With `--simulate auto` it detects `wokwi-cli` on your
PATH and runs it **if a compiled firmware binary is present**.

> RoboMentor generates firmware *source*, not a compiled binary. To run a real
> Wokwi simulation, compile `firmware/sketch.ino` (Arduino CLI / PlatformIO) into
> a `.hex`/`.elf`/`.uf2` and update `wokwi.toml`. Until then, the static backend
> runs — and RoboMentor **never claims a successful simulation that didn't
> happen** (it reports the actual backend in `simulator_status.json`).

### Fallback static simulation

The local static backend is **always available**. It performs static analysis —
confirms `setup()`/`loop()`/`Serial` exist, counts pin constants, validates the
diagram JSON — and synthesises an illustrative serial transcript so demos always
have something to show. It is clearly labelled as *not* an electrical simulation.

## Renders / screenshots

Open `report/report.html` for a clean, self-contained dashboard (local CSS, no
CDN) embedding the circuit renders. Even with no extra packages installed you get
high-quality **SVG** wiring diagrams and breadboard-style layouts; install
`matplotlib networkx` to also get **PNG** wiring graphs and breadboard renders at
1920×1080.

| `circuit_diagram.svg` | `breadboard_style.svg` | `wiring_graph.png` |
|---|---|---|
| Board-centred wiring graph, colour-coded nets, labelled pins | Breadboard-style chip layout with power rails | NetworkX/Matplotlib graph |

## Research / workshop use case

Each run emits `metrics.json` (project type, board, #parts, #connections,
validation errors/warnings, simulation backend & success, firmware lines, render
count, timestamp). Point the tool at a folder of student kits + requests to
produce a reproducible dataset of generated projects and their validation outcomes
for a workshop paper.

## LLM providers

The default `heuristic` provider is deterministic and offline. Optional providers
(`openai`, `anthropic`, `groq`, `ollama`) read their API keys from the
environment and **only enrich the educational explanation / reasoning summary** —
they never rewrite validated firmware. If a key is missing or the service is
unreachable, RoboMentor silently falls back to heuristic mode.

```bash
setx ANTHROPIC_API_KEY "sk-..."   # Windows
python -m robomentor.cli generate ... --llm anthropic
```

## Testing

```bash
pip install pytest
python -m pytest
```

The suite (no external APIs) covers the material parser, planner selection, all
key validators, Wokwi diagram generation, and a full CLI generation smoke test.

## Limitations

- STM32 Nucleo and other non-Arduino-Uno pin maps are **approximate**; verify
  against your exact board variant.
- Some parts (motor drivers, IR sensors, soil probe) have **partial** Wokwi
  support — local renders always work, but a full Wokwi run may need substitute
  parts.
- RoboMentor generates firmware source + project files; it does **not** compile.
- The static backend is analysis, not electrical simulation.

## Future work

- Compile-and-run integration (Arduino CLI / PlatformIO) so `wokwi-cli` runs
  end-to-end automatically.
- MicroPython firmware variants for ESP32/Pico.
- More templates (robot arm, weather station, balancing bot) and more parts.
- A verified Wokwi Python-client backend behind the existing feature flag.
- LLM-assisted material inference from a photo of a kit.

## Safety

Build with the power **off**, share a common ground, never drive motors directly
from a GPIO pin, and always use a resistor with an LED. **Simulation is a learning
aid, not a guarantee of real-world behaviour.**

## License

MIT — see [LICENSE](LICENSE).
