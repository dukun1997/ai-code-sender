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
- version/tag (optional; default auto-infers latest semver and bumps patch)
- plugin ZIP path (optional; default auto-picks newest `.zip` in the fixed directory below)

2. Run the release script (defaults enabled):
```bash
skills/jetbrains-plugin-release/scripts/release_jetbrains_plugin.sh
```

3. If needed, pass explicit repo/version/zip/title/notes:
```bash
skills/jetbrains-plugin-release/scripts/release_jetbrains_plugin.sh \
  --version v0.1.2 \
  --zip /Users/dukun/code/tool/ai-code-sender/ide-context/jetbrains-plugin/build/distributions/opencode-ide-context-plugin-0.1.2.zip \
  --repo dukun1997/ai-code-sender \
  --title "v0.1.2" \
  --notes-file /tmp/release-notes.md
```

## Behavior

The script will:
- default ZIP lookup directory: `/Users/dukun/code/tool/ai-code-sender/ide-context/jetbrains-plugin/build/distributions`
- auto-select the newest `.zip` when `--zip` is omitted
- auto-infer next version (latest semver + patch) when `--version` is omitted
- normalize tag to `v*`
- check required tools (`git`, `gh`)
- create local tag if missing
- push tag to `origin` if missing remotely
- create release if missing
- upload ZIP to the release (replace existing asset with same name)

## Fallback

If `gh` is unavailable or unauthenticated, use the manual browser flow in:
`references/manual-release-ui.md`
