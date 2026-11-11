"""Local paths, read from the untracked .paths.json: revott_stamps (the REVOTT STAMPS checkout whose archive and
stamp are used) and engine (the MDQNM engine's sources, as Alien Corridor publishes them)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def path(name: str) -> Path:
    return Path(json.loads((ROOT / ".paths.json").read_text())[name]).expanduser()
