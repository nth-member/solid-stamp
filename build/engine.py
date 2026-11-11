#!/usr/bin/env python3
"""The MDQNM engine's TNLDY functions, read exactly from its sources: docs/data/functions.json.

    python3 build/engine.py                 read the engine and write the maps
    python3 build/engine.py --if-changed    only when a source file changed (stage/refresh.sh runs this)

Every coordinate of TNLDY the engine writes, in the primary and the bank edition, places the SFOs in
time. It writes them four ways: a function of Z, `(def name (fn [Z] ...))`, whose value is the coordinate
or, as a vector, has it first; the further coordinates such a vector labels "on NAME" (KINGS.3500D,
GOGID.100D, ...); the coordinates an enumeration prints, `(println "<name> yields" ...)`, as its
sfo-bbvalue-timetravel-enumeration does for a single TNLDY; and the agents and the functions of no
argument ("...current-by-z-tnldy-clock3"), whose value is read on the
engine's clock, (/ (+ C (. (new Date) getTime)) 86400000) or the clock agent it defines so,
@z-tnldy-clock3: either is Z now. Every one is linear in Z,

    c(Z) = (Z - Ztp) / U

and reaches an SFO-BB x when Z = Ztp + U·x. This file reads each coordinate's expression from the
source and evaluates it with Z as an unknown, in exact rationals, the author's literals taken exactly
as written (the engine itself computes in doubles). Coordinates that are the same linear map are one
map, with every place the engine writes it. Expressions not linear in Z (a frequency in 1/Z, a string)
place no SFO-BB and are listed as excluded, with the reason.

The sources are the ones Alien Corridor publishes, byte for byte the engine's (.paths.json "engine").
Standard library only.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from decimal import Decimal
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "stage"))
from paths import path  # noqa: E402
from exact import fparse, fstr  # noqa: E402

OUT = ROOT / "docs" / "data" / "functions.json"


# ---- reading Clojure ---------------------------------------------------------------------------

def tokens(s: str):
    """(kind, text, offset): brackets, strings, character literals and atoms; comments skipped."""
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c in " \t\r\n,":
            i += 1
        elif c == ";":
            while i < n and s[i] != "\n":
                i += 1
        elif c in "()[]{}":
            yield c, c, i
            i += 1
        elif c == '"':
            j = i + 1
            while s[j] != '"':
                j += 2 if s[j] == "\\" else 1
            yield "str", s[i + 1:j], i
            i = j + 1
        elif c == "\\":
            j = i + 2
            while j < n and s[j] not in " \t\r\n,()[]{}":
                j += 1
            yield "chr", s[i:j], i
            i = j
        else:
            j = i
            while j < n and s[j] not in " \t\r\n,()[]{}\";":
                j += 1
            yield "sym", s[i:j], i
            i = j


OPEN = {"(": "list", "[": "vec", "{": "map"}


def read(s: str) -> list:
    """Top-level forms as nested tuples (kind, offset, children...) / (kind, text, offset)."""
    stack = [["top", 0]]
    for kind, text, at in tokens(s):
        if kind in OPEN:
            stack.append([OPEN[kind], at])
        elif kind in ")]}":
            node = stack.pop()
            stack[-1].append(tuple(node))
        else:
            stack[-1].append((kind, text, at))
    if len(stack) != 1:
        raise ValueError("unbalanced brackets")
    return stack[0][2:]


def is_sym(x, text=None) -> bool:
    return x[0] == "sym" and (text is None or x[1] == text)


# ---- evaluating a coordinate, exactly, with Z unknown --------------------------------------------

class NotLinear(Exception):
    pass


def literal(t: str) -> F | None:
    if re.fullmatch(r"[+-]?\d+/\d+", t):
        a, b = t.split("/")
        return F(int(a), int(b))
    if re.fullmatch(r"[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?M?", t):
        return F(Decimal(t.rstrip("M")))
    if re.fullmatch(r"[+-]?\d+N", t):
        return F(int(t[:-1]))
    return None


def is_clock(x) -> bool:
    """The engine's reading of the present TNLDY: (/ (+ C (. (new Date) getTime)) 86400000), C its constant."""
    try:
        return (x[0] == "list" and len(x) == 5 and is_sym(x[2], "/") and is_sym(x[4], "86400000")
                and x[3][0] == "list" and len(x[3]) == 5 and is_sym(x[3][2], "+") and literal(x[3][3][1]) is not None
                and x[3][4][0] == "list" and len(x[3][4]) == 5 and is_sym(x[3][4][2], ".") and is_sym(x[3][4][4], "getTime")
                and x[3][4][3][0] == "list" and is_sym(x[3][4][3][2], "new") and is_sym(x[3][4][3][3], "Date"))
    except (IndexError, TypeError):
        return False


CLOCK_AGENTS: set[str] = set()     # "@name" for each agent the engine defines as its clock reading, e.g. @z-tnldy-clock3


def has_clock(x) -> bool:
    return (is_clock(x) or (x[0] == "sym" and x[1] in CLOCK_AGENTS)
            or (x[0] in ("list", "vec", "map") and any(has_clock(k) for k in x[2:])))


def find_clock_agents(forms) -> None:
    """(def name (agent <the clock reading>)): its deref, @name, reads Z now."""
    for x in forms:
        if (x[0] == "list" and len(x) == 5 and is_sym(x[2], "def") and x[3][0] == "sym" and x[4][0] == "list"
                and len(x[4]) == 4 and is_sym(x[4][2], "agent") and is_clock(x[4][3])):
            CLOCK_AGENTS.add("@" + x[3][1])


def lin(x) -> tuple[F, F]:
    """(a, b) with the expression = a·Z + b; the engine's clock reading is Z, now."""
    if is_clock(x) or (x[0] == "sym" and x[1] in CLOCK_AGENTS):
        return F(1), F(0)
    if x[0] == "sym":
        if x[1] == "Z":
            return F(1), F(0)
        v = literal(x[1])
        if v is None:
            raise NotLinear(f"the symbol {x[1]}")
        return F(0), v
    if x[0] != "list" or len(x) < 3 or not is_sym(x[2]):
        raise NotLinear("not an arithmetic form" if x[0] != "str" else "a string")
    op, args = x[2][1], [lin(a) for a in x[3:]]
    if op == "+":
        return sum((a for a, _ in args), F(0)), sum((b for _, b in args), F(0))
    if op == "-":
        if len(args) == 1:
            return -args[0][0], -args[0][1]
        a0, b0 = args[0]
        for a, b in args[1:]:
            a0, b0 = a0 - a, b0 - b
        return a0, b0
    if op == "*":
        a0, b0 = args[0]
        for a, b in args[1:]:
            if a0 and a:
                raise NotLinear("Z times Z")
            a0, b0 = a0 * b + a * b0, b0 * b
        return a0, b0
    if op == "/":
        if len(args) == 1:
            if args[0][0]:
                raise NotLinear("1/Z")
            return F(0), 1 / args[0][1]
        a0, b0 = args[0]
        for a, b in args[1:]:
            if a:
                raise NotLinear("division by Z")
            a0, b0 = a0 / b, b0 / b
        return a0, b0
    if op == "Math/pow":
        (a1, b1), (a2, b2) = args
        if a1 or a2 or b2.denominator != 1:
            raise NotLinear("a power of Z, or a fractional power")
        return F(0), b1 ** int(b2)
    raise NotLinear(f"the operation {op}")


def coordinates(body) -> list[tuple[str, object]]:
    """[(label, (a, b) or the reason it is not linear)]: the function's own coordinate first (label ""),
    then each one the vector labels "on NAME"."""
    if body[0] == "list" and len(body) == 4 and is_sym(body[2], "do") and body[3][0] == "vec":
        els = list(body[3][2:])
        if not els:
            return [("", NotLinear("an empty vector"))]
        out = []
        for i, e in enumerate(els):
            if i and not (i + 1 < len(els) and els[i + 1][0] == "str" and els[i + 1][1].strip().startswith("on ")):
                continue
            if i and e[0] == "str":
                continue
            label = "" if i == 0 else els[i + 1][1].strip()[3:].strip()
            try:
                out.append((label, lin(e)))
            except NotLinear as why:
                out.append((label, why))
        return out
    try:
        return [("", lin(body))]
    except NotLinear as why:
        return [("", why)]


def short(name: str) -> str:
    """The name as read: without the earmuffs, the jd- prefix of the dated twin, or the -by-tnldy suffix."""
    n = name.strip("*")
    n = re.sub(r"^jd-", "", n)
    return re.sub(r"-by-tnldy$", "", n)


def sources_hash(files: list[Path]) -> str:
    h = hashlib.sha256()
    for f in files:
        h.update(f.relative_to(path("engine")).as_posix().encode() + b"\0" + f.read_bytes() + b"\0")
    return h.hexdigest()


def main() -> int:
    engine = path("engine")
    files = sorted(engine.rglob("*.clj"))
    digest = sources_hash(files)
    if "--if-changed" in sys.argv and OUT.exists() and json.loads(OUT.read_text()).get("sources_sha256") == digest:
        return 0
    maps: dict[tuple[F, F], dict] = {}
    excluded = []
    counts = {"function": 0, "vector": 0, "printed": 0, "agent": 0, "current": 0}
    defs = 0

    def keep(got, where):
        a, b = got
        if a == 0:
            excluded.append({**where, "why": "constant in Z"})
            return
        maps.setdefault((a, b), {"where": []})["where"].append(where)
        counts[where["kind"]] += 1

    parsed = {f: read(f.read_text(errors="replace")) for f in files}
    for forms in parsed.values():
        find_clock_agents(forms)
    for f in files:
        rel = f.relative_to(engine).as_posix()
        edition = rel.split("/")[0]
        src = f.read_text(errors="replace")

        def line_at(at: int) -> int:
            return src.count("\n", 0, at) + 1

        def walk(x, inside: str | None):
            nonlocal defs
            if x[0] not in ("list", "vec", "map"):
                return
            kids = x[2:]
            here = inside
            if x[0] == "list" and len(kids) >= 3 and is_sym(kids[0], "def") and kids[1][0] == "sym":
                name, val = kids[1][1], kids[2]
                here = name
                where = {"edition": edition, "file": rel, "line": line_at(x[1]), "def": name}
                if (val[0] == "list" and len(val) >= 5 and is_sym(val[2], "fn") and val[3][0] == "vec"
                        and len(val[3]) == 3 and is_sym(val[3][2], "Z")):
                    defs += 1                                   # a function of TNLDY
                    printed = any(is_yields(y) for y in descend(val[4]))
                    for label, got in coordinates(val[4]):
                        w = {**where, "kind": "function" if label == "" else "vector", "label": label}
                        if not isinstance(got, NotLinear):
                            keep(got, w)
                        elif not printed:                       # an enumeration prints its coordinates instead
                            excluded.append({**w, "why": str(got)})
                elif has_clock(val):                            # an agent, a value or a function of now, on the clock
                    kind, e = "agent", val
                    if val[0] == "list" and len(val) == 4 and is_sym(val[2], "agent"):
                        e = val[3]
                    elif (val[0] == "list" and len(val) == 5 and is_sym(val[2], "fn") and val[3][0] == "vec"
                          and len(val[3]) == 2):
                        kind, e = "current", val[4]
                    for label, got in coordinates(e):
                        w = {**where, "kind": kind if label == "" else "vector", "label": label}
                        if not isinstance(got, NotLinear):
                            keep(got, w)
                        else:
                            excluded.append({**w, "why": str(got)})
            if is_yields(x):                                    # (println "<name> yields" <coordinate>)
                label = re.sub(r"\s*yields\s*$", "", kids[1][1].strip())
                w = {"edition": edition, "file": rel, "line": line_at(x[1]), "def": inside or "", "kind": "printed",
                     "label": label}
                try:
                    keep(lin(kids[2]), w)
                except NotLinear as why:
                    excluded.append({**w, "why": str(why)})
            for k in kids:
                walk(k, here)

        for form in parsed[f]:
            walk(form, None)

    out, where_all = [], {}
    order = {"function": 0, "printed": 1, "current": 2, "agent": 3, "vector": 4}
    for (a, b), m in maps.items():
        ztp, unit = -b / a, 1 / a
        w = sorted(m["where"], key=lambda r: (order[r["kind"]], r["edition"] != "primary", r["file"], r["line"]))
        mid = "f" + hashlib.sha256(f"{fstr(a)}|{fstr(b)}".encode()).hexdigest()[:10]
        kinds: dict[str, int] = {}
        for r in w:
            kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
        out.append({"id": mid, "name": read_name(w[0]), "names": sorted({read_name(r) for r in w}),
                    "ztp": fstr(ztp), "unit": fstr(unit), "a": fstr(a), "b": fstr(b), "kinds": kinds,
                    "at": f"{w[0]['file']}:{w[0]['line']}"})
        where_all[mid] = w
    out.sort(key=lambda m: (fparse(m["ztp"]), fparse(m["unit"]), m["id"]))
    groups: dict[tuple, dict] = {}
    for e in excluded:
        g = groups.setdefault((e["why"], e["kind"], e["label"] or short(e["def"])),
                              {"why": e["why"], "kind": e["kind"], "name": e["label"] or short(e["def"]), "count": 0,
                               "at": f"{e['file']}:{e['line']}"})
        g["count"] += 1
    reasons: dict[str, int] = {}
    for e in excluded:
        reasons[e["why"]] = reasons.get(e["why"], 0) + 1
    doc = {"note": "The MDQNM engine's coordinates of TNLDY, as exact linear maps c(Z) = (Z - ztp)/unit; each reaches "
                   "SFO-BB x at Z = ztp + unit·x. kinds counts where the engine writes each: function = a function of Z; "
                   "vector = a coordinate its vector labels 'on NAME'; printed = an enumeration's '<name> yields "
                   "<coordinate>'; current = a function of no argument read on the engine's clock; agent = an agent or "
                   "value read on it. Exact rationals are decimals when they end, else n/d. Every place is listed in "
                   "functions-where.json.",
           "sources": len(files), "sources_sha256": digest, "functions_of_z": defs, "coordinates": counts, "maps": out,
           "excluded": sorted(groups.values(), key=lambda g: (-g["count"], g["name"])), "excluded_counts": reasons}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")))
    (OUT.parent / "functions-where.json").write_text(json.dumps(where_all, ensure_ascii=False, separators=(",", ":")))
    print(f"engine: clock agents {sorted(CLOCK_AGENTS)}")
    print(f"engine: {len(files)} source files, {defs} functions of Z; coordinates {counts} -> {len(out)} distinct "
          f"maps; excluded {len(excluded)} ({len(groups)} kinds): {reasons}")
    return 0


def descend(x):
    yield x
    if x[0] in ("list", "vec", "map"):
        for k in x[2:]:
            yield from descend(k)


def is_yields(x) -> bool:
    return (x[0] == "list" and len(x) == 5 and is_sym(x[2], "println") and x[3][0] == "str"
            and re.search(r"\byields\s*$", x[3][1].strip()) is not None and x[4][0] != "str")


def read_name(r: dict) -> str:
    if r["kind"] == "vector":
        return r["label"]
    if r["kind"] == "printed":
        return short(r["label"])
    return short(r["def"])


if __name__ == "__main__":
    sys.exit(main())
