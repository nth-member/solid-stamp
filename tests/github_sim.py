#!/usr/bin/env python3
"""What a run on GitHub would have stamped while this computer slept, against what it stamped on waking.

    python3 tests/github_sim.py [--slept "2026-11-11T22:33"] [--woke "2026-11-12T07:29"]

It copies REVOTT STAMPS' archive as it stood when the computer went to sleep -- every item first seen after
that removed, the as-of set back -- and lets stage/recent.py bring it up to date from JOMO SFO-WAM's
GitHub readings, as the workflow does. Then every trigger of the night is stamped both ways: by the
archive this computer built on waking (with its page times), and by the GitHub archive. Nothing is sent.
"""
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WAT = dt.timezone(dt.timedelta(hours=1))
arg = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d  # noqa: E731
slept = int(dt.datetime.fromisoformat(arg("--slept", "2026-11-11T22:33")).replace(tzinfo=WAT).timestamp() * 1000)
woke = int(dt.datetime.fromisoformat(arg("--woke", "2026-11-12T07:29")).replace(tzinfo=WAT).timestamp() * 1000)
home = Path.home()
T = Path(tempfile.mkdtemp(prefix="solid-sim-"))
rs = T / "revott-stamps"
shutil.copytree(home / "revott-stamps" / "stage", rs / "stage", ignore=shutil.ignore_patterns("__pycache__"))
(rs / "docs" / "data" / "days").mkdir(parents=True)
src = home / "revott-stamps" / "docs" / "data"
for f in ("sources.json", "coverage.json", "keys.json"):
    shutil.copy(src / f, rs / "docs" / "data" / f)
idx = json.loads((src / "index.json").read_text())
idx["as_of"] = slept
(rs / "docs" / "data" / "index.json").write_text(json.dumps(idx))
kept = dropped = 0
for p in sorted((src / "days").glob("*.json"))[-9:]:
    rows = json.loads(p.read_text())
    keep = [r for r in rows if r[5] <= slept]          # first seen before the computer slept
    kept, dropped = kept + len(keep), dropped + len(rows) - len(keep)
    (rs / "docs" / "data" / "days" / p.name).write_text(json.dumps(keep))
paths = T / "paths.json"
paths.write_text(json.dumps({"revott_stamps": str(rs), "jomo": str(home / "jomo-sfo-wam"), "engine": ""}))
env = {**os.environ, "SOLID_PATHS": str(paths)}
out = T / "stamps-data"
print(subprocess.run([sys.executable, str(ROOT / "stage" / "recent.py"), str(out)], env=env, capture_output=True, text=True, check=True).stdout.strip())
print(f"sim: the archive as it stood at sleep: {kept} items kept, {dropped} first seen later removed")

code = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
import db, digest
from fractions import Fraction as F
settings = json.load(open(sys.argv[2]))
con = db.connect()
out = {}
for d in db.triggers(con, int(sys.argv[3]), int(sys.argv[4])):
    s = digest.stamp(d, settings)
    out[d["id"]] = {"z6": d["z6"], "at": d["instants"][0], "items": [[it[4], it[1], it[2]] for it in s["items"]], "as_of": s["as_of"]}
print(json.dumps(out))
'''
args = [sys.executable, "-c", code, str(ROOT / "stage"), str(ROOT / "settings.json"), str(slept), str(woke - 2 * 3600000)]
laptop = json.loads(subprocess.run(args, capture_output=True, text=True, check=True).stdout)
gh = json.loads(subprocess.run(args, env={**env, "SOLID_STAMPS_DATA": str(out)}, capture_output=True, text=True, check=True).stdout)
same_set = same_all = 0
for tid, a in laptop.items():
    b = gh[tid]
    ua, ub = {x[0] for x in a["items"]}, {x[0] for x in b["items"]}
    clocks = sum(1 for x in a["items"] if x[2] == "p")
    when = dt.datetime.fromtimestamp(a["at"] / 1000, WAT).strftime("%d %b %H:%M:%S")
    print(f"  {when}  TNLDY {a['z6']}  laptop {len(ua):3} items ({clocks} by page time) · GitHub {len(ub):3} items · "
          f"in both {len(ua & ub)}, laptop only {len(ua - ub)}, GitHub only {len(ub - ua)}")
    same_set += ua == ub
print(f"sim: {len(laptop)} triggers of the night; the same items both ways for {same_set}")
shutil.rmtree(T)
