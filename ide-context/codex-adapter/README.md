# Codex IDE Context Adapter (MVP)

This adapter injects IDE context into Codex prompts.

## Current limitation

Codex CLI currently has no exposed per-message prompt hook comparable to:

- OpenCode: `chat.message`
- Claude Code: `UserPromptSubmit`

So this MVP supports:

1. `codex exec` prompt injection (full)
1. Interactive session bootstrap injection (first message only)
1. Compact injection by default (e.g. `@src/foo/Bar.java#L10-L22`)

## Commands

### Print injected prompt only

```bash
python3 /Users/dukun/code/tool/ai-code-sender/ide-context/codex-adapter/codex_ide.py prompt \
  --cwd /Users/dukun/code/tool/ai-code-sender \
  --prompt "请优化这段代码"
```

### Run `codex exec` with injection

```bash
python3 /Users/dukun/code/tool/ai-code-sender/ide-context/codex-adapter/codex_ide.py exec \
  --cwd /Users/dukun/code/tool/ai-code-sender \
  --prompt "请重构当前服务"
```

### Start interactive Codex with injected bootstrap prompt

```bash
python3 /Users/dukun/code/tool/ai-code-sender/ide-context/codex-adapter/codex_ide.py start \
  --cwd /Users/dukun/code/tool/ai-code-sender \
  --prompt "我们先看当前选区"
```

### Dry run (show command only)

```bash
python3 /Users/dukun/code/tool/ai-code-sender/ide-context/codex-adapter/codex_ide.py exec \
  --cwd /Users/dukun/code/tool/ai-code-sender \
  --prompt "test" \
  --dry-run
```

## Format override

Use verbose mode only when needed:

```bash
python3 /Users/dukun/code/tool/ai-code-sender/ide-context/codex-adapter/codex_ide.py exec \
  --cwd /Users/dukun/code/tool/ai-code-sender \
  --format full \
  --prompt "请重构当前服务"
```
