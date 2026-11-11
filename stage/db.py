"""Exact lookups in the precomputed database (build/table.py): the live run never recomputes the table."""
from __future__ import annotations

import sqlite3
import sys
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "build"))
sys.path.insert(0, str(ROOT / "stage"))
import table as builder  # noqa: E402
import solid  # noqa: E402
from exact import fparse  # noqa: E402


def connect() -> sqlite3.Connection:
    """The database, rebuilt first if REVOTT's keys or the engine's maps changed since it was built."""
    builder.build()
    con = sqlite3.connect(builder.DB)
    meta = dict(con.execute("SELECT k, v FROM meta"))
    want = solid.inputs()
    if meta.get("keys.json") != want["keys.json"] or meta.get("functions.json") != want["functions.json"]:
        raise RuntimeError("the database does not match its inputs")
    return con


def row(con, z: str) -> list[list]:
    """[pairs [(y, x)], hits [(map, key)]] at the exact TNLDY z (text, as stored)."""
    return [con.execute("SELECT y, x FROM pairs WHERE z = ? ORDER BY y, x", (z,)).fetchall(),
            con.execute("SELECT k, x FROM hits WHERE z = ? ORDER BY k, x", (z,)).fetchall()]


def triggers(con, lo_ms: int, hi_ms: int) -> list[dict]:
    """Every trigger whose first instant falls in [lo_ms, hi_ms], in order: described, with its row."""
    out = []
    for (z,) in con.execute("SELECT z FROM instants WHERE first_ms BETWEEN ? AND ? ORDER BY first_ms, zf", (lo_ms, hi_ms)):
        out.append(solid.describe(fparse(z), row(con, z)))
    return out


def trigger(con, tid: str, around_ms: tuple[int, int]) -> dict | None:
    for d in triggers(con, *around_ms):
        if d["id"] == tid:
            return d
    return None


def at(con, z: F) -> dict | None:
    """The trigger at an exact TNLDY, or None: no SFO-BB matches there."""
    from exact import fstr
    r = row(con, fstr(z))
    return solid.describe(z, r) if r[0] or r[1] else None


def nearby(con, z: F, h: F) -> list[dict]:
    """The other matches to SFO-BBs within Z ± h -- each its own stamp, listed in a digest only as context."""
    out = []
    m = 1e-6 + abs(float(z)) * 1e-12                            # the float index narrows; the exact test decides
    lo, hi = float(z - h) - m, float(z + h) + m
    for (z2,) in con.execute("SELECT z FROM instants WHERE zf BETWEEN ? AND ? ORDER BY zf", (lo, hi)):
        v = fparse(z2)
        if v != z and abs(v - z) <= h:
            d = solid.describe(v, row(con, z2))
            out.append({k: d[k] for k in ("id", "z", "z6", "class", "instants", "pairs", "functions")})
    return out
