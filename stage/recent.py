#!/usr/bin/env python3
"""The feed archive for a run on GitHub: REVOTT STAMPS' published archive, brought up to the latest reading.

    python3 stage/recent.py OUT [--days 4]

GitHub reads JOMO SFO-WAM's feeds every 15 minutes, whether or not the author's computer is on, and logs
what each reading adds in that repository's feeds/history/<UTC date>.jsonl.gz. REVOTT STAMPS' archive,
built on the author's computer, holds each item's reconciled time, including the time its article page
states, but only up to that computer's last refresh. This writes, into OUT, a copy of the archive in
REVOTT STAMPS' own layout (index.json, sources.json, coverage.json, keys.json, days/<Nsukka date>.json)
for the last few Nsukka days:

  - every item the published archive already holds keeps its row exactly (page times included);
  - every item GitHub has read since gets the row REVOTT STAMPS' own reconcile() gives it with no
    page time yet: the feed's time, the day only, or the moment it was first seen;
  - each source's coverage gains the stretches GitHub's readings covered, and the as-of becomes the
    latest reading.

stage/solid.py then stamps against OUT (SOLID_STAMPS_DATA), with REVOTT STAMPS' stamp.py unchanged.
Paths: .paths.json "revott_stamps" (a checkout holding stage/ and docs/data) and "jomo" (one holding
feeds/history and feeds/catalogue.json).
"""
from __future__ import annotations

import datetime as dt
import gzip
import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from paths import path  # noqa: E402

STAMPS, JOMO = path("revott_stamps"), path("jomo")
if not (STAMPS / ".paths.json").exists():          # REVOTT STAMPS' code reads its own local paths on import
    (STAMPS / ".paths.json").write_text(json.dumps({"history": str(STAMPS / ".history"), "jomo": str(JOMO),
                                                    "revott": str(STAMPS), "gdelt": str(STAMPS)}))
sys.modules.pop("paths", None)                    # REVOTT STAMPS has its own paths module of the same name
sys.path.insert(0, str(STAMPS / "stage"))
import archive  # noqa: E402  (REVOTT STAMPS' archive: ms, nsukka_day, reconcile)
import nsukka_yg_clock as clock  # noqa: E402


def history_lines(days: list[str]) -> list[dict]:
    """Every reading logged on these UTC dates, in order."""
    out = []
    for d in days:
        p = JOMO / "feeds" / "history" / f"{d}.jsonl.gz"
        if p.exists():
            with gzip.open(p, "rt") as f:
                out += [json.loads(line) for line in f if line.strip()]
    return sorted(out, key=lambda r: r["generated"])


def merge(intervals: list[list[int]]) -> list[list[int]]:
    iv = sorted(intervals)
    out = [iv[0][:]] if iv else []
    for a, b in iv[1:]:
        if a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def main() -> int:
    out = Path(sys.argv[1])
    ndays = int(sys.argv[sys.argv.index("--days") + 1]) if "--days" in sys.argv else 4
    src = STAMPS / "docs" / "data"
    if out.exists():
        shutil.rmtree(out)
    (out / "days").mkdir(parents=True)
    idx = json.loads((src / "index.json").read_text())
    sources = json.loads((src / "sources.json").read_text())
    coverage = json.loads((src / "coverage.json").read_text())
    shutil.copy(src / "keys.json", out / "keys.json")
    catalogue = {s["id"]: s for s in json.loads((JOMO / "feeds" / "catalogue.json").read_text())}

    now = dt.datetime.now(dt.timezone.utc)
    nsukka_days = [(now + dt.timedelta(hours=1) - dt.timedelta(days=k)).date().isoformat() for k in range(ndays)][::-1]
    utc_days = [(now - dt.timedelta(days=k)).date().isoformat() for k in range(ndays + 1)][::-1]
    rows: dict[str, dict[str, list]] = {d: {} for d in nsukka_days}
    held = set()                     # items the published archive holds, on these days or the four before
    earlier = [(now + dt.timedelta(hours=1) - dt.timedelta(days=k)).date().isoformat() for k in range(ndays, ndays + 4)]
    for d in nsukka_days + earlier:
        p = src / "days" / f"{d}.json"
        if p.exists():
            for r in json.loads(p.read_text()):
                held.add((r[4], r[2]))
                if d in rows:
                    rows[d][(r[4], r[2])] = r

    lines = history_lines(utc_days)
    first_seen: dict[str, tuple[int, dict]] = {}
    spans = defaultdict(list)
    for ln in lines:
        g = archive.ms(ln["generated"])
        for i in ln.get("new", []):
            if i["id"] not in first_seen:
                first_seen[i["id"]] = (g, i)
        for s, (oldest, _newest, _n) in ln.get("span", {}).items():
            spans[s].append([min(archive.ms(oldest), g), g])
    added = 0
    for seen, i in first_seen.values():
        s = i["_jomo"]["source"]
        if (i["url"], s) in held:
            continue
        if s not in sources:
            c = catalogue.get(s, {})
            sources[s] = [c.get("label") or s, c.get("domain") or i["_jomo"].get("domain", ""), c.get("perspective", ""), False]
        feed = archive.ms(i.get("date_published"))
        capped = bool(feed is not None and i["_jomo"].get("fetched") and i.get("date_published") == i["_jomo"]["fetched"])
        t, how, note = archive.reconcile(feed, None, seen, capped, sources[s][3])
        d = archive.nsukka_day(t)
        if d in rows:
            rows[d][(i["url"], s)] = [t, how, s, i["title"], i["url"], seen, feed, None, note]
            held.add((i["url"], s))
            added += 1
    for s, iv in spans.items():
        coverage[s] = merge(coverage.get(s, []) + iv)

    days = dict(idx["days"])
    for d, rs in rows.items():
        r = sorted(rs.values(), key=lambda r: (r[0], r[4]))
        (out / "days" / f"{d}.json").write_text(json.dumps(r, ensure_ascii=False, separators=(",", ":")))
        if r:
            zs = [float(clock.z_of(x[0])) for x in r]
            days[d] = [len(r), round(min(zs), 6), round(max(zs), 6)]
    days = {d: v for d, v in sorted(days.items()) if d in rows}     # only the days written here are stamped
    as_of = max([idx["as_of"]] + [archive.ms(ln["generated"]) for ln in lines])
    idx.update(as_of=as_of, days=days)
    (out / "index.json").write_text(json.dumps(idx, ensure_ascii=False, separators=(",", ":")))
    (out / "sources.json").write_text(json.dumps(dict(sorted(sources.items())), ensure_ascii=False, separators=(",", ":")))
    (out / "coverage.json").write_text(json.dumps(dict(sorted(coverage.items())), separators=(",", ":")))
    print(f"recent: {len(lines)} readings on {utc_days[0]}..{utc_days[-1]} UTC, {added} items newer than the published "
          f"archive; days {nsukka_days[0]}..{nsukka_days[-1]}; as of "
          f"{dt.datetime.fromtimestamp(as_of / 1000, clock.WAT):%Y-%m-%d %H:%M} Nsukka")
    return 0


if __name__ == "__main__":
    sys.exit(main())
