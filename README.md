# ai-code-sender

一个用于把 JetBrains IDEA 上下文（选区/当前类）注入到 CLI AI 编程工具的实验项目。

## 当前实现

- OpenCode：支持每条消息自动注入 IDE 上下文
- Claude Code：支持每次提交 prompt 自动注入 IDE 上下文
- Codex：支持 `exec` 每次注入，交互模式仅首条 bootstrap 注入

## 主要文档

- English: `ide-context/README.md`
- 中文: `ide-context/README.zh-CN.md`
- 架构图: `ide-context/ARCHITECTURE.md`
- 能力对照: `ide-context/TOOL_CAPABILITIES.md`

## 快速入口

```bash
cd /Users/dukun/code/tool/ai-code-sender

# OpenCode
opencode

# Claude
claude --plugin-dir /Users/dukun/code/tool/ai-code-sender/ide-context/claude-plugin

# Codex (bootstrap)
/Users/dukun/code/tool/ai-code-sender/ide-context/bin/codex-ide --prompt "先看当前选区"
```
