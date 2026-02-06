# IDE 工具能力对照

本文档说明当前工作区里三种 CLI 工具的实际能力差异：

- `OpenCode`
- `Claude Code`
- `Codex`

## 一句话结论

1. `OpenCode`：每条消息都能自动注入 IDE 上下文。
2. `Claude Code`：每条提交也能自动注入（通过 `UserPromptSubmit`）。
3. `Codex`：交互模式没有稳定的每条消息 Hook，只能首条注入或 `exec` 单次注入。

## 当前行为

### OpenCode

- 状态：稳定
- 注入时机：每条用户消息（`chat.message`）
- 默认格式：紧凑模式
- 示例：`@hm-server/src/main/java/.../Foo.java#L120-L128`
- 配置文件：`/Users/dukun/code/tool/ai-code-sender/opencode.json`
- 实现位置：`/Users/dukun/code/tool/ai-code-sender/ide-context/opencode-plugin/ide-context-plugin.mjs`

### Claude Code

- 状态：稳定
- 注入时机：每次提交 prompt（`UserPromptSubmit`）
- 默认格式：完整块（`[IDE Context] ... [/IDE Context]`）
- 启动方式：`claude --plugin-dir /Users/dukun/code/tool/ai-code-sender/ide-context/claude-plugin`
- 实现位置：`/Users/dukun/code/tool/ai-code-sender/ide-context/claude-plugin/hooks/user-prompt-submit.py`

### Codex

- 状态：部分可用（受 CLI 能力边界限制）
- 注入时机：`codex exec` 每次都注入，交互 `codex` 仅首条 bootstrap 注入
- 默认格式：紧凑模式
- 启动方式：`/Users/dukun/code/tool/ai-code-sender/ide-context/bin/codex-ide`
- 实现位置：
  - `/Users/dukun/code/tool/ai-code-sender/ide-context/codex-adapter/codex_ide.py`
  - `/Users/dukun/code/tool/ai-code-sender/ide-context/opencode-cli/opencode_ide_context.py`

## 为什么 Codex 不同

`OpenCode` 和 `Claude` 都有消息级插件 Hook。当前 `Codex` CLI 没有等价的、稳定的“每轮发送前 Hook”，外部适配器拿不到每条消息发送时机，所以交互模式不能做到每轮自动刷新注入。

## 推荐用法

1. 需要“跟随选区实时变化”时优先用 `OpenCode`。
2. 需要 Claude 工作流并保持每轮注入时用 `Claude Code`。
3. `Codex` 场景优先用 `codex exec`，保证每次都是最新上下文。
