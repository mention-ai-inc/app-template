## Request-scoped logging in Python

`add_log_context(**fields)` from `control_plane.logs` is the request-scoped log context. It merges fields with `dict.update`, which is why a key set twice keeps the last value only; never call it with `organization_id=...` or another per-item key inside a loop.

Per-item failures in batch jobs use `logger.exception(...)` instead of mutating the shared context.

Never pass `context.model_dump()` or another serialized payload to it. LLM prompts, responses, and retries go through Logfire via `llm_span` in `library/library/infrastructure/llm/telemetry.py`.
