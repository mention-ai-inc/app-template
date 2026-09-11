---
name: agent-parity
description: Audit and repair parity across the repository's Codex, Claude, and Cursor rules and skills. Use when AGENTS.md, CLAUDE.md, .agents, .claude, or .cursor agent guidance changes, or for scheduled maintenance after changes merge to main.
---

# Maintain agent parity

## Source model

- `AGENTS.md` is the shared always-on instruction source.
- `CLAUDE.md` must contain only `@AGENTS.md`.
- `.agents/rules/` and `.agents/rules.json` are canonical rule bodies and path scopes.
- `.agents/skills/` is the canonical skill tree.
- `.claude/rules`, `.claude/skills`, `.cursor/rules`, and `.cursor/skills` are generated native mirrors.

Do not create a `.codex/rules` tree: Codex uses `AGENTS.md` and `.agents/skills`. The `.agents/rules` directory is a portable canonical source that `AGENTS.md` explicitly directs Codex to read.

## Scheduled maintenance workflow

1. Start from the latest `main` and inspect recent changes to `AGENTS.md`, `CLAUDE.md`, `.agents/`, `.claude/`, and `.cursor/`.
2. Run `m check-agent-parity`.
3. If it passes and recent changes do not introduce contradictory, duplicated, stale, or overly broad guidance, stop without changing files or opening a PR.
4. If a generated mirror changed directly, preserve the contributor's intent by applying the equivalent concise change to the canonical `.agents` source.
5. Keep rules focused and path-scoped where possible. Put multi-step or task-specific workflows in skills. Remove duplicated guidance instead of copying it into another always-loaded file.
6. Keep each skill's `name` and `description` concise and portable. Use supporting files only for detail that should load on demand.
7. Run `m sync-agent-parity`, inspect the generated diff, then run `m check-agent-parity`.
8. If changes remain, create one focused branch and PR explaining the drift repaired. Do not modify product code.

Never erase a newly merged instruction merely because it originated in a generated mirror. Reconcile intent first, then restore the canonical structure.
