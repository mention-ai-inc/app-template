---
paths:
  - "admin/**/*.py"
  - "services/**/*.py"
---

## Request-scoped logging (`add_log_context`)

Use `add_log_context` in use cases and services to attach structured fields to the per-request log envelope. Context is flushed once per HTTP/executor request (nested under `context`) or per Cloud Run job.

### Always log (high signal)

| Key | When |
| --- | --- |
| `early_return_reason` | Guard clauses / skipped work (`already_summarized`, `note_purged`, …) |
| `outcome` | Terminal state when branches matter (`content_changed`, `content_unchanged`, `completed`, …) |
| `operation` | Optional short snake_case label when one handler runs multiple paths |
| Entity IDs | **Once** at handler entry: `note_id`, `command_id` |
| Aggregate metrics | **Once** at end: `num_*` counts, batch totals — not per-iteration |

### Do not log in `context`

- **`organization_id`** on HTTP/executor paths (already top-level on API logs). Exception: Clerk/unsigned webhooks and job summaries.
- **Secrets / credentials**: `authorization_url`, presigned `content_url`, `token_nonce`
- **Raw payloads / PII**: `response_text`, `raw_text`, full `summary`, `context.model_dump()` — use Logfire `llm.*` spans for LLM content
- **Constants** that never vary (e.g. `max_pairs_budget=500`)
- **Weak proxies**: `summary_length`, `body_length`
- **Redundant happy-path flags** when absence of `early_return_reason` already implies success

### Loops

`add_log_context` uses `dict.update` — duplicate keys keep the **last** value only. Never call `add_log_context(organization_id=...)` inside a loop. Accumulate counts and log once after the loop.

For per-item failures in batch jobs, use `logger.exception(...)` instead of mutating shared context per item.

### LLM observability

Use Logfire (`llm_span` in `library/infrastructure/llm/telemetry.py`) for prompts, responses, and retries — not `add_log_context`.
