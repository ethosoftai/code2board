"""Circuit visual renderers.

Two independent paths, so renders are produced even in a bare environment:

* **Hand-rolled SVG** (pure Python, *always* available) — a clean wiring graph
  and a breadboard-style schematic. These are deterministic and look good in a
  workshop paper.
* **Matplotlib + NetworkX** (optional) — PNG versions at high DPI when those
  libraries are installed.

``render_all`` returns a mapping of artifact name -> path for everything it
managed to produce, so the report can embed whatever exists.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Tuple

from ..schemas import Circuit
from ..utils import HAS_MATPLOTLIB, HAS_NETWORKX, category_color, ensure_dir, net_color, write_text


# --------------------------------------------------------------------------- #
# Layout helper: assign every component to a column based on its role.
# --------------------------------------------------------------------------- #
def _layout(circuit: Circuit) -> Dict[str, Tuple[float, float]]:
    """Return {component_id: (x, y)} on a 1920x1080 canvas. 'board' included."""
    W, H = 1920.0, 1080.0
    pos: Dict[str, Tuple[float, float]] = {"board": (W / 2, H / 2)}

    left, right, top, bottom = [], [], [], []
    for c in circuit.components:
        if c.category == "sensor":
            left.append(c.id)
        elif c.category in ("actuator", "display"):
            right.append(c.id)
        elif c.category == "power":
            bottom.append(c.id)
        else:  # passive / board_support
            top.append(c.id)

    def spread(ids: List[str], x: float, y0: float, y1: float) -> None:
        n = len(ids)
        if n == 0:
            return
        for i, cid in enumerate(ids):
            y = y0 + (y1 - y0) * (i + 1) / (n + 1)
            pos[cid] = (x, y)

    spread(left, W * 0.13, 120, H - 120)
    spread(right, W * 0.87, 120, H - 120)
    spread(top, W * 0.5, 90, 90)  # will be re-spread horizontally below
    spread(bottom, W * 0.5, H - 90, H - 90)

    # re-spread top/bottom horizontally so they don't stack on one point
    def spread_h(ids: List[str], y: float) -> None:
        n = len(ids)
        for i, cid in enumerate(ids):
            x = W * (0.30 + 0.40 * (i + 1) / (n + 1)) if n else W * 0.5
            pos[cid] = (x, y)

    spread_h(top, 90)
    spread_h(bottom, H - 90)
    return pos


# --------------------------------------------------------------------------- #
# Hand-rolled SVG
# --------------------------------------------------------------------------- #
def _svg_box(x: float, y: float, w: float, h: float, fill: str, label: str,
             sub: str = "") -> str:
    parts = [
        f'<rect x="{x - w/2:.1f}" y="{y - h/2:.1f}" width="{w:.1f}" height="{h:.1f}" '
        f'rx="12" ry="12" fill="{fill}" stroke="#1b2631" stroke-width="2"/>',
        f'<text x="{x:.1f}" y="{y - (4 if sub else -4):.1f}" text-anchor="middle" '
        f'font-family="Helvetica,Arial,sans-serif" font-size="20" font-weight="bold" '
        f'fill="#ffffff">{_esc(label)}</text>',
    ]
    if sub:
        parts.append(
            f'<text x="{x:.1f}" y="{y + 22:.1f}" text-anchor="middle" '
            f'font-family="Helvetica,Arial,sans-serif" font-size="14" fill="#ecf0f1">{_esc(sub)}</text>'
        )
    return "\n".join(parts)


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_svg(circuit: Circuit) -> str:
    W, H = 1920, 1080
    pos = _layout(circuit)
    comp_by_id = {c.id: c for c in circuit.components}

    svg: List[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'font-family="Helvetica,Arial,sans-serif">',
        f'<rect width="{W}" height="{H}" fill="#f7f9fb"/>',
        f'<text x="{W/2}" y="44" text-anchor="middle" font-size="30" font-weight="bold" '
        f'fill="#1b2631">RoboMentor wiring diagram — {_esc(circuit.board.name)}</text>',
    ]

    # Draw wires first (under the boxes). Group identical endpoints, offset labels.
    drawn_labels: Dict[Tuple[int, int], int] = {}
    for c in circuit.connections:
        x1, y1 = pos.get(c.from_part, (W / 2, H / 2))
        x2, y2 = pos.get(c.to_part, (W / 2, H / 2))
        color = c.color or net_color(c.net)
        svg.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{color}" stroke-width="3" opacity="0.75"/>'
        )
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        key = (int(mx // 40), int(my // 20))
        offset = drawn_labels.get(key, 0)
        drawn_labels[key] = offset + 1
        label = f"{c.from_pin}→{c.to_pin}"
        svg.append(
            f'<text x="{mx:.1f}" y="{my + offset * 16:.1f}" text-anchor="middle" '
            f'font-size="13" fill="{color}" stroke="#f7f9fb" stroke-width="0.6" '
            f'paint-order="stroke">{_esc(label)}</text>'
        )

    # Board
    bx, by = pos["board"]
    svg.append(_svg_box(bx, by, 230, 120, category_color("board"),
                        circuit.board.name.split("(")[0].strip(), f"{circuit.board.logic_voltage}V logic"))

    # Components
    for cid, (x, y) in pos.items():
        if cid == "board":
            continue
        comp = comp_by_id.get(cid)
        if not comp:
            continue
        svg.append(_svg_box(x, y, 180, 80, category_color(comp.category), comp.label, comp.part_type))

    # Legend
    legend_items = [("Power", net_color("power")), ("Ground", net_color("ground")),
                    ("Signal", net_color("signal")), ("PWM", net_color("pwm")),
                    ("I2C", net_color("i2c"))]
    lx, ly = 40, H - 40
    for i, (name, color) in enumerate(legend_items):
        x = lx + i * 150
        svg.append(f'<line x1="{x}" y1="{ly}" x2="{x+28}" y2="{ly}" stroke="{color}" stroke-width="5"/>')
        svg.append(f'<text x="{x+34}" y="{ly+5}" font-size="16" fill="#1b2631">{name}</text>')

    svg.append("</svg>")
    return "\n".join(svg)


def render_breadboard_svg(circuit: Circuit) -> str:
    """A cleaner, breadboard-flavoured schematic approximation in SVG."""
    W, H = 1920, 1080
    svg: List[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'font-family="Helvetica,Arial,sans-serif">',
        f'<rect width="{W}" height="{H}" fill="#fffdf5"/>',
        f'<text x="{W/2}" y="44" text-anchor="middle" font-size="30" font-weight="bold" '
        f'fill="#1b2631">RoboMentor breadboard-style layout — {_esc(circuit.board.name)}</text>',
    ]
    # Power rails
    svg.append(f'<rect x="80" y="90" width="{W-160}" height="24" fill="#e74c3c" opacity="0.85"/>')
    svg.append(f'<text x="90" y="108" font-size="16" fill="#fff">+ VCC rail</text>')
    svg.append(f'<rect x="80" y="{H-130}" width="{W-160}" height="24" fill="#2c3e50" opacity="0.9"/>')
    svg.append(f'<text x="90" y="{H-112}" font-size="16" fill="#fff">- GND rail</text>')

    # Board in centre-left
    svg.append('<rect x="120" y="380" width="360" height="320" rx="14" fill="#16435f" stroke="#0b2233" stroke-width="3"/>')
    svg.append(f'<text x="300" y="360" text-anchor="middle" font-size="22" font-weight="bold" fill="#16435f">{_esc(circuit.board.name.split("(")[0])}</text>')
    # draw a few pin pads
    for i, pin in enumerate(circuit.board.all_pins()[:16]):
        px = 150 + (i % 8) * 42
        py = 410 + (i // 8) * 250
        svg.append(f'<circle cx="{px}" cy="{py}" r="6" fill="#f1c40f"/>')
        svg.append(f'<text x="{px}" y="{py-10}" text-anchor="middle" font-size="11" fill="#ecf0f1">{_esc(pin)}</text>')

    # Components on the right as chips
    comps = [c for c in circuit.components]
    cols = 3
    for i, comp in enumerate(comps):
        cx = 620 + (i % cols) * 400
        cy = 200 + (i // cols) * 200
        svg.append(f'<rect x="{cx}" y="{cy}" width="320" height="120" rx="12" '
                   f'fill="{category_color(comp.category)}" stroke="#1b2631" stroke-width="2"/>')
        svg.append(f'<text x="{cx+160}" y="{cy+50}" text-anchor="middle" font-size="20" '
                   f'font-weight="bold" fill="#fff">{_esc(comp.label)}</text>')
        svg.append(f'<text x="{cx+160}" y="{cy+80}" text-anchor="middle" font-size="14" '
                   f'fill="#ecf0f1">{_esc(comp.part_type)}</text>')

    # Pin map note
    pm = ", ".join(f"{k}={v}" for k, v in list(circuit.pin_map.items())[:10])
    svg.append(f'<text x="80" y="{H-150}" font-size="15" fill="#34495e">Pins: {_esc(pm)}</text>')
    svg.append("</svg>")
    return "\n".join(svg)


# --------------------------------------------------------------------------- #
# Matplotlib / NetworkX PNG path (optional)
# --------------------------------------------------------------------------- #
def _render_wiring_png(circuit: Circuit, out_png: Path) -> bool:
    if not (HAS_MATPLOTLIB and HAS_NETWORKX):
        return False
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import networkx as nx

    G = nx.MultiGraph()
    G.add_node("board", label=circuit.board.name.split("(")[0].strip(), color=category_color("board"))
    for c in circuit.components:
        G.add_node(c.id, label=c.label, color=category_color(c.category))
    for c in circuit.connections:
        G.add_edge(c.from_part, c.to_part, color=c.color, net=c.net)

    pos_px = _layout(circuit)
    pos = {k: (x / 1920.0, 1 - y / 1080.0) for k, (x, y) in pos_px.items() if k in G}

    fig, ax = plt.subplots(figsize=(19.2, 10.8), dpi=100)
    node_colors = [G.nodes[n].get("color", "#34495e") for n in G.nodes]
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=2600, ax=ax,
                           edgecolors="#1b2631", linewidths=1.5)
    edge_colors = [d.get("color", "#2c3e50") for *_e, d in G.edges(data=True)]
    nx.draw_networkx_edges(G, pos, edge_color=edge_colors, width=2.0, ax=ax, alpha=0.7)
    labels = {n: G.nodes[n].get("label", n) for n in G.nodes}
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=9, font_color="white", ax=ax)
    ax.set_title(f"RoboMentor wiring graph — {circuit.board.name}", fontsize=16, fontweight="bold")
    ax.axis("off")
    fig.tight_layout()
    ensure_dir(out_png.parent)
    fig.savefig(out_png, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return True


def _render_breadboard_png(circuit: Circuit, out_png: Path) -> bool:
    if not HAS_MATPLOTLIB:
        return False
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch

    fig, ax = plt.subplots(figsize=(19.2, 10.8), dpi=100)
    ax.set_xlim(0, 1920)
    ax.set_ylim(0, 1080)
    ax.invert_yaxis()
    ax.axis("off")
    ax.add_patch(plt.Rectangle((80, 60), 1760, 24, color="#e74c3c", alpha=0.85))
    ax.text(90, 78, "+ VCC rail", color="white", fontsize=12, va="center")
    ax.add_patch(plt.Rectangle((80, 996), 1760, 24, color="#2c3e50"))
    ax.text(90, 1012, "- GND rail", color="white", fontsize=12, va="center")

    def chip(x, y, w, h, color, title, sub):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=8,rounding_size=12",
                                    fc=color, ec="#1b2631", lw=1.5))
        ax.text(x + w / 2, y + h / 2 - 8, title, ha="center", va="center",
                color="white", fontsize=13, fontweight="bold")
        ax.text(x + w / 2, y + h / 2 + 18, sub, ha="center", va="center",
                color="#ecf0f1", fontsize=10)

    chip(140, 400, 360, 300, "#16435f", circuit.board.name.split("(")[0].strip(),
         f"{circuit.board.logic_voltage}V")
    cols = 3
    for i, comp in enumerate(circuit.components):
        cx = 640 + (i % cols) * 400
        cy = 180 + (i // cols) * 200
        chip(cx, cy, 320, 120, category_color(comp.category), comp.label, comp.part_type)

    ax.set_title(f"RoboMentor breadboard-style layout — {circuit.board.name}",
                 fontsize=16, fontweight="bold")
    fig.tight_layout()
    ensure_dir(out_png.parent)
    fig.savefig(out_png, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return True


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def render_all(circuit: Circuit, renders_dir: Path, level: str = "high") -> Dict[str, str]:
    renders_dir = ensure_dir(Path(renders_dir))
    produced: Dict[str, str] = {}

    # SVGs are always produced (pure Python).
    svg_main = renders_dir / "circuit_diagram.svg"
    write_text(svg_main, render_svg(circuit))
    produced["circuit_diagram_svg"] = str(svg_main)

    bb_svg = renders_dir / "breadboard_style.svg"
    write_text(bb_svg, render_breadboard_svg(circuit))
    produced["breadboard_style_svg"] = str(bb_svg)

    # PNGs (matplotlib / networkx). On high level we also do the wiring graph.
    png_main = renders_dir / "circuit_diagram.png"
    if _render_wiring_png(circuit, png_main):
        produced["circuit_diagram_png"] = str(png_main)

    wiring_png = renders_dir / "wiring_graph.png"
    if _render_wiring_png(circuit, wiring_png):
        produced["wiring_graph_png"] = str(wiring_png)

    bb_png = renders_dir / "breadboard_style.png"
    if _render_breadboard_png(circuit, bb_png):
        produced["breadboard_style_png"] = str(bb_png)

    if not HAS_MATPLOTLIB:
        note = renders_dir / "RENDER_NOTE.txt"
        write_text(note, (
            "Matplotlib/NetworkX are not installed, so PNG renders were skipped.\n"
            "High-quality SVG renders were generated instead (open the .svg files).\n"
            "Install extras for PNGs:  pip install matplotlib networkx\n"
        ))
        produced["render_note"] = str(note)

    return produced
