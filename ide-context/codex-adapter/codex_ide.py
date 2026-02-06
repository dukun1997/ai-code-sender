#!/usr/bin/env python3
"""Codex adapter for IDE context injection.

MVP behavior:
- start: launch interactive `codex` with one injected bootstrap prompt.
- exec: launch `codex exec` with injected prompt.
- prompt: print injected prompt only.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def _injector_script() -> Path:
    return Path(__file__).resolve().parents[1] / "opencode-cli" / "opencode_ide_context.py"


def _inject_prompt(cwd: Path, prompt: str, format_name: str) -> str:
    injector = _injector_script()
    command = [
        sys.executable,
        str(injector),
        "inject",
        "--cwd",
        str(cwd),
        "--format",
        format_name,
        "--prompt",
        prompt,
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode == 0:
        output = result.stdout.strip()
        if output:
            return output
    return prompt


def _read_prompt(args: argparse.Namespace) -> str:
    if args.stdin:
        return sys.stdin.read()
    return args.prompt


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Codex IDE context adapter")
    sub = parser.add_subparsers(dest="cmd", required=True)
    default_format = os.environ.get("CODEX_IDE_CONTEXT_FORMAT", "compact").strip().lower()
    if default_format not in {"compact", "full"}:
        default_format = "compact"

    prompt_parser = sub.add_parser("prompt", help="print injected prompt")
    prompt_parser.add_argument("--cwd", default=os.getcwd(), help="workspace cwd")
    prompt_parser.add_argument("--prompt", default="", help="user prompt")
    prompt_parser.add_argument("--stdin", action="store_true", help="read prompt from stdin")
    prompt_parser.add_argument(
        "--format",
        choices=["compact", "full"],
        default=default_format,
        help="context injection format",
    )

    exec_parser = sub.add_parser("exec", help="run codex exec with injected prompt")
    exec_parser.add_argument("--cwd", default=os.getcwd(), help="workspace cwd")
    exec_parser.add_argument("--prompt", default="", help="user prompt")
    exec_parser.add_argument("--stdin", action="store_true", help="read prompt from stdin")
    exec_parser.add_argument(
        "--format",
        choices=["compact", "full"],
        default=default_format,
        help="context injection format",
    )
    exec_parser.add_argument("--dry-run", action="store_true", help="print final command")
    exec_parser.add_argument("codex_args", nargs="*", help="extra args passed to codex exec")

    start_parser = sub.add_parser("start", help="start codex interactive with injected bootstrap prompt")
    start_parser.add_argument("--cwd", default=os.getcwd(), help="workspace cwd")
    start_parser.add_argument("--prompt", default="", help="optional initial user prompt")
    start_parser.add_argument("--stdin", action="store_true", help="read prompt from stdin")
    start_parser.add_argument(
        "--format",
        choices=["compact", "full"],
        default=default_format,
        help="context injection format",
    )
    start_parser.add_argument("--dry-run", action="store_true", help="print final command")
    start_parser.add_argument("codex_args", nargs="*", help="extra args passed to codex")

    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    cwd = Path(args.cwd).resolve()
    prompt = _read_prompt(args)
    injected = _inject_prompt(cwd, prompt, args.format)

    if args.cmd == "prompt":
        print(injected)
        return 0

    if args.cmd == "exec":
        command = ["codex", "exec", injected, *args.codex_args]
        if args.dry_run:
            print(" ".join(command))
            return 0
        return subprocess.call(command)

    if args.cmd == "start":
        command = ["codex", injected, *args.codex_args]
        if args.dry_run:
            print(" ".join(command))
            return 0
        return subprocess.call(command)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
