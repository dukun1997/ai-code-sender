# OpenCode IDE 上下文桥接（MVP）

这个目录提供了一套端到端 MVP：把 JetBrains IDE 中的选区/类上下文注入到 CLI AI 编程工具的提示词里。

- 架构图：`./ARCHITECTURE.md`
- 工具能力对照：`./TOOL_CAPABILITIES.md`

## 快速开始

把脚本目录加入 `PATH`：

```bash
export PATH="/Users/dukun/code/tool/ai-code-sender/ide-context/bin:$PATH"
```

然后可直接使用：

```bash
claude-ide
codex-ide --prompt "先看当前类"
opencode-ide
```

## 已实现功能

1. JetBrains 插件（`jetbrains-plugin/`）
2. 追踪编辑器选区变化
3. 无选区时回退为“当前类”或“光标窗口”
4. 提供本地 API：`GET /context/current`（需要鉴权头）
5. 写入 lock 文件：`~/.opencode/ide/<port>.lock`
6. 通用注入器（`opencode-cli/opencode_ide_context.py`）
7. 按 `cwd` 匹配 workspace，拉取 IDE 上下文
8. 支持 `compact/full` 两种注入格式
9. OpenCode 自动注入插件（`opencode-plugin/ide-context-plugin.mjs`）
10. Claude Code 自动注入插件（`claude-plugin/`）
11. Codex 适配器（`codex-adapter/`）

## OpenCode 自动注入

在项目根目录配置 `opencode.json`：

```json
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": ["/Users/dukun/code/tool/ai-code-sender/ide-context/opencode-plugin/ide-context-plugin.mjs"]
}
```

然后在项目目录启动：

```bash
cd /Users/dukun/code/tool/ai-code-sender
opencode
```

说明：

1. OpenCode 会在每条用户消息发送前自动注入 IDE 上下文。
2. 默认是紧凑格式（例如 `@path/to/File.java#L12-L20`）。
3. 详细块格式可用环境变量切换：

```bash
OPENCODE_IDE_CONTEXT_FORMAT=full opencode
```

## Claude Code 自动注入

使用本地插件目录启动：

```bash
cd /Users/dukun/code/tool/ai-code-sender
claude --plugin-dir /Users/dukun/code/tool/ai-code-sender/ide-context/claude-plugin
```

说明：

1. 通过 `UserPromptSubmit` Hook 在每次提交 prompt 时注入。
2. 当前默认注入为完整 `[IDE Context]` 块格式。

## Codex 适配器（当前边界）

执行型（每次调用都注入）：

```bash
python3 /Users/dukun/code/tool/ai-code-sender/ide-context/codex-adapter/codex_ide.py exec \
  --cwd /Users/dukun/code/tool/ai-code-sender \
  --format compact \
  --prompt "请重构当前类"
```

交互型（仅首条 bootstrap 注入）：

```bash
python3 /Users/dukun/code/tool/ai-code-sender/ide-context/codex-adapter/codex_ide.py start \
  --cwd /Users/dukun/code/tool/ai-code-sender \
  --format compact \
  --prompt "先看当前选区"
```

说明：

1. `codex exec` 能保证每次请求都拿到最新 IDE 上下文。
2. `codex` 交互模式当前仅首条注入，这是现阶段 CLI 能力边界。

## 本地验证（无需安装 IDE 插件）

先启动 mock bridge：

```bash
cd /Users/dukun/code/tool/ai-code-sender
./ide-context/opencode-cli/mock_ide_server.py --workspace /Users/dukun/code/tool/ai-code-sender
```

另开一个终端查看上下文：

```bash
./ide-context/opencode-cli/opencode_ide_context.py show --cwd /Users/dukun/code/tool/ai-code-sender
```

测试注入结果：

```bash
./ide-context/opencode-cli/opencode_ide_context.py inject \
  --cwd /Users/dukun/code/tool/ai-code-sender \
  --format compact \
  --prompt "Refactor this service"
```

## 集成说明

1. IDE 插件仅监听 `127.0.0.1`。
2. 请求必须带 `X-OpenCode-Ide-Authorization`。
3. lock 目录默认 `~/.opencode/ide`，可通过 `OPENCODE_IDE_LOCK_DIR` 覆盖。
