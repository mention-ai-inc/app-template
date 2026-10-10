---
paths:
  - "admin/**/*.py"
  - "services/**/*.py"
---

## Request-scoped logging

Use the request-scoped log context in use cases and services to attach structured fields to the per-request log envelope. Context is flushed once per HTTP/executor request (nested under `context`) or per job execution.

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
- **Raw payloads / PII**: `response_text`, `raw_text`, full `summary`, a whole serialized context object — use the LLM telemetry spans for LLM content
- **Constants** that never vary (e.g. `max_pairs_budget=500`)
- **Weak proxies**: `summary_length`, `body_length`
- **Redundant happy-path flags** when absence of `early_return_reason` already implies success

### Loops

The context is a flat map — a key added twice keeps the **last** value only. Never add `organization_id` or another per-item key to the context inside a loop. Accumulate counts and log once after the loop.

For per-item failures in batch jobs, log the exception for that item instead of mutating shared context per item.

### LLM observability

Prompts, responses, and retries go to the LLM telemetry span the kernel provides — not into the log context.
