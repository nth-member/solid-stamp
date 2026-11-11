"""The smallest ntfy client: publish a message as JSON, or delete a scheduled one. Standard library only.

The server and topic are read from the untracked .ntfy.json, {"server": "https://ntfy.sh", "topic": "..."}.
The topic is the only secret: whoever knows it can read the messages, so it is never written anywhere else.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / ".ntfy.json"
AGENT = "solid-stamp (nth-member.github.io)"


class Refused(Exception):
    def __init__(self, status: int, body: str):
        super().__init__(f"HTTP {status}: {body[:200]}")
        self.status = status


def config() -> dict | None:
    return json.loads(CONFIG.read_text()) if CONFIG.exists() else None


def publish(cfg: dict, msg: dict, delay_s: int | None = None) -> dict:
    """POST the message to the server's root; delay_s, a Unix time in seconds, schedules it (10 s to 3 days ahead)."""
    body = {"topic": cfg["topic"], **msg}
    if delay_s is not None:
        body["delay"] = str(delay_s)
    req = urllib.request.Request(cfg["server"].rstrip("/") + "/", data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": AGENT})
    return _send(req)


def delete(cfg: dict, sequence_id: str) -> dict:
    """Delete a message by sequence ID: a scheduled one is never delivered; a delivered one is removed."""
    req = urllib.request.Request(f"{cfg['server'].rstrip('/')}/{cfg['topic']}/{sequence_id}", method="DELETE",
                                 headers={"User-Agent": AGENT})
    return _send(req)


def _send(req) -> dict:
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            text = r.read().decode()
            return json.loads(text) if text.strip().startswith("{") else {"ok": True}
    except urllib.error.HTTPError as e:
        raise Refused(e.code, e.read().decode(errors="replace")) from None
