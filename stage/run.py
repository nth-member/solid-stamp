#!/usr/bin/env python3
"""The live run, every 15 minutes after REVOTT STAMPS' refresh (stage/cron.sh):

    python3 stage/run.py              schedule, send and record (dry when .ntfy.json is missing)
    python3 stage/run.py --dry-run    the same, sending nothing and changing no state
    python3 stage/run.py --dry-run --since 2026-11-09T00:00 [--until ...]   replay a past stretch, as if live then

Each run, from the precomputed database (stage/db.py) and REVOTT STAMPS' archive:

  1  alerts   every trigger whose instant lies in the next horizon_hours (and after activation) is scheduled
              on the ntfy server for that instant, by its id as sequence ID; one whose message changed (the
              keys or the maps changed) is scheduled again, which replaces it; one that no longer matches is
              deleted before it is delivered
  2  digests  every trigger whose window has closed and settled -- by the archive's as-of, so the feeds
              have been read past it -- is stamped and its digest sent, replacing the alert in place; once
  3  finals   final_hours after its window closed, each digested trigger is stamped again and the record
              kept, not sent
  4  record   docs/log/<Nsukka date>.json holds every trigger's record, alert and digest as sent;
              docs/data/upcoming.json the next 7 days' triggers; docs/data/status.json this run

What drives a stamp is the match to SFO-BBs alone: every trigger is alerted and digested, whatever its
window holds. A failed send is left for the next run; a sequence ID never sends a duplicate notification,
because the ntfy app replaces a notification with the same sequence ID in place.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time
from fractions import Fraction as F
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import db  # noqa: E402
import digest  # noqa: E402
import ntfy  # noqa: E402
import solid  # noqa: E402
from exact import fparse  # noqa: E402

STATE = ROOT / "state" / "state.json"      # committed: what was scheduled and sent (no topic)
OLD_STATE = ROOT / ".state.json"
LOG = ROOT / "docs" / "log"
OUT = ROOT / "docs" / "data"
MINUTE = 60_000
SEND_LIMIT = 40                    # messages per run: the ntfy server allows 60 at once, then one per 5 s


def nsukka_date(ms: int) -> str:
    return dt.datetime.fromtimestamp(ms / 1000, solid.clock.WAT).strftime("%Y-%m-%d")


def parse_time(s: str) -> int:
    t = dt.datetime.fromisoformat(s)
    if t.tzinfo is None:
        t = t.replace(tzinfo=solid.clock.WAT)
    return int(t.timestamp() * 1000)


def load_state() -> dict:
    if not STATE.exists() and OLD_STATE.exists():          # before 2026-11-12 the state was local and untracked
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(OLD_STATE.read_text())
    return json.loads(STATE.read_text()) if STATE.exists() else {"since": None, "alerts": {}, "digests": {}, "finals": {}}


class Log:
    """docs/log/<date>.json: {id: record}, by the Nsukka date of the trigger's instant."""

    def __init__(self, dry: bool):
        self.dry, self.days, self.dirty = dry, {}, set()

    def day(self, date: str) -> dict:
        if date not in self.days:
            p = LOG / f"{date}.json"
            self.days[date] = json.loads(p.read_text()) if p.exists() else {}
        return self.days[date]

    def put(self, d: dict, **fields) -> dict:
        date = nsukka_date(d["instants"][0])
        rec = self.day(date).setdefault(d["id"], {})
        rec.update(fields)
        self.dirty.add(date)
        return rec

    def get(self, d: dict) -> dict | None:
        return self.day(nsukka_date(d["instants"][0])).get(d["id"])

    def save(self) -> None:
        if self.dry:
            return
        LOG.mkdir(parents=True, exist_ok=True)
        for date in sorted(self.dirty):
            recs = dict(sorted(self.days[date].items(), key=lambda kv: (kv[1]["trigger"]["instants"][0], kv[0])))
            (LOG / f"{date}.json").write_text(json.dumps(recs, ensure_ascii=False, separators=(",", ":")))
        days = sorted(p.stem for p in LOG.glob("*.json") if p.stem != "index")
        (LOG / "index.json").write_text(json.dumps(days))


def window(d: dict, settings: dict) -> tuple[int, int]:
    h = F(settings["eps"]) * solid.U
    z = fparse(d["z"])
    return solid.stamps.span_of(z - h, z + h)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--since", help="replay from this Nsukka time (dry runs only)")
    ap.add_argument("--until", help="replay until this Nsukka time (dry runs only)")
    ap.add_argument("--show", type=int, default=3, help="dry runs: print this many alerts and digests in full")
    a = ap.parse_args()

    settings = json.loads((ROOT / "settings.json").read_text())
    here = "github" if os.environ.get("GITHUB_ACTIONS") else "laptop"
    if settings.get("sender", "laptop") != here and not a.dry_run:
        print(f"solid: the sender is {settings.get('sender')}; this {here} run sends nothing")
        return 0
    cfg = ntfy.config()
    dry = a.dry_run or cfg is None
    if cfg is None and not a.dry_run:
        print("solid: no .ntfy.json -- a dry run (nothing sent)")
    if (a.since or a.until) and not a.dry_run:
        print("solid: --since and --until replay only as a dry run"); return 2
    con = db.connect()
    idx = solid.stamps.data("index.json")
    as_of, first_reading = idx["as_of"], idx["first_reading"]
    now = parse_time(a.until) if a.until else int(time.time() * 1000)
    if a.until:
        as_of = min(as_of, now)
    state = load_state() if not a.since else {"since": None, "alerts": {}, "digests": {}, "finals": {}}
    since = parse_time(a.since) if a.since else state["since"] or now
    if not dry and state["since"] is None:
        state["since"] = since
        print(f"solid: activated {solid.nsukka(since)} Nsukka -- triggers from now on")
    log, sent, shown = Log(dry), 0, {"alert": 0, "digest": 0}
    h = F(settings["eps"]) * solid.U
    settle, final = settings["settle_minutes"] * MINUTE, settings["final_hours"] * 60 * MINUTE

    def send(msg: dict, delay_s: int | None = None) -> dict | None:
        nonlocal sent
        if dry:
            kind = "alert" if delay_s else "digest"
            if shown[kind] < a.show:
                shown[kind] += 1
                print(f"--- {'scheduled for ' + solid.nsukka(delay_s * 1000) if delay_s else 'sent'}: {msg['title']}"
                      f"  [{len(msg['message'].encode())} bytes, priority {msg['priority']}]\n{msg['message']}\n")
            return {"id": "dry", "time": now // 1000}
        if sent >= SEND_LIMIT:
            return None
        try:
            r = ntfy.publish(cfg, msg, delay_s)
        except (ntfy.Refused, OSError) as e:
            print(f"solid: send failed ({e}); left for the next run")
            sent = SEND_LIMIT
            return None
        sent += 1
        return r

    counts = {"alerts": 0, "rescheduled": 0, "deleted": 0, "digests": 0, "finals": 0, "late": 0}

    # 1  alerts, up to the horizon
    ahead = db.triggers(con, max(now + MINUTE // 6, since), now + settings["horizon_hours"] * 60 * MINUTE)
    live = {d["id"] for d in ahead}
    for d in ahead:
        near = db.nearby(con, fparse(d["z"]), h)
        msg = digest.payload(d, settings, None, near)
        ph = digest.payload_hash(msg)
        have = state["alerts"].get(d["id"])
        if have and have["hash"] == ph:
            continue
        r = send(msg, d["instants"][0] // 1000)
        if r is None:
            continue
        counts["rescheduled" if have else "alerts"] += 1
        state["alerts"][d["id"]] = {"at": d["instants"][0], "hash": ph, "ntfy": r.get("id"), "posted": now}
        log.put(d, trigger=d, alert={"scheduled_for": d["instants"][0], "posted": now, "ntfy": r.get("id"),
                                     "priority": msg["priority"], "bytes": len(msg["message"].encode())})
    for tid, al in list(state["alerts"].items()):         # scheduled, not yet delivered, and no longer a match
        if al["at"] > now + MINUTE and al["at"] <= now + settings["horizon_hours"] * 60 * MINUTE and tid not in live:
            if not dry:
                try:
                    ntfy.delete(cfg, tid)
                except (ntfy.Refused, OSError) as e:
                    print(f"solid: delete {tid} failed ({e})"); continue
            del state["alerts"][tid]
            counts["deleted"] += 1

    # 2  digests, once the archive has read past the window's close and the settling time
    lookback = max(since, now - settings.get("lookback_days", 3) * 24 * 60 * MINUTE)
    for d in db.triggers(con, lookback, now):
        if d["id"] in state["digests"]:
            continue
        a_ms, b_ms = window(d, settings)
        if b_ms + settle > as_of or a_ms < first_reading:
            continue
        near = db.nearby(con, fparse(d["z"]), h)
        rec = digest.record(d, settings, near)
        late = 0 if a.since else max(0, (now - (b_ms + settle)) // MINUTE)
        msg = digest.payload(d, settings, rec, near, late)
        r = send(msg)
        if r is None:
            continue
        counts["digests"] += 1
        counts["late"] += late > 30
        state["digests"][d["id"]] = {"at": d["instants"][0], "sent": now, "ntfy": r.get("id")}
        log.put(d, trigger=d, nearby=near, spectrum=rec["spectrum"], feeds=rec["feeds"],
                digest={"sent": now, "ntfy": r.get("id"), "priority": msg["priority"], "late_minutes": late,
                        "bytes": len(msg["message"].encode())})

    # 3  finals: the stamp again, final_hours after the window closed; kept, not sent
    for tid, dg in list(state["digests"].items()):
        if tid in state["finals"]:
            continue
        d = db.trigger(con, tid, (dg["at"], dg["at"]))
        if d is None:
            continue
        if window(d, settings)[1] + final > as_of:
            continue
        log.put(d, final=digest.stamp(d, settings))
        state["finals"][tid] = now
        counts["finals"] += 1

    # 4  the record
    upcoming = [{k: d[k] for k in ("id", "z", "z6", "class", "instants", "pairs", "functions")}
                for d in db.triggers(con, now, now + 7 * 24 * 60 * MINUTE)]
    status = {"run": now, "as_of": as_of, "since": state["since"], "dry": dry, "counts": counts,
              "manifest": json.loads((OUT / "manifest.json").read_text())["table_sha256"]}
    if not dry:
        log.save()
        (OUT / "upcoming.json").write_text(json.dumps(upcoming, ensure_ascii=False, separators=(",", ":")))
        (OUT / "status.json").write_text(json.dumps(status, separators=(",", ":")))
        srcs = solid.stamps.data("sources.json")
        (OUT / "feeds.json").write_text(json.dumps({
            "note": "The feeds read: JOMO SFO-WAM's knowledge servers (https://3pp-noah.github.io/jomo-sfo-wam/feeds/all.json, "
                    "JSON Feed 1.1, refreshed every 15 minutes), kept and dated by REVOTT STAMPS' archive; chosen: in the domains "
                    "a digest stamps. Each source: [id, name, domain, perspective, gives the day only].",
            "domains": sorted(settings["domains"]),
            "sources": [[k, v[0], v[1], v[2], v[3], v[1] in settings["domains"]] for k, v in sorted(srcs.items())]},
            ensure_ascii=False, separators=(",", ":")))
        (OUT / "settings.json").write_text(json.dumps({k: settings[k] for k in ("eps", "clock", "domains", "settle_minutes",
                                                       "final_hours", "priority", "stamps_page")}, separators=(",", ":")))
        keep = now - 12 * 24 * 60 * MINUTE                 # state only needs the last days
        for k in ("alerts", "digests"):
            state[k] = {t: v for t, v in state[k].items() if v["at"] >= keep}
        state["finals"] = {t: v for t, v in state["finals"].items() if t in state["digests"]}
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(state, separators=(",", ":"), sort_keys=True))
    print(f"solid: {'dry run, ' if dry else ''}as of {solid.nsukka(as_of, False)} Nsukka; {counts}; "
          f"next 7 days: {len(upcoming)} triggers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
