#!/usr/bin/env python3
"""OpenCode IDE context injector.

Reads lock files produced by the JetBrains plugin bridge, fetches current context,
and prints either the context JSON or a prompt with explicit [IDE Context] injection.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

LOCK_DIR_ENV = "OPENCODE_IDE_LOCK_DIR"
DEFAULT_LOCK_DIR = Path.home() / ".opencode" / "ide"
TOKEN_HEADER = "X-OpenCode-Ide-Authorization"
LOCK_STALE_SECONDS = 45
FORMAT_ENV = "OPENCODE_IDE_CONTEXT_FORMAT"


@dataclass
class LockRecord:
    path: Path
    workspace_folders: list[str]
    url: str
    auth_token: str
    updated_ts: int


@dataclass
class ContextSnapshot:
    payload: dict[str, Any]

    @property
    def context_type(self) -> str:
        return str(self.payload.get("contextType") or "unknown")

    @property
    def file_path(self) -> str:
        return str(self.payload.get("filePath") or "")

    @property
    def line_start(self) -> Optional[int]:
        value = self.payload.get("lineStart")
        return int(value) if isinstance(value, int) else None

    @property
    def line_end(self) -> Optional[int]:
        value = self.payload.get("lineEnd")
        return int(value) if isinstance(value, int) else None

    @property
    def class_name(self) -> str:
        return str(self.payload.get("className") or "")

    @property
    def text(self) -> str:
        return str(self.payload.get("text") or "")

    @property
    def revision(self) -> int:
        value = self.payload.get("revision")
        return int(value) if isinstance(value, int) else 0


def _lock_dir() -> Path:
    configured = os.environ.get(LOCK_DIR_ENV, "").strip()
    if configured:
        return Path(configured).expanduser()
    return DEFAULT_LOCK_DIR


def _discover_locks() -> list[LockRecord]:
    lock_dir = _lock_dir()
    if not lock_dir.exists() or not lock_dir.is_dir():
        return []

    results: list[LockRecord] = []
    for file in lock_dir.glob("*.lock"):
        try:
            payload = json.loads(file.read_text(encoding="utf-8"))
            workspace_folders = [
                str(x) for x in payload.get("workspaceFolders", []) if isinstance(x, str)
            ]
            url = str(payload.get("url") or "")
            auth_token = str(payload.get("authToken") or "")
            if not url or not auth_token:
                continue

            updated_at = str(payload.get("updatedAt") or "")
            updated_ts = 0
            if updated_at:
                try:
                    updated_ts = int(datetime.fromisoformat(updated_at.replace("Z", "+00:00")).timestamp())
                except Exception:
                    updated_ts = 0

            results.append(
                LockRecord(
                    path=file,
                    workspace_folders=workspace_folders,
                    url=url.rstrip("/"),
                    auth_token=auth_token,
                    updated_ts=updated_ts,
                )
            )
        except Exception:
            continue
    return results


def _choose_lock(cwd: Path, locks: list[LockRecord]) -> Optional[LockRecord]:
    cwd = cwd.resolve()
    now = int(time.time())

    best: tuple[tuple[int, int, int], LockRecord] | None = None
    for lock in locks:
        for folder in lock.workspace_folders:
            try:
                resolved = Path(folder).resolve()
            except Exception:
                continue
            if str(cwd) == str(resolved) or str(cwd).startswith(str(resolved) + os.sep):
                freshness = 1 if lock.updated_ts and (now - lock.updated_ts) <= LOCK_STALE_SECONDS else 0
                score = (freshness, len(str(resolved)), lock.updated_ts)
                if best is None or score > best[0]:
                    best = (score, lock)

    return best[1] if best else None


def _fetch_context(lock: LockRecord) -> ContextSnapshot:
    request = urllib.request.Request(
        url=f"{lock.url}/context/current",
        headers={TOKEN_HEADER: lock.auth_token},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=1.5) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return ContextSnapshot(payload=payload)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"context endpoint rejected request: HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"failed to reach context endpoint: {exc}") from exc


def _context_priority(context_type: str) -> int:
    mapping = {
        "selection": 3,
        "class_fallback": 2,
        "caret_window": 1,
        "none": 0,
    }
    return mapping.get(context_type, 0)


def _select_best_snapshot(locks: list[LockRecord]) -> Optional[ContextSnapshot]:
    now = int(time.time())
    best: tuple[tuple[int, int, int, int], ContextSnapshot] | None = None
    for lock in locks:
        try:
            snapshot = _fetch_context(lock)
        except Exception:
            continue
        if not snapshot.text.strip():
            continue
        freshness = 1 if lock.updated_ts and (now - lock.updated_ts) <= LOCK_STALE_SECONDS else 0
        score = (_context_priority(snapshot.context_type), snapshot.revision, freshness, lock.updated_ts)
        if best is None or score > best[0]:
            best = (score, snapshot)
    return best[1] if best else None


def _display_path(snapshot: ContextSnapshot, cwd: Path) -> str:
    file_path = snapshot.file_path.strip()
    if not file_path:
        return ""

    base = snapshot.payload.get("workspace")
    base_path = str(base).strip() if isinstance(base, str) else str(cwd.resolve())
    try:
        relative = os.path.relpath(file_path, start=base_path)
        if relative != "." and not relative.startswith(".."):
            return relative.replace(os.sep, "/")
    except Exception:
        pass
    return file_path


def _range_text(snapshot: ContextSnapshot) -> str:
    if snapshot.line_start is None or snapshot.line_end is None:
        return ""
    if snapshot.line_start == snapshot.line_end:
        return f"L{snapshot.line_start}"
    return f"L{snapshot.line_start}-L{snapshot.line_end}"


def _render_context_full(snapshot: ContextSnapshot) -> str:
    range_text = ""
    if snapshot.line_start and snapshot.line_end:
        range_text = f"L{snapshot.line_start}-L{snapshot.line_end}"

    class_line = f"class: {snapshot.class_name}\n" if snapshot.class_name else ""
    body = snapshot.text.rstrip()

    return (
        "[IDE Context]\n"
        f"type: {snapshot.context_type}\n"
        f"file: {snapshot.file_path}\n"
        f"range: {range_text}\n"
        f"revision: {snapshot.revision}\n"
        f"{class_line}"
        "content:\n"
        f"{body}\n"
        "[/IDE Context]"
    )


def _render_context_compact(snapshot: ContextSnapshot, cwd: Path) -> str:
    display = _display_path(snapshot, cwd)
    if not display:
        return ""
    range_text = _range_text(snapshot)
    head = f"@{display}#{range_text}" if range_text else f"@{display}"
    if snapshot.context_type == "class_fallback" and snapshot.class_name:
        return f"{head}\nclass: {snapshot.class_name}"
    return head


def _render_context(snapshot: ContextSnapshot, cwd: Path, format_name: str) -> str:
    if format_name == "full":
        return _render_context_full(snapshot)
    return _render_context_compact(snapshot, cwd)


def _inject(prompt: str, snapshot: ContextSnapshot, cwd: Path, format_name: str) -> str:
    context_block = _render_context(snapshot, cwd, format_name)
    prompt = prompt.rstrip("\n")
    if not context_block:
        return prompt
    if not prompt:
        return context_block
    return f"{context_block}\n\n{prompt}"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OpenCode IDE context injector")
    sub = parser.add_subparsers(dest="cmd", required=True)

    show = sub.add_parser("show", help="show current context JSON")
    show.add_argument("--cwd", default=os.getcwd(), help="working directory for workspace match")

    inject = sub.add_parser("inject", help="inject IDE context into prompt")
    inject.add_argument("--cwd", default=os.getcwd(), help="working directory for workspace match")
    inject.add_argument("--prompt", default="", help="prompt text")
    inject.add_argument(
        "--stdin", action="store_true", help="read prompt from stdin (overrides --prompt)"
    )
    default_format = os.environ.get(FORMAT_ENV, "compact").strip().lower()
    if default_format not in {"compact", "full"}:
        default_format = "compact"
    inject.add_argument(
        "--format",
        choices=["compact", "full"],
        default=default_format,
        help=f"injection format (default from ${FORMAT_ENV} or compact)",
    )

    return parser.parse_args()


def _resolve_context(cwd: Path) -> ContextSnapshot:
    locks = _discover_locks()
    if not locks:
        raise RuntimeError(f"no lock files found under {_lock_dir()}")

    lock = _choose_lock(cwd, locks)
    primary_error: Optional[Exception] = None
    if lock:
        try:
            snapshot = _fetch_context(lock)
            if snapshot.text.strip():
                return snapshot
        except Exception as exc:
            primary_error = exc
    else:
        primary_error = RuntimeError(f"no matching lock found for cwd {cwd}")

    fallback = _select_best_snapshot(locks)
    if fallback is not None:
        return fallback
    if primary_error is not None:
        raise primary_error
    raise RuntimeError("unable to resolve IDE context")


def main() -> int:
    args = _parse_args()
    cwd = Path(args.cwd)

    try:
        snapshot = _resolve_context(cwd)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.cmd == "show":
        print(json.dumps(snapshot.payload, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "inject":
        prompt = args.prompt
        if args.stdin:
            prompt = sys.stdin.read()
        print(_inject(prompt, snapshot, cwd, args.format))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
