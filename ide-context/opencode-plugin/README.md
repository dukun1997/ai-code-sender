# OpenCode Auto Injection Plugin

This plugin injects JetBrains IDE context into every OpenCode user message.

## What it does

1. Reads lock files from `~/.opencode/ide/*.lock` (or `OPENCODE_IDE_LOCK_DIR`)
1. Picks the lock matching current `cwd`
1. Calls `GET /context/current` with `X-OpenCode-Ide-Authorization`
1. Prepends compact IDE reference text to the outgoing prompt (`chat.message` hook), for example:
   - `@hm-server/src/main/java/.../Foo.java#L120-L128`

## Enable in project

Create or edit your project `opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": ["./ide-context/opencode-plugin/ide-context-plugin.mjs"]
}
```

If your config already has plugins, append this path to the existing array.

## Debug mode

Set `OPENCODE_IDE_DEBUG=1` to print injection failures in terminal.

## Format mode

Default is compact mode. To switch back to verbose block mode:

```bash
OPENCODE_IDE_CONTEXT_FORMAT=full opencode
```

## Local smoke test with mock bridge

Start mock bridge:

```bash
cd /Users/dukun/code/tool/ai-code-sender
./ide-context/opencode-cli/mock_ide_server.py --workspace /Users/dukun/code/tool/ai-code-sender
```

In another terminal, run hook-only smoke test:

```bash
cd /Users/dukun/code/tool/ai-code-sender
node ./ide-context/opencode-plugin/smoke_test.mjs /Users/dukun/code/tool/ai-code-sender "请解释这段代码"
```

Then run OpenCode in the same project and send a message:

```bash
cd /Users/dukun/code/tool/ai-code-sender
opencode run "请告诉我你收到的 IDE Context 是什么"
```

You should see the model can reference the injected `[IDE Context]` block.
