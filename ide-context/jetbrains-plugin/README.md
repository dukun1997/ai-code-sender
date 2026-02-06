# JetBrains Plugin Skeleton

This plugin skeleton provides IDE context for OpenCode.

## Features in this MVP

1. Tracks selection and caret movement
1. Context priority:
   - `selection`
   - `class_fallback`
   - `caret_window`
1. Serves context via local HTTP endpoint:
   - `GET /health`
   - `GET /context/current`
1. Uses token auth header:
   - `X-OpenCode-Ide-Authorization: <token>`
1. Writes lock file:
   - `~/.opencode/ide/<port>.lock`

## Build

This project is configured for IntelliJ Platform Gradle plugin.

```bash
cd /Users/dukun/code/tool/ai-code-sender/ide-context/jetbrains-plugin
./gradlew build
```

(Gradle wrapper is not included in this MVP skeleton. You can generate it with `gradle wrapper`.)
