#!/usr/bin/env python3
"""The reference for tests/fidelity.mjs: reads {"spectra": [z...], "ranges": [[z0, z1]...]} on stdin and writes
Python's spectra (as JSON text, with SHA-256) and the database's rows in each range."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "stage"))
import db  # noqa: E402
import solid  # noqa: E402
from exact import fparse  # noqa: E402

req = json.load(sys.stdin)
con = db.connect()
out = {"spectra": [], "ranges": []}
for z in req["spectra"]:
    sp = solid.spectrum(fparse(z))
    out["spectra"].append({"json": json.dumps(sp, separators=(",", ":")), "sha256": solid.spectrum_hash(sp)})
for z0, z1 in req["ranges"]:
    lo, hi = fparse(z0), fparse(z1)
    m = 1e-6 + abs(float(lo)) * 1e-12
    rows = []
    for (z,) in con.execute("SELECT z FROM instants WHERE zf BETWEEN ? AND ? ORDER BY zf", (float(lo) - m, float(hi) + m)):
        if lo <= fparse(z) <= hi:
            p, f = db.row(con, z)
            rows.append({"z": z, "pairs": [list(x) for x in p], "hits": [list(x) for x in f]})
    rows.sort(key=lambda r: fparse(r["z"]))
    out["ranges"].append(rows)
json.dump(out, sys.stdout)
