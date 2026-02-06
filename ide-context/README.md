# OpenCode IDE Context Bridge (MVP)

This folder contains an end-to-end MVP to inject JetBrains IDE context into CLI prompts.

Architecture diagram: `./ARCHITECTURE.md`
Tool capability matrix: `./TOOL_CAPABILITIES.md`
Chinese README: `./README.zh-CN.md`

## Quick start scripts

Add scripts to `PATH`:

```bash
export PATH="/Users/dukun/code/tool/ai-code-sender/ide-context/bin:$PATH"
```

Then use:

```bash
claude-ide
codex-ide --prompt "先看当前类"
opencode-ide
```

## What is implemented

1. JetBrains plugin skeleton (`jetbrains-plugin/`)
1. Tracks editor selection changes
1. Fallback to current class when selection is empty
1. Exposes local API: `GET /context/current` (auth header required)
1. Writes lock file: `~/.opencode/ide/<port>.lock`
1. OpenCode-side CLI injector (`opencode-cli/opencode_ide_context.py`)
1. Discovers lock files and matches by `cwd`
1. Fetches context from bridge API
1. Supports compact/default and full/verbose injection formats
1. OpenCode auto-injection plugin (`opencode-plugin/ide-context-plugin.mjs`)
1. Hooks `chat.message` and prepends IDE context automatically per message
1. Claude Code auto-injection plugin (`claude-plugin/`)
1. Hooks `UserPromptSubmit` and injects IDE context via `additionalContext`
1. Codex adapter (`codex-adapter/`)
1. Supports `codex exec` injection and interactive bootstrap injection

## Quick local demo (without installing the plugin)

1. Start mock bridge server:

```bash
cd /Users/dukun/code/tool/ai-code-sender
./ide-context/opencode-cli/mock_ide_server.py --workspace /Users/dukun/code/tool/ai-code-sender
```

1. In another terminal, show context:

```bash
./ide-context/opencode-cli/opencode_ide_context.py show --cwd /Users/dukun/code/tool/ai-code-sender
```

1. Inject context into a prompt:

```bash
./ide-context/opencode-cli/opencode_ide_context.py inject --cwd /Users/dukun/code/tool/ai-code-sender --prompt "Refactor this service"
```

## Plugin integration notes

- The plugin serves only on `127.0.0.1`.
- Requests must include header `X-OpenCode-Ide-Authorization`.
- Lock directory defaults to `~/.opencode/ide`; override with `OPENCODE_IDE_LOCK_DIR`.

## OpenCode TUI auto injection

Enable plugin in your project `opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": ["./ide-context/opencode-plugin/ide-context-plugin.mjs"]
}
```

Then run OpenCode normally:

```bash
cd /Users/dukun/code/tool/ai-code-sender
opencode
```

Each submitted user message will include injected IDE reference text (compact by default).

## Claude Code auto injection

Run Claude with the local plugin directory:

```bash
cd /Users/dukun/code/tool/ai-code-sender
claude --plugin-dir /Users/dukun/code/tool/ai-code-sender/ide-context/claude-plugin
```

Each submitted user message will trigger `UserPromptSubmit` and inject `[IDE Context]`.

## Codex adapter (MVP)

Run Codex with injected prompt:

```bash
python3 /Users/dukun/code/tool/ai-code-sender/ide-context/codex-adapter/codex_ide.py exec \
  --cwd /Users/dukun/code/tool/ai-code-sender \
  --format compact \
  --prompt "请重构当前类"
```

Interactive bootstrap:

```bash
python3 /Users/dukun/code/tool/ai-code-sender/ide-context/codex-adapter/codex_ide.py start \
  --cwd /Users/dukun/code/tool/ai-code-sender \
  --format compact \
  --prompt "先看当前选区"
```

Note: Codex currently lacks a public per-message prompt hook, so interactive mode is first-message bootstrap only in this MVP.
