#!/usr/bin/env python3
"""Cellar brew log server. Serves index.html and stores the log in data.json.

    python3 server.py
    open http://127.0.0.1:8000
"""

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data.json")
INDEX = os.path.join(ROOT, "index.html")
HOST = "0.0.0.0"
PORT = 8000
MAX_BODY = 5_000_000
LOCK = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, PUT, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def path_only(self):
        return self.path.split("?", 1)[0].rstrip("/") or "/"

    def do_OPTIONS(self):
        self.send_response(204)
        self.cors()
        self.end_headers()

    def do_GET(self):
        path = self.path_only()
        if path == "/data":
            self.send_data()
            return
        if path in ("/", "/index.html"):
            self.send_index()
            return
        self.send_error(404)

    def send_index(self):
        try:
            with open(INDEX, "rb") as handle:
                body = handle.read()
        except OSError:
            self.send_error(404, "index.html is missing")
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_data(self):
        with LOCK:
            try:
                with open(DATA, "rb") as handle:
                    body = handle.read()
            except FileNotFoundError:
                body = b"null"
        self.send_response(200)
        self.cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_PUT(self):
        if self.path_only() != "/data":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = -1
        if length < 0 or length > MAX_BODY:
            self.send_response(400)
            self.cors()
            self.end_headers()
            return
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = None
        if not isinstance(data, dict) or not isinstance(data.get("recipes"), list):
            self.send_response(400)
            self.cors()
            self.end_headers()
            return
        tmp = DATA + ".tmp"
        with LOCK:
            with open(tmp, "wb") as handle:
                handle.write(raw)
            os.replace(tmp, DATA)
        self.send_response(204)
        self.cors()
        self.end_headers()


if __name__ == "__main__":
    print(f"Cellar is at http://127.0.0.1:{PORT}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
