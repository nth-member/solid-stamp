#!/usr/bin/env python3
"""Precompute, exhaustively, every foreknown TNLDY: the SQLite database data/solid.sqlite and docs/data/manifest.json.

    python3 build/table.py            build when an input changed (or the database is missing)
    python3 build/table.py --force    build regardless

The inputs are REVOTT's 401 keys (REVOTT STAMPS' docs/data/keys.json) and the engine's maps
(docs/data/functions.json, from build/engine.py). Every one of the 401 × 401 pairs (Y, X) is evaluated,
and every map at every one of the 401 keys -- no sampling. The database holds:

    keys       the 401 SFO-BB keys: index, x (exact), reading, apocalypse layers
    maps       the engine's maps: index, id, name, Ztp, U (exact), where the engine first writes it
    pairs      REVOTT: Y index, X index -> Z                  (401 × 401 rows)
    hits       MDQNM: map index, key index -> Z               (maps × 401 rows)
    instants   each distinct Z once: exact, to 6 decimals, as a float (for range search), its instant(s) on
               the Nsukka/Yg clock, its class (revott+mdqnm, revott, mdqnm) and its numbers of pairs and hits
    meta       the inputs' SHA-256, the counts, and the SHA-256 of the canonical table

and docs/data/keys.json, the keys with x as exact text, for the page.

Z is held exactly as text (a decimal when it ends, else n/d), which is also how rows are matched; the float
is only an index. The database is rebuilt, not edited: keys feed both tables, the maps only the hits, so a
change of maps alone rebuilds the hits and the instants and keeps the pairs. manifest.json, committed,
carries the same counts and hashes, so any rebuild can be checked against it.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "stage"))
import solid  # noqa: E402
from exact import fmt, fstr  # noqa: E402

DB = ROOT / "data" / "solid.sqlite"
MANIFEST = ROOT / "docs" / "data" / "manifest.json"

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS keys (i INTEGER PRIMARY KEY, x TEXT, xf REAL, reading TEXT, layers TEXT);
CREATE TABLE IF NOT EXISTS maps (k INTEGER PRIMARY KEY, id TEXT, name TEXT, ztp TEXT, unit TEXT, at TEXT);
CREATE TABLE IF NOT EXISTS pairs (y INTEGER, x INTEGER, z TEXT);
CREATE TABLE IF NOT EXISTS hits (k INTEGER, x INTEGER, z TEXT);
CREATE TABLE IF NOT EXISTS instants (z TEXT PRIMARY KEY, z6 TEXT, zf REAL, first_ms INTEGER, second_ms INTEGER,
                                     class TEXT, npairs INTEGER, nhits INTEGER);
"""
INDEXES = """
CREATE INDEX IF NOT EXISTS pairs_z ON pairs (z);   CREATE INDEX IF NOT EXISTS pairs_yx ON pairs (y, x);
CREATE INDEX IF NOT EXISTS hits_z ON hits (z);     CREATE INDEX IF NOT EXISTS hits_kx ON hits (k, x);
CREATE INDEX IF NOT EXISTS instants_zf ON instants (zf);  CREATE INDEX IF NOT EXISTS instants_ms ON instants (first_ms);
CREATE INDEX IF NOT EXISTS instants_class ON instants (class, first_ms);
"""


def canonical_hash(rows: dict) -> str:
    """SHA-256 of the whole table written canonically: one line per Z in order, its pairs and hits sorted."""
    h = hashlib.sha256()
    for z in sorted(rows):
        p, f = rows[z]
        h.update(f"{fstr(z)}|{sorted(p)}|{sorted(f)}\n".encode())
    return h.hexdigest()


def current(con) -> dict:
    try:
        return dict(con.execute("SELECT k, v FROM meta"))
    except sqlite3.Error:
        return {}


def build(force: bool = False) -> dict:
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)
    have, want = current(con), solid.inputs()
    if not force and have.get("keys.json") == want["keys.json"] and have.get("functions.json") == want["functions.json"]:
        con.close()
        return json.loads(have["counts"])
    t0 = time.time()
    keys_changed = force or have.get("keys.json") != want["keys.json"]
    rows = solid.table()
    ks, fs = solid.keys(), solid.functions()["maps"]
    with con:
        con.execute("DELETE FROM meta")
        con.execute("DELETE FROM keys")
        con.executemany("INSERT INTO keys VALUES (?,?,?,?,?)",
                        [(i, fstr(x), float(x), r, json.dumps(l)) for i, (x, r, l) in enumerate(ks)])
        con.execute("DELETE FROM maps")
        con.executemany("INSERT INTO maps VALUES (?,?,?,?,?,?)",
                        [(k, m["id"], m["name"], m["ztp"], m["unit"], m["at"]) for k, m in enumerate(fs)])
        if keys_changed:
            con.execute("DELETE FROM pairs")
            con.executemany("INSERT INTO pairs VALUES (?,?,?)",
                            [(i, j, fstr(z)) for z, (p, _f) in rows.items() for i, j in p])
        con.execute("DELETE FROM hits")
        con.executemany("INSERT INTO hits VALUES (?,?,?)", [(k, j, fstr(z)) for z, (_p, f) in rows.items() for k, j in f])
        con.execute("DELETE FROM instants")
        out = []
        for z, (p, f) in rows.items():
            ins = solid.instants(z)
            out.append((fstr(z), fmt(z, 6), float(z), ins[0] if ins else None, ins[1] if len(ins) > 1 else None,
                        solid.kind(p, f), len(p), len(f)))
        con.executemany("INSERT INTO instants VALUES (?,?,?,?,?,?,?,?)", out)
        con.executescript(INDEXES)
        n = {"keys": len(ks), "maps": len(fs), "pairs": con.execute("SELECT COUNT(*) FROM pairs").fetchone()[0],
             "hits": con.execute("SELECT COUNT(*) FROM hits").fetchone()[0], "instants": len(rows),
             "by_class": dict(con.execute("SELECT class, COUNT(*) FROM instants GROUP BY class")),
             "revott_instants": con.execute("SELECT COUNT(DISTINCT z) FROM pairs").fetchone()[0],
             "mdqnm_instants": con.execute("SELECT COUNT(DISTINCT z) FROM hits").fetchone()[0],
             "outside_calendar": con.execute("SELECT COUNT(*) FROM instants WHERE first_ms IS NULL").fetchone()[0],
             "met_twice": con.execute("SELECT COUNT(*) FROM instants WHERE second_ms IS NOT NULL").fetchone()[0]}
        table_hash = canonical_hash(rows)
        meta = {**want, "counts": json.dumps(n), "table_sha256": table_hash,
                "built": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        con.executemany("INSERT INTO meta VALUES (?,?)", list(meta.items()))
    con.execute("VACUUM")
    con.close()
    MANIFEST.write_text(json.dumps({"inputs": want, "counts": n, "table_sha256": table_hash}, indent=1) + "\n")
    (MANIFEST.parent / "keys.json").write_text(json.dumps([[fstr(x), r, l] for x, r, l in ks], ensure_ascii=False,
                                                          separators=(",", ":")))
    print(f"table: {n['instants']} distinct TNLDY ({n['by_class']}), {n['pairs']} pairs, {n['hits']} hits "
          f"from {n['maps']} maps × {n['keys']} keys; {time.time() - t0:.1f} s -> {DB.relative_to(ROOT)}")
    return n


if __name__ == "__main__":
    build("--force" in sys.argv)
