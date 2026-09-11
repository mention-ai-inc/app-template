---
name: review
description: Review branch changes against main for correctness, regressions, repository rules, shortcuts, and missing tests or docs. Use for code review, pre-PR review, or branch-versus-main review requests.
---

# Review branch changes

## Scope

Default to committed, staged, and unstaged branch changes versus `main`:

```bash
git fetch origin main 2>/dev/null || true
git diff main...HEAD --stat
git diff main...HEAD
git diff
git diff --cached
```

Use `origin/main` if local `main` is unavailable. Honor a narrower scope when the user names a PR, branch, commit, or working-tree-only review. If the resolved diff is empty, say so and stop.

## Review process

1. Identify changed areas from the diff stat.
2. Read each changed file with enough surrounding context to understand behavior.
3. Read applicable project rule files for the changed paths.
4. Read only the relevant sections of [STANDARDS.md](STANDARDS.md).
5. Compare with neighboring implementations when checking local patterns.
6. Report actionable findings only; do not fix them unless asked.

Prioritize correctness and production risk, then hard rule violations, missing tests, and finally meaningful pattern drift. Do not report pre-existing issues in untouched code unless the change makes them worse.

For diffs over 30 files or 2,000 lines, review the highest-risk application, presentation, domain, and infrastructure paths first and state what was not fully reviewed.

## Findings

Order findings by severity:

- **Must fix:** likely bug, security or data risk, broken contract, or hard rule violation.
- **Should fix:** meaningful maintainability risk, missing test for risky behavior, or established-pattern violation.
- **Nit:** small consistency issue worth changing; omit low-value style preferences.

Each finding must include a file and line, the observed problem, its impact, and the applicable rule or local pattern. Lead with findings. If there are none, say so clearly and note any test gap or residual risk.

End with a brief summary and relevant verification that remains to be run.
