#!/usr/bin/env python3
"""The dry-run acceptance checks; each prints PASS or FAIL, and the record goes to tests/results.md.

    python3 tests/acceptance.py

Nothing here sends a notification: the ntfy client is replaced by a recorder.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import random
import re
import sqlite3
import sys
import tempfile
import time
from decimal import Decimal
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "stage"))
sys.path.insert(0, str(ROOT / "build"))
import db  # noqa: E402
import digest  # noqa: E402
import run  # noqa: E402
import solid  # noqa: E402
import table as builder  # noqa: E402
from exact import fmt, fparse, fstr  # noqa: E402
from paths import path  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []
SETTINGS = json.loads((ROOT / "settings.json").read_text())


def check(name: str):
    def wrap(fn):
        t0 = time.time()
        try:
            note = fn() or ""
            RESULTS.append((name, True, note))
            print(f"PASS  {name}  {note}  ({time.time() - t0:.1f} s)")
        except AssertionError as e:
            RESULTS.append((name, False, str(e)))
            print(f"FAIL  {name}  {e}")
        return fn
    return wrap


con = db.connect()
ks = solid.key_values()
rng = random.Random(20261111)


@check("401 SFO-BBs: distinct, ascending, the same values as REVOTT's own keys, 85.32 among them")
def _():
    assert len(ks) == 401, len(ks)
    assert len(set(ks)) == 401
    assert all(a < b for a, b in zip(ks, ks[1:])), "not ascending"
    src = json.loads((path("revott_stamps").parent / "revott" / "data" / "keys.json").read_text()) \
        if (Path.home() / "revott" / "data" / "keys.json").exists() else None
    if src is not None:
        raw = src["keys"]
        vals = {F(Decimal(str(k["x"] if isinstance(k, dict) else k[0]))) for k in (raw.values() if isinstance(raw, dict) else raw)}
        assert vals == set(ks), f"REVOTT's keys.json differs: {len(vals ^ set(ks))} values"
    assert F(Decimal("85.32")) in set(ks)
    return f"{len(ks)} keys, {fstr(ks[0])} .. {fstr(ks[-1])}"


@check("the engine's maps: every coordinate linear in Z, exact; REVOTT itself and GOG_ID among them")
def _():
    fs = solid.functions()
    maps = {(m["ztp"], m["unit"]) for m in fs["maps"]}
    assert ("14160", "100") in maps, "REVOTT_ABSOLUTE_ZERO (14160, 100) missing"
    assert ("22440", "100") in maps, "GOGID.100D (22440 = 14160 + 100·82.80, 100) missing"
    assert len(fs["maps"]) == len({m["id"] for m in fs["maps"]}), "duplicate ids"
    reasons = set(fs["excluded_counts"])
    assert reasons <= {"division by Z", "the symbol z-tnldy-clock3", "not an arithmetic form"}, reasons
    return f"{len(fs['maps'])} distinct maps from {sum(fs['coordinates'].values())} coordinates; excluded {fs['excluded_counts']}"


@check("the precomputation is exhaustive: 401 × 401 pairs and every map at every key, counts as the manifest says")
def _():
    man = json.loads((ROOT / "docs/data/manifest.json").read_text())
    n = man["counts"]
    assert n["pairs"] == 401 * 401 == con.execute("SELECT COUNT(*) FROM pairs").fetchone()[0]
    assert n["hits"] == len(solid.maps()) * 401 == con.execute("SELECT COUNT(*) FROM hits").fetchone()[0]
    assert n["instants"] == con.execute("SELECT COUNT(*) FROM instants").fetchone()[0]
    assert sum(n["by_class"].values()) == n["instants"]
    assert n["revott_instants"] + n["mdqnm_instants"] - n["by_class"]["revott+mdqnm"] == n["instants"]
    return f"{n['pairs']} pairs, {n['hits']} hits, {n['instants']} distinct TNLDY"


@check("a fresh recomputation reproduces the stored table exactly (SHA-256 of the canonical table)")
def _():
    rows = solid.table()
    h = builder.canonical_hash(rows)
    man = json.loads((ROOT / "docs/data/manifest.json").read_text())
    assert h == man["table_sha256"] == dict(con.execute("SELECT k, v FROM meta"))["table_sha256"]
    return h[:16]


@check("stored combinations are retrieved exactly: 2,000 random pairs and 2,000 random (map, key) hits")
def _():
    for _ in range(2000):
        i, j = rng.randrange(401), rng.randrange(401)
        z = fstr(solid.ZTP + solid.U * (ks[i] + ks[j]))
        got = con.execute("SELECT z FROM pairs WHERE y = ? AND x = ?", (i, j)).fetchone()[0]
        assert got == z, (i, j, got, z)
        assert (i, j) in db.row(con, z)[0]
    ms = solid.maps()
    for _ in range(2000):
        k, j = rng.randrange(len(ms)), rng.randrange(401)
        z = fstr(ms[k][0] + ms[k][1] * ks[j])
        got = con.execute("SELECT z FROM hits WHERE k = ? AND x = ?", (k, j)).fetchone()[0]
        assert got == z, (k, j, got, z)
        assert (k, j) in db.row(con, z)[1]


@check("non-matching TNLDY values never trigger: random instants, and every trigger of 30 days moved by 1 ms, by brute force")
def _():
    ms_, kset = solid.maps(), set(ks)

    def brute(z):
        return any((z - solid.ZTP) / solid.U - y in kset for y in ks) or any((z - zt) / u in kset for zt, u in ms_)

    now = int(time.time() * 1000)
    hits = 0
    for _ in range(500):
        z = solid.clock.z_of(now + rng.randrange(-30 * 86400000, 30 * 86400000))
        assert brute(z) == (db.at(con, z) is not None), fstr(z)
        hits += db.at(con, z) is not None
    moved = 0
    for d in db.triggers(con, now, now + 30 * 86400000):
        for dz in (F(1, 86400000), F(-1, 86400000)):
            z = fparse(d["z"]) + dz
            assert brute(z) == (db.at(con, z) is not None), (d["id"], fstr(dz))
            moved += 1
    return f"500 random instants ({hits} matches) and {moved} moved triggers: the table agrees with brute force on all"


@check("every live trigger is an exact match: the next 30 days, each pair and hit recomputed from the keys")
def _():
    now = int(time.time() * 1000)
    ds = db.triggers(con, now, now + 30 * 86400000)
    for d in ds:
        z = fparse(d["z"])
        for p in d["pairs"]:
            assert solid.ZTP + solid.U * (fparse(p["y"]) + fparse(p["x"])) == z
            assert fparse(p["y"]) in set(ks) and fparse(p["x"]) in set(ks)
        for f in d["functions"]:
            assert fparse(f["ztp"]) + fparse(f["unit"]) * fparse(f["x"]) == z and fparse(f["x"]) in set(ks)
        assert d["instants"] and abs(solid.clock.z_of(d["instants"][0]) - z) < F(1, 86400000), "instant off by > 1 ms"
    by = {c: sum(d["class"] == c for d in ds) for c in solid.CLASSES}
    return f"{len(ds)} triggers in 30 days: {by}"


@check("the spectrum's 'on' entries are exactly the trigger's matched functions (200 triggers)")
def _():
    now = int(time.time() * 1000)
    ds = db.triggers(con, now - 60 * 86400000, now + 60 * 86400000)
    for d in rng.sample(ds, min(200, len(ds))):
        sp = solid.spectrum(fparse(d["z"]))
        on = sorted((k, lo) for k, _c, where, lo, _hi in sp if where == "on")
        assert on == sorted((f["k"], f["xi"]) for f in d["functions"]), d["id"]
        assert len(sp) == len(solid.maps())


@check("the driver is the match alone: a trigger whose window holds no item is still alerted and digested")
def _():
    now = int(time.time() * 1000)
    d = db.triggers(con, now - 3 * 86400000, now - 86400000)[0]
    empty = {**SETTINGS, "domains": ["no-such-domain"]}
    rec = digest.record(d, empty, [])
    assert rec["feeds"]["items"] == []
    msg = digest.payload(d, empty, rec, [])
    assert msg["sequence_id"] == d["id"] and "0 items" in msg["message"]
    return d["id"]


@check("every message fits ntfy's 4,096 bytes: the next 30 days' alerts and the last 3 days' digests")
def _():
    now = int(time.time() * 1000)
    big = 0
    for d in db.triggers(con, now, now + 30 * 86400000):
        n = len(digest.payload(d, SETTINGS, None, db.nearby(con, fparse(d["z"]), F(SETTINGS["eps"]) * solid.U))["message"].encode())
        assert n <= 4096, (d["id"], n)
        big = max(big, n)
    for d in db.triggers(con, now - 3 * 86400000, now - 6 * 3600000):
        near = db.nearby(con, fparse(d["z"]), F(SETTINGS["eps"]) * solid.U)
        n = len(digest.payload(d, SETTINGS, digest.record(d, SETTINGS, near), near)["message"].encode())
        assert n <= 4096, (d["id"], n)
        big = max(big, n)
    return f"largest {big} bytes"


@check("every stamped item lies within ±100·ε TNLDY of its trigger, on the reconciled clock")
def _():
    now = int(time.time() * 1000)
    h = F(SETTINGS["eps"]) * solid.U
    n = 0
    for d in db.triggers(con, now - 3 * 86400000, now - 6 * 3600000):
        for it in digest.stamp(d, SETTINGS)["items"]:
            assert abs(solid.clock.z_of(it[1]) - fparse(d["z"])) <= h, (d["id"], it[:5])
            n += 1
    return f"{n} items checked"


@check("duplicates: a second run with nothing new sends nothing; a changed message replaces by the same sequence ID")
def _():
    sent = []
    real_publish, real_config = run.ntfy.publish, run.ntfy.config
    tmp = Path(tempfile.mkdtemp())
    real_state, real_old, real_log, real_out = run.STATE, run.OLD_STATE, run.STATE, run.OUT
    real_log = run.LOG
    run.STATE, run.OLD_STATE, run.LOG = tmp / "state.json", tmp / "no-old-state.json", tmp / "log"
    out = tmp / "data"; out.mkdir()
    (out / "manifest.json").write_text((ROOT / "docs/data/manifest.json").read_text())
    run.OUT = out
    run.ntfy.publish = lambda cfg, msg, delay_s=None: sent.append((msg["sequence_id"], delay_s)) or {"id": f"m{len(sent)}"}
    run.ntfy.config = lambda: {"server": "https://ntfy.invalid", "topic": "test"}
    argv, env = sys.argv, os.environ.get("GITHUB_ACTIONS")
    if SETTINGS.get("sender", "laptop") == "github":
        os.environ["GITHUB_ACTIONS"] = "true"              # run here as the sender would run
    else:
        os.environ.pop("GITHUB_ACTIONS", None)
    try:
        sys.argv = ["run.py"]
        run.main()
        first = len(sent)
        run.main()
        second = len(sent) - first
        assert first > 0, "the first run scheduled nothing"
        assert second == 0, f"the second run sent {second} again"
        ids = [s for s, _ in sent]
        assert len(ids) == len(set(ids)), "one trigger scheduled twice"
        st = json.loads(run.STATE.read_text())
        assert all(st["alerts"][s]["at"] // 1000 == dl for s, dl in sent), "alert not scheduled at its instant"
        one = next(iter(st["alerts"]))
        st["alerts"][one]["hash"] = "changed"                 # as if the keys or maps had changed its message
        run.STATE.write_text(json.dumps(st))
        run.main()
        third = sent[first:]
        assert [s for s, _ in third] == [one], f"the third run sent {third}"
    finally:
        sys.argv = argv
        if env is None:
            os.environ.pop("GITHUB_ACTIONS", None)
        else:
            os.environ["GITHUB_ACTIONS"] = env
        run.ntfy.publish, run.ntfy.config = real_publish, real_config
        run.STATE, run.OLD_STATE, run.LOG, run.OUT = real_state, real_old, real_log, real_out
    return f"first run {first} scheduled, second run {second}, a changed one re-sent under its own sequence ID"


@check("REVOTT STAMPS links open the same TNLDY: Y + X of the link's request gives the trigger's Z exactly")
def _():
    now = int(time.time() * 1000)
    n = 0
    for d in db.triggers(con, now, now + 14 * 86400000):
        r = solid.revott_request(d, SETTINGS)
        if r is None:
            assert "/" in d["z"], d["id"]
            continue
        assert solid.ZTP + solid.U * (fparse(r["y"]["value"]) + fparse(r["x"]["x"])) == fparse(d["z"])
        n += 1
    return f"{n} links checked"


def write_results() -> None:
    ok = all(p for _, p, _ in RESULTS)
    lines = [f"# SOLID STAMP — acceptance checks", "",
             f"Run {dt.datetime.now(solid.clock.WAT):%Y-%m-%d %H:%M} Nsukka · table {json.loads((ROOT / 'docs/data/manifest.json').read_text())['table_sha256'][:16]}"
             f" · {sum(p for _, p, _ in RESULTS)}/{len(RESULTS)} pass", "", "| check | result | note |", "|---|---|---|"]
    lines += [f"| {n} | {'PASS' if p else 'FAIL'} | {note} |" for n, p, note in RESULTS]
    (ROOT / "tests" / "results.md").write_text("\n".join(lines) + "\n")
    print(f"{sum(p for _, p, _ in RESULTS)}/{len(RESULTS)} pass" + ("" if ok else " -- see above"))


if __name__ == "__main__":
    write_results()
    sys.exit(0 if all(p for _, p, _ in RESULTS) else 1)
