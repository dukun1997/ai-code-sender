---
name: jetbrains-plugin-release
description: Publish a built JetBrains plugin ZIP to a GitHub Release. Use this skill when the user asks to tag a version, create/update a GitHub release, and upload plugin artifacts.
---

# JetBrains Plugin Release

## Overview

Use this skill to publish an already-built JetBrains plugin ZIP to GitHub Releases in a repeatable way.

## When to Use

Use this skill when the user asks to:
- publish a JetBrains/IntelliJ plugin build artifact
- create or update a GitHub Release for a plugin version
- tag and release a plugin ZIP with minimal manual steps

Do not use this skill for building the plugin itself. Build first, then release.

## Workflow

1. Confirm inputs:
- repository (default from current git `origin`)
- version/tag (for example `0.1.2` or `v0.1.2`)
- plugin ZIP path

2. Run the release script:
```bash
skills/jetbrains-plugin-release/scripts/release_jetbrains_plugin.sh \
  --version 0.1.2 \
  --zip ide-context/jetbrains-plugin/build/distributions/opencode-ide-context-plugin-0.1.2.zip
```

3. If needed, pass explicit repo/title/notes:
```bash
skills/jetbrains-plugin-release/scripts/release_jetbrains_plugin.sh \
  --version v0.1.2 \
  --zip ide-context/jetbrains-plugin/build/distributions/opencode-ide-context-plugin-0.1.2.zip \
  --repo dukun1997/ai-code-sender \
  --title "v0.1.2" \
  --notes-file /tmp/release-notes.md
```

## Behavior

The script will:
- normalize tag to `v*`
- check required tools (`git`, `gh`)
- create local tag if missing
- push tag to `origin` if missing remotely
- create release if missing
- upload ZIP to the release (replace existing asset with same name)

## Fallback

If `gh` is unavailable or unauthenticated, use the manual browser flow in:
`references/manual-release-ui.md`
