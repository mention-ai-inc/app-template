---
name: investigate-systems
description: Investigate feature or production data, API logs, GCP service logs, and LLM traces using the configured Firestore, BigQuery, Cloud Logging, and Logfire MCP servers. Use for debugging incidents, retries, request failures, or stored application state.
---

# Investigate systems

## Safety and environment

- Default to feature-environment tools unless the user explicitly asks about production.
- Treat production writes as live changes. Do not write or mutate production data without explicit approval.
- Confirm the time range, environment, organization or entity identifiers, and observed symptom before broad queries.

## Choose the source

| Need | Source |
| --- | --- |
| Stored application state | `firestore-feature` or `firestore-production` |
| Structured API request logs and usage | `bigquery-feature` or `bigquery-production`, dataset `api_logs` |
| Cloud Run, GCE, and platform logs | `cloud-logging-feature` or `cloud-logging-production` |
| LLM calls, retries, validation failures, and traces | Logfire MCP |

Do not use BigQuery LLM invocation exports for LLM diagnosis; use Logfire traces.

## Data conventions

- Production collections and datasets have no environment prefix.
- Feature collections include the environment and service: `[environment][service]_[table_name]`.
- Feature BigQuery datasets use the environment prefix, for example `demoapi_logs`.
- LLM spans are named `llm.{service}.{operation}`. Correlate with `llm.trace_id`, OpenTelemetry trace IDs, organization IDs, and request logs.

## Investigation workflow

1. Narrow by environment and time.
2. Find the request, entity, or trace using the highest-signal identifier available.
3. Follow linked logs, child spans, retries, exceptions, and validation events.
4. For validator retries, search adjacent messages for `There was a problem with the result:` and inspect Pydantic errors for schema failures.
5. Summarize evidence and uncertainty. Avoid returning full prompts, raw PII, or large payloads when counts or short excerpts are enough.

If Cloud Logging authentication is missing or broken, read [cloud-logging-auth.md](references/cloud-logging-auth.md).
