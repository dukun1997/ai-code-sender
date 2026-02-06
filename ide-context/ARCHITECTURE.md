# IDE Context Injection Architecture

```mermaid
flowchart LR
  A["IntelliJ Plugin<br/>selection/caret tracker"] --> B["In-memory snapshot"]
  B --> C["Local HTTP bridge<br/>127.0.0.1:<port>/context/current"]
  A --> D["Lock file<br/>~/.opencode/ide/<port>.lock<br/>token + workspace + url"]

  E["OpenCode TUI"] --> F["chat.message hook<br/>ide-context-plugin.mjs"]
  F --> D
  F --> C
  F --> G["Prompt with [IDE Context] block"]
  G --> E

  H["Claude Code TUI"] --> I["UserPromptSubmit hook<br/>user-prompt-submit.py"]
  I --> D
  I --> C
  I --> J["additionalContext with [IDE Context] block"]
  J --> H

  K["Codex CLI"] --> L["codex_ide.py adapter<br/>start/exec"]
  L --> D
  L --> C
  L --> M["Bootstrap/exec prompt with [IDE Context] block"]
  M --> K
```

## Runtime sequence

1. IDE plugin captures selection or current class fallback.
1. IDE plugin refreshes lock file with auth token and local endpoint.
1. OpenCode plugin intercepts each outgoing user message (`chat.message`) and prepends context.
1. Claude plugin intercepts each submitted prompt (`UserPromptSubmit`) and returns context as `additionalContext`.
1. Codex adapter injects context for `exec` and first interactive bootstrap prompt.
