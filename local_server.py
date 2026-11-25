# -*- coding: utf-8 -*-
"""Local progress dashboard for the 2026 diaper recruitment and product tests."""
from __future__ import annotations

import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from stats import build_stats_safe

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
PORT = int(os.environ.get("MONITOR_PORT", "8766"))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/api/stats", "/api/stats/"):
            payload, status = build_stats_safe()
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def log_message(self, fmt, *args):
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))


def main():
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Diapers 2026 monitor: http://127.0.0.1:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
