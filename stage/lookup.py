#!/usr/bin/env python3
"""Read the precomputed table: what matches, where and when.

    python3 stage/lookup.py next [N]                  the next N triggers (default 10)
    python3 stage/lookup.py at TNLDY                  the trigger at an exact TNLDY (as 20824 or 478949/23), or none
    python3 stage/lookup.py when "2026-11-12 14:36"   that Nsukka instant's TNLDY, and the triggers within ±ε
    python3 stage/lookup.py spectrum TNLDY            every MDQNM function at that TNLDY: on an SFO-BB or between two
    python3 stage/lookup.py key X [FROM TO]           when SFO-BB X is matched: REVOTT pairs with Y or X = X, and the
                                                      functions reaching X (FROM, TO: Nsukka dates; default the next year)
    python3 stage/lookup.py function NAME|ID          a function's 401 instants, one per SFO-BB
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
from fractions import Fraction as F
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import db  # noqa: E402
import solid  # noqa: E402
from exact import fmt, fparse, fstr  # noqa: E402

SETTINGS = json.loads((HERE.parent / "settings.json").read_text())


def when_text(d: dict) -> str:
    return solid.nsukka(d["instants"][0]) if d["instants"] else "no instant (passed over, or outside the calendar)"


def show(d: dict, full: bool = True) -> None:
    print(f"{when_text(d)} Nsukka · TNLDY {d['z6']} (exact {d['z']}) · {solid.CLASS_LABEL[d['class']]} · id {d['id']}")
    if not full:
        return
    for p in d["pairs"]:
        print(f"   REVOTT  Y {p['y']:>9} {solid.reading(p['yi'])[:60]!r:64} X {p['x']:>9} {solid.reading(p['xi'])[:60]!r}")
    for f in d["functions"]:
        print(f"   MDQNM   {f['name'][:72]:72} on SFO-BB {f['x']:>9} {solid.reading(f['xi'])[:50]!r}  ({f['ztp']} + {f['unit']}·x)")


def ms_of(s: str) -> int:
    t = dt.datetime.fromisoformat(s)
    return int((t if t.tzinfo else t.replace(tzinfo=solid.clock.WAT)).timestamp() * 1000)


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__); return 2
    con = db.connect()
    cmd, args = argv[0], argv[1:]
    now = int(time.time() * 1000)
    if cmd == "next":
        n = int(args[0]) if args else 10
        hi = now + 86400000
        while True:
            ds = db.triggers(con, now, hi)
            if len(ds) >= n or hi - now > 400 * 86400000:
                break
            hi += 7 * 86400000
        for d in ds[:n]:
            show(d)
    elif cmd == "at":
        z = fparse(args[0])
        d = db.at(con, z)
        print(f"TNLDY {fmt(z, 6)}: no SFO-BB matches here" if d is None else "", end="\n" if d is None else "")
        if d:
            show(d)
    elif cmd == "when":
        ms = ms_of(args[0])
        z = solid.clock.z_of(ms)
        h = F(SETTINGS["eps"]) * solid.U
        print(f"{solid.nsukka(ms)} Nsukka reads TNLDY {fmt(z, 6)}; matches within ±{float(h * 1440):g} min:")
        for d in db.nearby(con, z, h):
            show(d)
    elif cmd == "spectrum":
        z = fparse(args[0])
        fs = solid.functions()["maps"]
        rank = {"on": 0, "between": 1, "before": 2, "after": 2}          # as the summary counts them; within each, by Ztp
        for k, c, where, lo, hi in sorted(solid.spectrum(z), key=lambda r: (rank[r[2]], r[0])):
            pos = (f"ON SFO-BB {fstr(solid.key_values()[lo])}: {solid.reading(lo)[:50]}" if where == "on" else
                   f"between {fstr(solid.key_values()[lo])} and {fstr(solid.key_values()[hi])}" if where == "between" else
                   f"before the first SFO-BB ({fstr(solid.key_values()[0])})" if where == "before" else
                   f"after the last SFO-BB ({fstr(solid.key_values()[-1])})")
            print(f"{k:4} {fs[k]['name'][:70]:70} {c:>22}  {pos}")
    elif cmd == "key":
        x = fparse(args[0])
        j = solid.key_index().get(x)
        if j is None:
            print(f"{args[0]} is not one of the 401 SFO-BB keys"); return 1
        lo = ms_of(args[1]) if len(args) > 1 else now
        hi = ms_of(args[2]) if len(args) > 2 else lo + 366 * 86400000
        for d in db.triggers(con, lo, hi):
            if any(p["yi"] == j or p["xi"] == j for p in d["pairs"]) or any(f["xi"] == j for f in d["functions"]):
                show(d)
    elif cmd == "function":
        fs = solid.functions()["maps"]
        hit = [k for k, m in enumerate(fs) if m["id"] == args[0] or m["name"] == args[0] or args[0] in m["names"]]
        if not hit:
            hit = [k for k, m in enumerate(fs) if args[0] in m["name"]]
        for k in hit[:5]:
            m = fs[k]
            print(f"{m['name']} · id {m['id']} · Z = {m['ztp']} + {m['unit']}·x · first written {m['at']} · {m['kinds']}")
            ztp, u = solid.maps()[k]
            for j, (x, r, _l) in enumerate(solid.keys()):
                z = ztp + u * x
                ins = solid.instants(z)
                print(f"   SFO-BB {fstr(x):>9}  TNLDY {fmt(z, 6):>22}  "
                      f"{solid.nsukka(ins[0]) if ins else 'no instant':26}  {r[:50]}")
    else:
        print(__doc__); return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
