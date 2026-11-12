"""A trigger's alert and digest: the record kept in docs/log/, and the ntfy messages made from it.

The alert goes out at the trigger's instant (scheduled ahead on the ntfy server): the TNLDY, the SFO-BBs
that match there and the spectrum's count. The digest replaces it in place once the window has closed and
settled: the same, with REVOTT STAMPS' stamp of the feeds about Z. The full spectrum -- every MDQNM
function at Z, on an SFO-BB or between two -- and every item are on the digest page; the record keeps the
spectrum's SHA-256 and its functions file's, so the page can show that it reads the same spectrum.
"""
from __future__ import annotations

import hashlib
import json
import re
from fractions import Fraction as F

import solid
from exact import fmt, fparse

MAX_BYTES = 4000           # ntfy keeps a message of up to 4,096 bytes as a message, not an attachment


def md(text: str) -> str:
    """Text shown as itself under Markdown: its emphasis, code and link characters escaped."""
    return re.sub(r"([\\`*_\[\]<>#|])", r"\\\1", text)


def trim(text: str, n: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def spectrum_summary(z: F) -> dict:
    sp = solid.spectrum(z)
    counts = {"on": 0, "between": 0, "before": 0, "after": 0}
    for _k, _c, where, _lo, _hi in sp:
        counts[where] += 1
    return {"maps": len(sp), "counts": counts, "sha256": solid.spectrum_hash(sp),
            "functions_sha256": solid.inputs()["functions.json"],
            "on": [[k, c, lo] for k, c, where, lo, _hi in sp if where == "on"]}


def window_text(settings: dict) -> str:
    sec = float(F(settings["eps"]) * solid.U * 86400)
    return f"±{sec / 60:g} min" if sec >= 60 else f"±{sec:g} s"


def stamp(d: dict, settings: dict) -> dict:
    """REVOTT STAMPS' stamp of the chosen feeds about Z, window ±100·ε TNLDY, on its reconciled clock. Each item
    is [seconds from Z, instant ms, how its time was read (p page, f feed, d day only, s first seen), source,
    headline, link, note, source's name]."""
    s = solid.stamps.stamp_z(fparse(d["z"]), F(settings["eps"]), settings["clock"], set(settings["domains"]), solid.U)
    cov = s.get("coverage", {"covered": [], "partly": [], "null": []})
    srcs = solid.stamps.data("sources.json")
    items = [it + [srcs.get(it[3], [it[3]])[0]] for it in s.get("items", [])]   # + the source's name
    return {"eps": settings["eps"], "clock": settings["clock"], "domains": sorted(settings["domains"]),
            "as_of": solid.stamps.data("index.json")["as_of"], "status": s["status"], "window": s["window"],
            "items": items, "covered": len(cov["covered"]), "partly": cov["partly"], "null": cov["null"],
            "gdelt": s.get("gdelt")}


def record(d: dict, settings: dict, near: list[dict]) -> dict:
    """The trigger as it stands now: what matched, the other matches inside its window (context only), the
    spectrum's summary, and the stamp of the feeds."""
    z = fparse(d["z"])
    return {**d, "nearby": near, "spectrum": spectrum_summary(z), "feeds": stamp(d, settings)}


# ---- the messages --------------------------------------------------------------------------------

def head(d: dict) -> str:
    ins = d["instants"]
    when = solid.nsukka(ins[0]) + " Nsukka" if ins else "passed over by the clock's recalibration"
    twice = f" (and again {solid.nsukka(ins[1])})" if len(ins) > 1 else ""
    return f"**{when}**{twice} · TNLDY **{d['z6']}**"


def matched(d: dict, room: int) -> list[str]:
    """The SFO-BBs that make this TNLDY, each with its reading: REVOTT's pairs, then the engine's functions."""
    out = []
    if d["pairs"]:
        s = fparse(d["pairs"][0]["y"]) + fparse(d["pairs"][0]["x"])
        out += [f"**REVOTT** · 14160 + 100·(Y + X), Y + X = {solid.fstr(s)}", ""]
        for n, p in enumerate(d["pairs"]):
            if n == room:
                out.append(f"- … and {len(d['pairs']) - room} more pairs")
                break
            out.append(f"- Y {p['y']}: {md(trim(solid.reading(p['yi']), 60))} · X {p['x']}: {md(trim(solid.reading(p['xi']), 60))}")
    if d["functions"]:
        out += (["" ] if out else []) + ["**MDQNM** · Ztp + U·x: the function's coordinate on SFO-BB x", ""]
        for n, f in enumerate(d["functions"]):
            if n == room:
                out.append(f"- … and {len(d['functions']) - room} more functions")
                break
            out.append(f"- {md(trim(f['name'], 70))} — on SFO-BB {f['x']}: {md(trim(solid.reading(f['xi']), 60))} "
                       f"({short_num(f['ztp'])} + {short_num(f['unit'])}·{paren(f['x'])})")
    return out


def paren(s: str) -> str:
    return f"({s})" if s.startswith("-") else s


def short_num(s: str) -> str:
    if "/" in s:
        return fmt(fparse(s), 6).rstrip("0").rstrip(".")
    return s


def spectrum_line(sp: dict) -> str:
    c = sp["counts"]
    return (f"**Spectrum** · all {sp['maps']} MDQNM functions read at this TNLDY: {c['on']} on an SFO-BB, "
            f"{c['between']} between two, {c['before'] + c['after']} beyond the first or last.")


def item_lines(feeds: dict, n: int) -> list[str]:
    out = []
    for it in feeds["items"][:n]:
        out.append(f"- {solid.hm(it[1])} {md(it[7])} — {md(trim(it[4], 110))}")
    if len(feeds["items"]) > n:
        out.append(f"- … {len(feeds['items']) - n} more on the digest page")
    return out


def feeds_line(feeds: dict, settings: dict) -> str:
    cov = f"{feeds['covered']} sources covered, {len(feeds['partly'])} partly, {len(feeds['null'])} NULL"
    return (f"**Feeds** {window_text(settings)} · {len(feeds['domains'])} domains · {len(feeds['items'])} items "
            f"({feeds['status']}; {cov})")


def fit(parts: list[list[str]], limit: int = MAX_BYTES) -> str:
    """Join the sections; while too long, drop lines from the end of the longest droppable section."""
    parts = [list(p) for p in parts]
    while len("\n".join("\n".join(p) for p in parts if p).encode()) > limit:
        p = max(parts[1:], key=len)
        if len(p) <= 1:
            break
        p.pop(-2 if len(p) > 2 else -1)
    return "\n".join("\n".join(p) for p in parts if p)


def title(d: dict) -> str:
    ins = d["instants"]
    t = solid.hm(ins[0]) if ins else "passed over"
    return f"{solid.CLASS_LABEL[d['class']]} · {t} Nsukka · TNLDY {d['z6']}"


def links(d: dict, settings: dict) -> tuple[str | None, list[dict]]:
    page, live = solid.page_link(d, settings), solid.stamps_link(d, settings)
    actions = []
    if page:
        actions.append({"action": "view", "label": "Digest", "url": page})
    if live:
        actions.append({"action": "view", "label": "Stamp now", "url": live})
    return page or live, actions


def nearby_line(near: list[dict], settings: dict) -> list[str]:
    if not near:
        return []
    n = sum(len(x["pairs"]) + len(x["functions"]) for x in near)
    return ["", f"Also within {window_text(settings)}: {n} other SFO-BB matches at {len(near)} TNLDY, each its own stamp."]


def payload(d: dict, settings: dict, rec: dict | None, near: list[dict], late_minutes: int = 0) -> dict:
    """The ntfy message: the alert (rec None) or the digest. Its sequence_id is the trigger's id, so the
    digest replaces the alert in place."""
    sp = rec["spectrum"] if rec else spectrum_summary(fparse(d["z"]))
    parts = [[head(d), ""], matched(d, 12), ["", spectrum_line(sp)] + nearby_line(near, settings)]
    if rec is None:
        b = solid.stamps.span_of(fparse(d["z"]) - F(settings["eps"]) * solid.U, fparse(d["z"]) + F(settings["eps"]) * solid.U)[1]
        parts.append(["", f"**Feeds** {window_text(settings)} · the digest replaces this note when the window has "
                          f"closed ({solid.hm(b)}) and settled ({settings['settle_minutes']} min)."])
    else:
        lines = ["", feeds_line(rec["feeds"], settings), ""] + item_lines(rec["feeds"], settings["items_in_message"])
        if late_minutes > 30:
            lines += ["", f"_Sent {late_minutes // 60} h {late_minutes % 60} min after it settled._"]
        parts.append(lines)
    click, actions = links(d, settings)
    msg = {"title": title(d), "message": fit(parts), "markdown": True, "priority": settings["priority"][d["class"]],
           "tags": [d["class"].replace("+", "-")], "sequence_id": d["id"]}
    if click:
        msg["click"] = click
    if actions:
        msg["actions"] = actions
    return msg


def payload_hash(p: dict) -> str:
    return hashlib.sha256(json.dumps(p, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]
