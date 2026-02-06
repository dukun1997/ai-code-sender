# Claude Code IDE Context Plugin

This plugin injects JetBrains IDE context into Claude Code on every user prompt submission.

## Mechanism

1. Claude triggers `UserPromptSubmit` hook when you press Enter.
1. Hook script reads lock files from `~/.opencode/ide` (or `OPENCODE_IDE_LOCK_DIR`).
1. Hook fetches `GET /context/current` from the local IDE bridge.
1. Hook returns `additionalContext` with an `[IDE Context]` block.

## Files

- Plugin manifest: `./.claude-plugin/plugin.json`
- Hook config: `./hooks/hooks.json`
- Hook handler: `./hooks/user-prompt-submit.py`

## Enable (session-level, no global install)

```bash
cd /Users/dukun/code/tool/ai-code-sender
claude --plugin-dir /Users/dukun/code/tool/ai-code-sender/ide-context/claude-plugin
```

You can combine this with your normal arguments (`--model`, `--continue`, etc.).

## Validate plugin manifest

```bash
claude plugin validate /Users/dukun/code/tool/ai-code-sender/ide-context/claude-plugin/.claude-plugin/plugin.json
```

## Hook-only local test (without launching Claude UI)

```bash
echo '{"hook_event_name":"UserPromptSubmit","cwd":"/Users/dukun/code/tool/ai-code-sender","user_prompt":"请检查当前类"}' \
  | OPENCODE_IDE_LOCK_DIR=/Users/dukun/code/tool/ai-code-sender/.tmp-locks \
    python3 /Users/dukun/code/tool/ai-code-sender/ide-context/claude-plugin/hooks/user-prompt-submit.py
```

Expected output contains:

- `hookSpecificOutput.hookEventName = UserPromptSubmit`
- `hookSpecificOutput.additionalContext` (the IDE context block)
