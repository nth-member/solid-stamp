#!/usr/bin/env python3
"""A copy of docs/ with two days of digests, made by the live run against a recording stand-in for ntfy:
tests/.fixture/, for tests/browser.mjs. Nothing is sent."""
import json
import os
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "stage"))
import run  # noqa: E402

FIX = ROOT / "tests" / ".fixture"
if FIX.exists():
    shutil.rmtree(FIX)
shutil.copytree(ROOT / "docs", FIX, ignore=shutil.ignore_patterns("log"))
now = time.time()
t0 = now - 2 * 86400
run.STATE, run.OLD_STATE, run.LOG, run.OUT = FIX / "state.json", FIX / "no-old-state.json", FIX / "log", FIX / "data"
run.STATE.write_text(json.dumps({"since": int(t0 * 1000), "alerts": {}, "digests": {}, "finals": {}}))
sent = []
run.ntfy.config = lambda: {"server": "https://ntfy.invalid", "topic": "fixture"}
run.ntfy.publish = lambda cfg, msg, delay_s=None: sent.append(msg) or {"id": f"fx{len(sent)}"}
sys.argv = ["run.py"]
if json.loads((ROOT / "settings.json").read_text()).get("sender", "laptop") == "github":
    os.environ["GITHUB_ACTIONS"] = "true"                  # run here as the sender would run
run.main()
print(f"fixture: {len(sent)} messages recorded; {FIX}")
