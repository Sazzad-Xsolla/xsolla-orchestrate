#!/usr/bin/env python3
"""Serve Field Team locally. Records decisions; never executes actions."""
import hmac
import json
import os
import secrets
import signal
import socket
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
SKILL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL / "scripts"))
import status
from field_team import record_decision
THEME = None
CACHE_SECONDS = 2

def resolve_run(arg):
    p = Path(arg).expanduser().resolve()
    if (p / "plan.json").is_file():
        return p
    runs = sorted((p / ".xsolla-orchestrator").glob("*/plan.json"), key=lambda f: f.stat().st_mtime)
    if not runs:
        raise ValueError("No Xsolla run found; choose a .xsolla-orchestrator run or its project")
    return runs[-1].parent

def free_port(start):
    for port in range(start, start + 50):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise ValueError("No free dashboard port")

class Handler(BaseHTTPRequestHandler):
    run = None
    token = secrets.token_hex(32)
    _cache = (0.0, None)
    def log_message(self, *args):
        pass
    def _send(self, code, body, ctype="application/json"):
        payload = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        for key, value in {"Content-Type": ctype + "; charset=utf-8", "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer", "Content-Length": str(len(payload))}.items():
            self.send_header(key, value)
        self.end_headers()
        try:
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError):
            pass
    def _host_ok(self):
        port = self.server.server_address[1]
        return self.headers.get("Host") in (f"127.0.0.1:{port}", f"localhost:{port}")
    def _data(self):
        at, data = type(self)._cache
        if data is None or time.monotonic() - at > CACHE_SECONDS:
            data = status.collect(self.run)
            type(self)._cache = (time.monotonic(), data)
        return data
    def do_GET(self):
        if not self._host_ok():
            self._send(403, '{"error":"Invalid local host"}')
            return
        try:
            path = urlsplit(self.path).path
            if path in ("/", "/index.html"):
                page = status.render_html(self._data(), THEME).replace("__SESSION__", self.token)
                self._send(200, page, "text/html")
            elif path == "/data.json":
                self._send(200, json.dumps(self._data()))
            elif path == "/health":
                self._send(200, json.dumps({"run": str(self.run), "service": "xsolla-field-team"}))
            else:
                self._send(404, '{"error":"Not found"}')
        except (OSError, ValueError, KeyError) as exc:
            self._send(503, json.dumps({"error": str(exc)}))
    def do_POST(self):
        if urlsplit(self.path).path != "/decision":
            self._send(405, '{"error":"Only decision recording is supported"}')
            return
        port = self.server.server_address[1]
        origins = (f"http://127.0.0.1:{port}", f"http://localhost:{port}")
        if not self._host_ok() or self.headers.get("Origin") not in origins or not hmac.compare_digest(self.headers.get("X-Field-Team-Token", ""), self.token):
            self._send(403, '{"error":"Open the local dashboard and review the request again"}')
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 32768 or self.headers.get_content_type() != "application/json":
                raise ValueError("Expected a small JSON decision")
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError("Expected a decision object")
            if body.get("run_key") != status.collect(self.run)["run_key"]:
                raise ValueError("Run changed; review the request again")
            result = record_decision(self.run, body.get("id"), body.get("decision"), body.get("fingerprint"), body.get("source", "mission-control"))
            type(self)._cache = (0.0, None)
            self._send(200, json.dumps(result))
        except (ValueError, TypeError, KeyError) as exc:
            self._send(409, json.dumps({"error": str(exc)}))
        except OSError as exc:
            self._send(503, json.dumps({"error": str(exc)}))

def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: serve_dashboard.py RUN_OR_PROJECT [--port 8790] [--theme xsolla]")
    run = resolve_run(sys.argv[1])
    start = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8790
    global THEME
    THEME = sys.argv[sys.argv.index("--theme") + 1] if "--theme" in sys.argv else None
    Handler.run = run
    server = ThreadingHTTPServer(("127.0.0.1", free_port(start)), Handler)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    (run / "dashboard.url").write_text(url + "\n")
    (run / "dashboard.pid").write_text(f"{os.getpid()}\n")
    print(f"dashboard for {run.name}: {url}", flush=True)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        if (run / "dashboard.pid").exists() and (run / "dashboard.pid").read_text().strip() == str(os.getpid()):
            for name in ("dashboard.url", "dashboard.pid"):
                (run / name).unlink(missing_ok=True)
if __name__ == "__main__":
    main()
