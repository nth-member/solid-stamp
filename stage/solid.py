#!/usr/bin/env python3
"""SOLID STAMP's core: the trigger instants, the full spectrum of the MDQNM functions at a TNLDY, and the digest.

A SOLID STAMP is driven by a match to SFO-BBs, and by nothing else: a TNLDY Z at which, exactly,

    REVOTT   Z = 14160 + 100·(Y + X)   Y and X each one of REVOTT's 401 SFO-BB keys (401 × 401 pairs)
    MDQNM    Z = Ztp + U·x             an engine coordinate c(Z) = (Z - Ztp)/U reaching SFO-BB key x

Feeds, words, schedules and nearness never start a stamp or stop one; the feeds are only what the digest
reports about Z. A REVOTT instant that an MDQNM function also reaches exactly is "sought after": there the
TNLDY a function of the engine generates is constituted by a foreknown Y and X. Each distinct Z is one trigger,
listing every pair and every function that make it. It occurs at its instant(s) on the Nsukka/Yg clock
(none when a recalibration passes it over, two when one meets it twice).

The digest of a trigger is REVOTT STAMPS' own stamp of the feeds about Z (stage/stamp.py, the reference its
page reproduces), with the SFO-BBs that made the trigger and the full spectrum of the MDQNM functions there:
every engine coordinate read at Z -- on an SFO-BB, or between two -- as the engine's own
sfo-bbvalue-timetravel-enumeration reads a single TNLDY.

Everything is exact rational arithmetic; times are the canonical Nsukka/Yg clock's.
"""
from __future__ import annotations

import bisect
import datetime as dt
import hashlib
import json
import sys
import urllib.parse
from collections import defaultdict
from decimal import Decimal
from fractions import Fraction as F
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from exact import fmt, fparse, fstr  # noqa: E402
from paths import path  # noqa: E402

STAMPS = path("revott_stamps")
sys.path.insert(0, str(STAMPS / "stage"))
import nsukka_yg_clock as clock  # noqa: E402  (REVOTT STAMPS' copy of the canonical clock)
import stamp as stamps  # noqa: E402

DATA = ROOT / "docs" / "data"
ZTP, U = F(14160), F(100)                   # REVOTT: Z = 14160 + 100·(Y + X)
CLASSES = ("revott+mdqnm", "revott", "mdqnm")
CLASS_LABEL = {"revott+mdqnm": "REVOTT + MDQNM", "revott": "REVOTT", "mdqnm": "MDQNM"}


# ---- inputs ------------------------------------------------------------------------------------

@lru_cache(None)
def keys() -> list[tuple[F, str, list]]:
    """REVOTT's 401 SFO-BB keys as REVOTT STAMPS holds them: (x exactly as written, reading, apocalypse layers)."""
    return [(F(Decimal(str(x))), r, layers) for x, r, layers in json.loads((STAMPS / "docs/data/keys.json").read_text())]


@lru_cache(None)
def key_index() -> dict[F, int]:
    return {x: i for i, (x, _r, _l) in enumerate(keys())}


@lru_cache(None)
def key_values() -> list[F]:
    return [x for x, _r, _l in keys()]


@lru_cache(None)
def functions() -> dict:
    return json.loads((DATA / "functions.json").read_text())


@lru_cache(None)
def maps() -> list[tuple[F, F]]:
    """(Ztp, U) of every engine map, in functions.json's order."""
    return [(fparse(m["ztp"]), fparse(m["unit"])) for m in functions()["maps"]]


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@lru_cache(None)
def inputs() -> dict:
    return {"keys.json": sha256_file(STAMPS / "docs/data/keys.json"), "functions.json": sha256_file(DATA / "functions.json")}


# ---- the trigger table ---------------------------------------------------------------------------

def table() -> dict[F, list[list]]:
    """Every foreknown TNLDY -> [pairs [(y index, x index)], hits [(map index, key index)]]: exhaustive."""
    rows: dict[F, list[list]] = defaultdict(lambda: [[], []])
    ks = key_values()
    for i, y in enumerate(ks):
        for j, x in enumerate(ks):
            rows[ZTP + U * (y + x)][0].append((i, j))
    for k, (ztp, u) in enumerate(maps()):
        for j, x in enumerate(ks):
            rows[ztp + u * x][1].append((k, j))
    return rows


def kind(pairs, hits) -> str:
    return "revott+mdqnm" if pairs and hits else "revott" if pairs else "mdqnm"


def in_calendar(z: F) -> bool:
    """Whether Z falls within the clock's years 1 .. 9999."""
    yg = 1969 + (z + 340) // clock.YG
    return 1 < yg < 9998


def instants(z: F) -> list[int]:
    """The epoch-ms instants at which the Nsukka/Yg clock reads Z: none, one or two."""
    return [stamps.ms_round(t) for t in clock.instants(z)] if in_calendar(z) else []


def tid(z: F) -> str:
    """A trigger's id, from its exact TNLDY: also its ntfy sequence ID."""
    return "ss" + hashlib.sha256(fstr(z).encode()).hexdigest()[:14]


class Table:
    """The trigger table in memory, sorted by TNLDY, for range lookups."""

    def __init__(self):
        rows = table()
        self.z = sorted(rows)
        self.rows = rows

    def between(self, lo: F, hi: F) -> list[F]:
        return self.z[bisect.bisect_left(self.z, lo):bisect.bisect_right(self.z, hi)]


# ---- readings ----------------------------------------------------------------------------------

def reading(j: int) -> str:
    return keys()[j][1]


def layers(j: int) -> list:
    return keys()[j][2]


def position(c: F) -> tuple[str, int | None, int | None]:
    """Where a coordinate stands among the keys: ("on", j, j), ("between", lo, hi), ("before", None, 0), ("after", n-1, None)."""
    ks = key_values()
    i = bisect.bisect_left(ks, c)
    if i < len(ks) and ks[i] == c:
        return "on", i, i
    if i == 0:
        return "before", None, 0
    if i == len(ks):
        return "after", len(ks) - 1, None
    return "between", i - 1, i


def spectrum(z: F) -> list[list]:
    """The full spectrum of the MDQNM functions at Z: for every map, [index, c to 6 decimals, where, lo, hi],
    c = (Z - Ztp)/U exactly, where = on | between | before | after the keys."""
    out = []
    for k, (ztp, u) in enumerate(maps()):
        c = (z - ztp) / u
        where, lo, hi = position(c)
        out.append([k, fmt(c, 6), where, lo, hi])
    return out


def spectrum_hash(sp: list[list]) -> str:
    return hashlib.sha256(json.dumps(sp, separators=(",", ":")).encode()).hexdigest()


def nsukka(ms: int, seconds: bool = True) -> str:
    t = dt.datetime.fromtimestamp(ms / 1000, clock.WAT)
    return t.strftime("%a %d %b %Y %H:%M:%S" if seconds else "%a %d %b %Y %H:%M")


def hm(ms: int) -> str:
    return dt.datetime.fromtimestamp(ms / 1000, clock.WAT).strftime("%H:%M:%S")


# ---- a trigger, described ---------------------------------------------------------------------

def describe(z: F, row: list[list]) -> dict:
    """What makes the trigger at Z: its pairs and functions, exactly, with the SFO-BBs' readings."""
    pairs, hits = row
    ks = keys()
    fs = functions()["maps"]
    return {
        "id": tid(z), "z": fstr(z), "z6": fmt(z, 6), "class": kind(pairs, hits), "instants": instants(z),
        "pairs": [{"y": fstr(ks[i][0]), "x": fstr(ks[j][0]), "yi": i, "xi": j} for i, j in sorted(pairs)],
        "functions": [{"k": k, "id": fs[k]["id"], "name": fs[k]["name"], "ztp": fs[k]["ztp"], "unit": fs[k]["unit"],
                       "x": fstr(ks[j][0]), "xi": j} for k, j in sorted(hits)],
    }


def revott_request(d: dict, settings: dict) -> dict | None:
    """The REVOTT STAMPS request that stamps this TNLDY in REVOTT's own setting -- one pair (Y, X) with
    14160 + 100·(Y + X) = Z exactly -- or None when Z has no such decimal Y."""
    if d["pairs"]:
        y, x = d["pairs"][0]["y"], d["pairs"][0]["x"]
    elif d["functions"]:
        x = d["functions"][0]["x"]
        yv = (fparse(d["z"]) - ZTP) / U - fparse(x)
        y = fstr(yv)
        if "/" in y:
            return None
    else:
        return None
    return {"y": {"mode": "value", "value": decimal_text(y)}, "x": {"mode": "key", "x": decimal_text(x)},
            "eps": settings["eps"], "clock": settings["clock"], "domains": sorted(settings["domains"])}


def decimal_text(s: str) -> str:
    return s if "." in s else s + ".0"


def stamps_link(d: dict, settings: dict) -> str | None:
    r = revott_request(d, settings)
    if r is None:
        return None
    return settings["stamps_page"] + "#" + urllib.parse.quote(json.dumps(r, separators=(",", ":")), safe="")


def page_link(d: dict, settings: dict) -> str | None:
    """The digest's page: #t=<id>&d=<the Nsukka date of its instant>."""
    if not settings.get("page") or not d["instants"]:
        return None
    date = dt.datetime.fromtimestamp(d["instants"][0] / 1000, clock.WAT).strftime("%Y-%m-%d")
    return f"{settings['page']}#t={d['id']}&d={date}"
