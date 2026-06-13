"""Small helpers shared across RoboMentor.

Kept dependency-free on purpose so the core always imports cleanly.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional


# --------------------------------------------------------------------------- #
# Optional dependency detection (never raises)
# --------------------------------------------------------------------------- #
def has_module(name: str) -> bool:
    import importlib.util

    return importlib.util.find_spec(name) is not None


HAS_MATPLOTLIB = has_module("matplotlib")
HAS_NETWORKX = has_module("networkx")
HAS_GRAPHVIZ = has_module("graphviz")
HAS_YAML = has_module("yaml")
HAS_TYPER = has_module("typer")
HAS_JINJA2 = has_module("jinja2")
HAS_REQUESTS = has_module("requests")


# --------------------------------------------------------------------------- #
# Filesystem
# --------------------------------------------------------------------------- #
def ensure_dir(path: Path) -> Path:
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, data: Any, indent: int = 2) -> Path:
    path = Path(path)
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, indent=indent, ensure_ascii=False), encoding="utf-8")
    return path


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_text(path: Path, text: str) -> Path:
    path = Path(path)
    ensure_dir(path.parent)
    path.write_text(text, encoding="utf-8")
    return path


def read_text(path: Path) -> str:
    return Path(path).read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# Text helpers
# --------------------------------------------------------------------------- #
def slugify(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip().lower())
    return text.strip("_") or "project"


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


# --------------------------------------------------------------------------- #
# Colour palette used by renderers (kept here so renderers stay consistent)
# --------------------------------------------------------------------------- #
NET_COLORS: Dict[str, str] = {
    "power": "#e74c3c",    # red
    "ground": "#2c3e50",   # dark slate
    "signal": "#2980b9",   # blue
    "pwm": "#8e44ad",      # purple
    "i2c": "#16a085",      # teal
    "spi": "#d35400",      # orange
}

CATEGORY_COLORS: Dict[str, str] = {
    "sensor": "#27ae60",
    "actuator": "#e67e22",
    "passive": "#7f8c8d",
    "power": "#c0392b",
    "display": "#2980b9",
    "board_support": "#95a5a6",
    "board": "#34495e",
}


def net_color(net: str) -> str:
    return NET_COLORS.get(net, "#2c3e50")


def category_color(category: str) -> str:
    return CATEGORY_COLORS.get(category, "#34495e")


def short_id() -> str:
    """Deterministic-friendly short token (not random by default)."""
    import time

    return hex(int(time.time() * 1000) & 0xFFFFFF)[2:]


def safe_get(d: Optional[Dict[str, Any]], *keys: str, default: Any = None) -> Any:
    cur: Any = d or {}
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur
