"""RoboMentor command-line interface.

Uses argparse (always available) so the CLI works in a bare Python environment.
Commands:

    generate     build a full project from materials + a request
    validate     re-run validators on an existing project folder
    simulate     run a simulation backend on an existing project
    render       (re)generate circuit visuals for an existing project
    explain      print/regenerate the educational explanation
    list-boards  show supported boards
    list-parts   show known parts
    create-skill write the RoboMentor Claude Skill to a folder
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__, board_profiles, part_library, project_io, validators
from .config import RunConfig


# --------------------------------------------------------------------------- #
# Pretty printing helpers
# --------------------------------------------------------------------------- #
def _hr(title: str = "") -> None:
    print("\n" + "=" * 70)
    if title:
        print(title)
        print("=" * 70)


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #
def cmd_generate(args: argparse.Namespace) -> int:
    from .agents import run_generation

    cfg = RunConfig(
        materials_path=Path(args.materials) if args.materials else None,
        request_path=Path(args.request) if args.request else None,
        request_text=args.request_text or "",
        out_dir=Path(args.out),
        board=args.board,
        simulate=args.simulate,
        render=args.render,
        llm_provider=args.llm,
        seed=args.seed,
        timeout_sec=args.timeout,
        project_hint=args.project,
    )
    _hr("RoboMentor — generate")
    result = run_generation(cfg)

    if result.material_warnings:
        print("\nMaterial parsing notes:")
        for w in result.material_warnings:
            print(f"  - {w}")

    print("\nStatus:")
    for m in result.messages:
        print(f"  • {m}")

    print("\nPlanner reasoning:")
    print(f"  {result.plan.reasoning_summary}")

    if result.plan.warnings:
        print("\nWarnings:")
        for w in result.plan.warnings:
            print(f"  ⚠️  {w}")

    _hr("Output")
    print(f"  Project folder : {result.out_dir}")
    print(f"  Firmware       : {result.out_dir / 'firmware' / 'sketch.ino'}")
    print(f"  Wokwi diagram  : {result.out_dir / 'simulation' / 'diagram.json'}")
    print(f"  Validation     : {result.out_dir / 'validation' / 'validation_report.md'}")
    print(f"  Report (HTML)  : {result.out_dir / 'report' / 'report.html'}")
    print(f"  Metrics        : {result.out_dir / 'metrics.json'}")
    print(f"\n  Validation: {'PASSED ✅' if result.validation.passed else 'FAILED ❌'}  "
          f"({len(result.validation.errors)} errors, {len(result.validation.warnings)} warnings)")
    return 0 if result.validation.passed else 2


def cmd_validate(args: argparse.Namespace) -> int:
    proj = project_io.load_project(Path(args.project))
    report = validators.run_all(proj.circuit, proj.firmware, proj.plan)
    project_io.write_validation(Path(args.project), report)
    _hr("RoboMentor — validate")
    print(f"Project: {args.project}")
    print(f"Result : {'PASSED ✅' if report.passed else 'FAILED ❌'}")
    print(f"Errors : {len(report.errors)} | Warnings: {len(report.warnings)} | Info: {len(report.infos)}")
    for i in report.errors + report.warnings:
        print(f"  [{i.severity.upper()}] {i.code}: {i.message}")
    return 0 if report.passed else 2


def cmd_simulate(args: argparse.Namespace) -> int:
    from .simulators import simulate

    result = simulate(Path(args.project), mode=args.backend, timeout_sec=args.timeout)
    project_io.write_simulation_logs(Path(args.project), result)
    _hr("RoboMentor — simulate")
    print(f"Backend  : {result.backend}")
    print(f"Available: {result.available}")
    print(f"Success  : {result.success}")
    print(f"Message  : {result.message}")
    print(f"Logs     : {Path(args.project) / 'simulation_logs'}")
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    from .renderers import circuit_plotter, graphviz_renderer

    proj = project_io.load_project(Path(args.project))
    renders_dir = project_io.paths(Path(args.project))["renders"]
    produced = circuit_plotter.render_all(proj.circuit, renders_dir, level="high")
    if args.style in ("all", "graphviz"):
        produced.update(graphviz_renderer.render_graphviz(proj.circuit, renders_dir))
    _hr("RoboMentor — render")
    print(f"Project: {args.project}")
    for name, path in produced.items():
        print(f"  {name}: {path}")
    return 0


def cmd_explain(args: argparse.Namespace) -> int:
    from .agents.explanation_agent import ExplanationAgent
    from .llm import get_provider

    proj = project_io.load_project(Path(args.project))
    agent = ExplanationAgent(get_provider(args.llm))
    bundle = agent.run(proj.plan, proj.circuit)
    out = Path(args.project) / "report" / "educational_explanation.md"
    from .utils import write_text
    write_text(out, bundle["explanation_md"])
    _hr("RoboMentor — explain")
    print(bundle["explanation_md"])
    print(f"\n(written to {out})")
    return 0


def cmd_list_boards(args: argparse.Namespace) -> int:
    _hr("Supported boards")
    for bid, b in board_profiles.all_boards().items():
        print(f"\n• {bid}  —  {b.name}")
        print(f"    logic {b.logic_voltage}V | wokwi: {b.wokwi_support} ({b.wokwi_id})")
        print(f"    digital: {len(b.all_pins())} pins | analog: {', '.join(b.analog_pins) or '—'}")
        print(f"    pwm: {', '.join(b.pwm_pins) or '—'}")
        print(f"    i2c: {b.i2c_pins} | uart: {b.uart_pins}")
        if b.notes:
            print(f"    note: {b.notes[0]}")
    return 0


def cmd_list_parts(args: argparse.Namespace) -> int:
    _hr("Known parts")
    for ptype, p in part_library.all_parts().items():
        print(f"• {ptype:<24} [{p.category:<13}] sim:{p.simulation_available:<8} "
              f"wokwi:{p.wokwi_id or '—'}")
        print(f"    {p.explanation}")
    return 0


def cmd_create_skill(args: argparse.Namespace) -> int:
    from .utils import ensure_dir, read_text, write_text

    out = ensure_dir(Path(args.out))
    src_skill = Path(__file__).resolve().parent.parent / "skills" / "robo-mentor" / "SKILL.md"
    if src_skill.exists():
        write_text(out / "SKILL.md", read_text(src_skill))
        print(f"Copied SKILL.md to {out / 'SKILL.md'}")
    else:
        write_text(out / "SKILL.md", _MINIMAL_SKILL)
        print(f"Wrote a minimal SKILL.md to {out / 'SKILL.md'} (source skill not found).")
    return 0


_MINIMAL_SKILL = """---
name: RoboMentor
description: Generate material-aware microcontroller projects for high-school robotics.
---
# RoboMentor
Run: `python -m robomentor.cli generate --materials materials.json --request request.txt --out outputs/demo --board auto --simulate auto --render high`
"""


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="robomentor",
        description="RoboMentor — material-aware robotics education toolchain.",
    )
    p.add_argument("--version", action="version", version=f"RoboMentor {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    g = sub.add_parser("generate", help="generate a full project")
    g.add_argument("--materials", help="path to a materials JSON/YAML file")
    g.add_argument("--request", help="path to a request .txt file")
    g.add_argument("--request-text", help="inline request text (alternative to --request)")
    g.add_argument("--out", required=True, help="output project folder")
    g.add_argument("--board", default="auto", help="board id or 'auto'")
    g.add_argument("--simulate", default="auto", choices=["auto", "static", "wokwi", "none"])
    g.add_argument("--render", default="high", choices=["none", "basic", "high"])
    g.add_argument("--llm", default="heuristic",
                   choices=["heuristic", "openai", "anthropic", "groq", "ollama"])
    g.add_argument("--project", default=None, help="force a template/project key")
    g.add_argument("--seed", type=int, default=1337)
    g.add_argument("--timeout", type=int, default=30)
    g.set_defaults(func=cmd_generate)

    v = sub.add_parser("validate", help="validate an existing project")
    v.add_argument("--project", required=True)
    v.set_defaults(func=cmd_validate)

    s = sub.add_parser("simulate", help="simulate an existing project")
    s.add_argument("--project", required=True)
    s.add_argument("--backend", default="auto", choices=["auto", "static", "wokwi", "none"])
    s.add_argument("--timeout", type=int, default=30)
    s.set_defaults(func=cmd_simulate)

    r = sub.add_parser("render", help="render circuit visuals for a project")
    r.add_argument("--project", required=True)
    r.add_argument("--style", default="all", choices=["all", "svg", "png", "graphviz"])
    r.set_defaults(func=cmd_render)

    e = sub.add_parser("explain", help="generate the educational explanation")
    e.add_argument("--project", required=True)
    e.add_argument("--llm", default="heuristic",
                   choices=["heuristic", "openai", "anthropic", "groq", "ollama"])
    e.set_defaults(func=cmd_explain)

    sub.add_parser("list-boards", help="list supported boards").set_defaults(func=cmd_list_boards)
    sub.add_parser("list-parts", help="list known parts").set_defaults(func=cmd_list_parts)

    cs = sub.add_parser("create-skill", help="write the RoboMentor Claude Skill")
    cs.add_argument("--out", default="skills/robo-mentor")
    cs.set_defaults(func=cmd_create_skill)

    return p


def _make_stdout_utf8() -> None:
    # Windows consoles often default to cp1252 and choke on emoji/box chars.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass


def main(argv=None) -> int:
    _make_stdout_utf8()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130
    except Exception as exc:  # keep the CLI from dumping a raw traceback at users
        print(f"\nERROR: {exc}", file=sys.stderr)
        if "--debug" in (argv or sys.argv):
            raise
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
