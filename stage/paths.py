"""Local paths, read from the untracked .paths.json: revott_stamps (the REVOTT STAMPS checkout whose archive and
stamp are used) and engine (the MDQNM engine's sources, as Alien Corridor publishes them)."""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def path(name: str) -> Path:
    """SOLID_PATHS names another paths file (a run on GitHub, a test)."""
    f = Path(os.environ.get("SOLID_PATHS") or ROOT / ".paths.json")
    return Path(json.loads(f.read_text())[name]).expanduser()
