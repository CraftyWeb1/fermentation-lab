"""Tableau de bord tactile local (ecran Raspberry Pi ou navigateur)."""

from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

DASH = Path(__file__).resolve().parent / "dashboard"
PORT = int(os.environ.get("FERMIA_DASH_PORT", "8765"))

COMMANDES_OK = {
    "yaourt",
    "biere",
    "pate",
    "terre",
    "demo",
    "chauffer",
    "refroidir",
    "stop",
    "auto",
    "von",
    "voff",
    "silence",
    "ouvrir",
    "fermer",
    "fini",
}


def demarrer_tableau(log, snapshot, executer, stop_event) -> None:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args) -> None:
            return

        def _send(self, code: int, body: bytes, mime: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", mime)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path in ("/", "/index.html"):
                page = (DASH / "index.html").read_bytes()
                self._send(200, page, "text/html; charset=utf-8")
                return
            if path == "/api/etat":
                corps = json.dumps(snapshot()).encode("utf-8")
                self._send(200, corps, "application/json")
                return
            self._send(404, b"not found", "text/plain")

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            if path != "/api/cmd":
                self._send(404, b"not found", "text/plain")
                return
            n = int(self.headers.get("Content-Length", "0") or 0)
            brut = self.rfile.read(n).decode("utf-8", errors="ignore")
            try:
                data = json.loads(brut or "{}")
            except json.JSONDecodeError:
                data = {}
            cmd = str(data.get("cmd") or "").strip().lower()
            if cmd not in COMMANDES_OK:
                self._send(400, b"cmd inconnue", "text/plain")
                return
            executer(cmd)
            self._send(200, b'{"ok":true}', "application/json")

    httpd = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)

    def run() -> None:
        log(f"Dashboard tactile : http://127.0.0.1:{PORT}")
        try:
            httpd.serve_forever()
        finally:
            httpd.server_close()

    threading.Thread(target=run, daemon=True, name="dashboard").start()

    def stop_when_done() -> None:
        stop_event.wait()
        httpd.shutdown()

    threading.Thread(target=stop_when_done, daemon=True).start()
