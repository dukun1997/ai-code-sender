#!/usr/bin/env python3
"""Mock IDE bridge for local testing without installing JetBrains plugin."""

from __future__ import annotations

import argparse
import json
import secrets
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HEADER = "X-OpenCode-Ide-Authorization"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_lock(lock_dir: Path, port: int, token: str, workspace: str) -> None:
    lock_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "workspaceFolders": [workspace],
        "ideName": "Mock IntelliJ IDEA",
        "transport": "http",
        "url": f"http://127.0.0.1:{port}",
        "authToken": token,
        "pid": 99999,
        "updatedAt": utc_now(),
    }
    (lock_dir / f"{port}.lock").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def make_handler(token: str, workspace: str):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/health":
                self._json(200, {"ok": True})
                return

            if self.path == "/context/current":
                provided = self.headers.get(HEADER)
                if provided != token:
                    self._json(401, {"error": "unauthorized"})
                    return

                payload = {
                    "contextType": "class_fallback",
                    "workspace": workspace,
                    "filePath": f"{workspace}/src/main/java/com/example/FooService.java",
                    "className": "FooService",
                    "lineStart": 12,
                    "lineEnd": 48,
                    "text": "public class FooService {\\n    public String say() { return \"hello\"; }\\n}",
                    "truncated": False,
                    "updatedAt": utc_now(),
                    "revision": 42,
                }
                self._json(200, payload)
                return

            self._json(404, {"error": "not_found"})

        def _json(self, status: int, payload: dict) -> None:
            raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, format: str, *args):
            return

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=61337)
    parser.add_argument("--workspace", default=str(Path.cwd()))
    parser.add_argument("--lock-dir", default=str(Path.home() / ".opencode" / "ide"))
    args = parser.parse_args()

    token = secrets.token_urlsafe(24)
    write_lock(Path(args.lock_dir), args.port, token, args.workspace)

    server = HTTPServer(("127.0.0.1", args.port), make_handler(token, args.workspace))
    print(f"mock ide bridge running on 127.0.0.1:{args.port}")
    print(f"workspace={args.workspace}")
    print(f"lock={Path(args.lock_dir) / f'{args.port}.lock'}")
    print(f"token={token}")
    server.serve_forever()


if __name__ == "__main__":
    raise SystemExit(main())
