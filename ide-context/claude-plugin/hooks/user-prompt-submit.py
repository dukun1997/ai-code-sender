#!/usr/bin/env python3
"""Claude UserPromptSubmit hook that injects current IDE context."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

LOCK_DIR_ENV = "OPENCODE_IDE_LOCK_DIR"
DEFAULT_LOCK_DIR = Path.home() / ".opencode" / "ide"
TOKEN_HEADER = "X-OpenCode-Ide-Authorization"
LOCK_STALE_SECONDS = 45
REQUEST_TIMEOUT_SECONDS = 1.5


@dataclass
class LockRecord:
    workspace_folders: list[str]
    url: str
    auth_token: str
    updated_ts: int


def _lock_dir() -> Path:
    configured = os.environ.get(LOCK_DIR_ENV, "").strip()
    if configured:
        return Path(configured).expanduser()
    return DEFAULT_LOCK_DIR


def _discover_locks() -> list[LockRecord]:
    lock_dir = _lock_dir()
    if not lock_dir.exists() or not lock_dir.is_dir():
        return []

    now = int(__import__("time").time())
    locks: list[LockRecord] = []
    for file in lock_dir.glob("*.lock"):
        try:
            payload = json.loads(file.read_text(encoding="utf-8"))
            workspace_folders = [
                str(item)
                for item in payload.get("workspaceFolders", [])
                if isinstance(item, str)
            ]
            url = str(payload.get("url") or "").rstrip("/")
            auth_token = str(payload.get("authToken") or "")
            if not url or not auth_token:
                continue

            updated_at = str(payload.get("updatedAt") or "")
            updated_ts = int(
                __import__("datetime")
                .datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                .timestamp()
            ) if updated_at else 0
            if updated_ts and now - updated_ts > LOCK_STALE_SECONDS:
                continue

            locks.append(
                LockRecord(
                    workspace_folders=workspace_folders,
                    url=url,
                    auth_token=auth_token,
                    updated_ts=updated_ts,
                )
            )
        except Exception:
            continue
    return locks


def _choose_lock(cwd: Path, locks: list[LockRecord]) -> Optional[LockRecord]:
    cwd = cwd.resolve()
    best: tuple[int, LockRecord] | None = None
    for lock in locks:
        for folder in lock.workspace_folders:
            try:
                resolved = Path(folder).resolve()
            except Exception:
                continue
            resolved_text = str(resolved)
            cwd_text = str(cwd)
            if cwd_text == resolved_text or cwd_text.startswith(resolved_text + os.sep):
                score = len(resolved_text)
                if best is None or score > best[0]:
                    best = (score, lock)
    return best[1] if best else None


def _fetch_context(lock: LockRecord) -> dict[str, Any]:
    request = urllib.request.Request(
        url=f"{lock.url}/context/current",
        headers={TOKEN_HEADER: lock.auth_token},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def _context_priority(snapshot: dict[str, Any]) -> int:
    mapping = {
        "selection": 3,
        "class_fallback": 2,
        "caret_window": 1,
        "none": 0,
    }
    return mapping.get(str(snapshot.get("contextType") or "none"), 0)


def _snapshot_has_text(snapshot: dict[str, Any]) -> bool:
    return bool(str(snapshot.get("text") or "").strip())


def _select_best_snapshot(locks: list[LockRecord]) -> Optional[dict[str, Any]]:
    best: tuple[tuple[int, int, int], dict[str, Any]] | None = None
    for lock in locks:
        try:
            snapshot = _fetch_context(lock)
        except Exception:
            continue
        if not _snapshot_has_text(snapshot):
            continue

        revision = int(snapshot.get("revision")) if isinstance(snapshot.get("revision"), int) else 0
        score = (_context_priority(snapshot), revision, lock.updated_ts)
        if best is None or score > best[0]:
            best = (score, snapshot)

    return best[1] if best else None


def _to_int(value: Any) -> Optional[int]:
    return int(value) if isinstance(value, int) else None


def _render_context_block(snapshot: dict[str, Any]) -> str:
    context_type = str(snapshot.get("contextType") or "unknown")
    file_path = str(snapshot.get("filePath") or "")
    class_name = str(snapshot.get("className") or "")
    line_start = _to_int(snapshot.get("lineStart"))
    line_end = _to_int(snapshot.get("lineEnd"))
    revision = int(snapshot.get("revision")) if isinstance(snapshot.get("revision"), int) else 0
    truncated = "true" if snapshot.get("truncated") is True else "false"
    text = str(snapshot.get("text") or "").rstrip()
    if not text:
        return ""

    range_text = ""
    if line_start and line_end:
        range_text = f"L{line_start}-L{line_end}"

    class_line = f"class: {class_name}\n" if class_name else ""

    return (
        "[IDE Context]\n"
        f"type: {context_type}\n"
        f"file: {file_path}\n"
        f"range: {range_text}\n"
        f"revision: {revision}\n"
        f"truncated: {truncated}\n"
        f"{class_line}"
        "content:\n"
        f"{text}\n"
        "[/IDE Context]"
    )


def _resolve_cwd(payload: dict[str, Any]) -> Path:
    candidates = [
        payload.get("cwd"),
        payload.get("project_dir"),
        payload.get("workspace"),
        os.environ.get("CLAUDE_PROJECT_DIR"),
        os.getcwd(),
    ]
    for value in candidates:
        if isinstance(value, str) and value.strip():
            return Path(value).expanduser()
    return Path.cwd()


def _build_output(context_block: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context_block,
        }
    }


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            payload = {}
    except Exception:
        payload = {}

    try:
        cwd = _resolve_cwd(payload)
        locks = _discover_locks()
        lock = _choose_lock(cwd, locks)
        context_block = ""

        if lock is not None:
            try:
                context_block = _render_context_block(_fetch_context(lock))
            except Exception:
                context_block = ""

        # Fallback path: Claude session cwd may be outside workspace
        # (e.g. ~/.claude/ide). Try all active IDE bridges and pick the
        # richest context snapshot, preferring explicit selections.
        if not context_block:
            fallback_snapshot = _select_best_snapshot(locks)
            if fallback_snapshot is not None:
                context_block = _render_context_block(fallback_snapshot)

        if not context_block:
            print("{}")
            return 0

        print(json.dumps(_build_output(context_block), ensure_ascii=False))
        return 0
    except urllib.error.URLError:
        print("{}")
        return 0
    except Exception:
        print("{}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
