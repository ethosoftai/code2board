"""Optional Graphviz renderer.

Renders the circuit DOT (from :func:`circuit_generator.to_dot`) to PNG/SVG when
the ``graphviz`` Python package *and* the system ``dot`` binary are available.
Always writes the ``.dot`` source so the artifact exists regardless.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from ..circuit_generator import to_dot
from ..schemas import Circuit
from ..utils import HAS_GRAPHVIZ, ensure_dir, write_text


def render_graphviz(circuit: Circuit, out_dir: Path) -> Dict[str, str]:
    out_dir = ensure_dir(Path(out_dir))
    produced: Dict[str, str] = {}

    dot_src = to_dot(circuit)
    dot_path = out_dir / "wiring_graph.dot"
    write_text(dot_path, dot_src)
    produced["wiring_graph_dot"] = str(dot_path)

    if not HAS_GRAPHVIZ:
        return produced

    try:
        import graphviz  # type: ignore

        src = graphviz.Source(dot_src)
        # render() needs the 'dot' binary; guard against it being missing.
        png = src.render(filename=str(out_dir / "wiring_graph_gv"), format="png", cleanup=True)
        produced["wiring_graph_gv_png"] = png
        svg = src.render(filename=str(out_dir / "wiring_graph_gv"), format="svg", cleanup=True)
        produced["wiring_graph_gv_svg"] = svg
    except Exception:
        # 'dot' binary missing or render failed — keep the .dot file only.
        pass
    return produced
