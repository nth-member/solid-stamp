#!/usr/bin/env python3
"""Send one test notification now: the next REVOTT trigger's alert, marked TEST, under its own sequence ID.

    python3 stage/notify_test.py

It goes to the topic in .ntfy.json; the phone subscribed to that topic should show it at once.
"""
import json
import sys
import time
from fractions import Fraction as F
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import db  # noqa: E402
import digest  # noqa: E402
import ntfy  # noqa: E402
import solid  # noqa: E402
from exact import fparse  # noqa: E402

cfg = ntfy.config()
if cfg is None:
    sys.exit("no .ntfy.json: nothing to send to")
settings = json.loads((HERE.parent / "settings.json").read_text())
con = db.connect()
now = int(time.time() * 1000)
d = next(t for t in db.triggers(con, now, now + 30 * 86400000) if t["pairs"])
msg = digest.payload(d, settings, None, db.nearby(con, fparse(d["z"]), F(settings["eps"]) * solid.U))
msg["title"] = "TEST · " + msg["title"]
msg["message"] = "_A test from SOLID STAMP: the next REVOTT match, as its alert will read._\n\n" + msg["message"]
msg["sequence_id"] = "test-" + d["id"]
r = ntfy.publish(cfg, msg)
print(f"sent: {msg['title']} ({len(msg['message'].encode())} bytes) -> ntfy id {r.get('id')}")
