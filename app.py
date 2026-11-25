# -*- coding: utf-8 -*-
"""Vercel / local Flask app: dashboard files + /api/stats."""
from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify, send_from_directory

from stats import build_stats_safe

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "static"

app = Flask(__name__, static_folder=str(PUBLIC), static_url_path="")


@app.get("/api/stats")
@app.get("/api/stats/")
def stats():
    payload, status = build_stats_safe()
    response = jsonify(payload)
    response.status_code = status
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/")
def index():
    return send_from_directory(PUBLIC, "index.html")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8766, debug=True)
