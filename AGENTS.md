## Skills
A skill is a set of local instructions to follow that is stored in a `SKILL.md` file.

### Available skills
- jetbrains-plugin-release: Publish a built JetBrains plugin ZIP to a GitHub Release. Use when the user asks to tag a version, create/update a GitHub release, and upload plugin artifacts. Project-local skill only. (file: skills/jetbrains-plugin-release/SKILL.md)
- skill-creator: Guide for creating effective skills. Use when users want to create a new skill (or update an existing skill) that extends Codex's capabilities with specialized knowledge, workflows, or tool integrations. (file: /Users/dukun/.codex/skills/.system/skill-creator/SKILL.md)
- skill-installer: Install Codex skills into `$CODEX_HOME/skills` from a curated list or a GitHub repo path. Use when a user asks to list installable skills, install a curated skill, or install a skill from another repo (including private repos). (file: /Users/dukun/.codex/skills/.system/skill-installer/SKILL.md)

### How to use skills
- Discovery: The list above is the skills available in this project context. Skill bodies live on disk at the listed paths.
- Trigger rules: If the user names a skill (with `$SkillName` or plain text) OR the task clearly matches a skill's description shown above, use that skill for that turn. Multiple mentions mean use them all. Do not carry skills across turns unless re-mentioned.
- Missing/blocked: If a named skill isn't in the list or the path can't be read, state it briefly and continue with the best fallback.
- Progressive disclosure:
  1) After deciding to use a skill, open its `SKILL.md`. Read only enough to follow the workflow.
  2) When `SKILL.md` references relative paths (for example `scripts/foo.py`), resolve them relative to the skill directory listed above first.
  3) If `SKILL.md` points to extra folders such as `references/`, load only the specific files needed for the request.
  4) If `scripts/` exist, prefer running or patching them instead of retyping large code blocks.
  5) If `assets/` or templates exist, reuse them instead of recreating from scratch.
- Coordination: If multiple skills apply, choose the minimal set that covers the request and state the order.
- Context hygiene: Keep context small, summarize long sections, and avoid deep reference chasing.
- Safety/fallback: If a skill cannot be applied cleanly (missing files, unclear instructions), state the issue, choose the next-best approach, and continue.
