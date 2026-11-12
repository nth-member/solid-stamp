#!/usr/bin/env python3
"""A stand-in for the ntfy server, for rehearsals: answers every publish and delete, and logs each to a file.

    python3 tests/fake_ntfy.py PORT LOGFILE
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT, LOG = int(sys.argv[1]), sys.argv[2]
n = 0


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def answer(self, body: dict):
        global n
        n += 1
        with open(LOG, "a") as f:
            f.write(json.dumps({"method": self.command, "path": self.path, **body}) + "\n")
        data = json.dumps({"id": f"fake{n}", "time": 0}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        self.answer(json.loads(raw or b"{}"))

    def do_DELETE(self):
        self.answer({})


HTTPServer(("127.0.0.1", PORT), H).serve_forever()
