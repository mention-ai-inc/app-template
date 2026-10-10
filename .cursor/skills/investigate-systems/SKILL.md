---
name: investigate-systems
description: Investigate feature or production data, API logs, Azure service logs, and LLM traces using the configured Cosmos DB, Log Analytics, KQL, and Logfire tooling. Use for debugging incidents, retries, request failures, or stored application state.
---

# Investigate systems

## Safety and environment

- Default to feature-environment tools unless the user explicitly asks about production.
- Treat production writes as live changes. Do not write or mutate production data without explicit approval.
- Confirm the time range, environment, organization or entity identifiers, and observed symptom before broad queries.

## Choose the source

| Need | Source |
| --- | --- |
| Stored application state | the Cosmos DB database: `<environment>acme` for a feature environment, `acme` for production, one container per service |
| Structured API request logs and usage | the event archive in Blob Storage, through the `<environment>event-archive` and `<environment>audit-archive` containers |
| Container Apps, ingress, and platform logs | Log Analytics, queried with KQL against the environment's workspace |
| LLM calls, retries, validation failures, and traces | Logfire MCP |

Do not use the blob event archive for LLM diagnosis; use Logfire traces.

## Data conventions

- Production resources have no environment prefix; every feature environment prefixes its own.
- One Cosmos DB account holds every environment's database, and one container per service holds every
  collection of that service. What Firestore would express as a collection id, Cosmos expresses as the
  `documentType` field: `<environment><service>_<collection>`. The item id is
  `<documentType>:<document id>`, the entity's own identity is kept beside it in `entityId`, and a
  subcollection is `<collection id>|<document id>|<subentity name>` in the same `documentType` field.
- `partitionKey` is a field, not a path. It is the partition the store was connected to, the
  document's `organization_id`, or the document id — which is what lets an aggregate and the command
  it dispatched land in one transactional batch.
- A query that does not filter on `partitionKey` is cross-partition and charges request units across
  every partition. Bound one before anything else, exactly as you would bound a time range.
- LLM spans are named `llm.{service}.{operation}`. Correlate with `llm.trace_id`, OpenTelemetry trace
  IDs, organization IDs, and request logs.
- A Container App is a **pool**, not a single entrypoint: `<environment><service>-p-<pool>` serves
  every executor, listener, or trigger routed to it. Filtering on the app narrows to the pool, never
  to one handler. To follow a single executor, listener, or trigger, filter on the `component_name`
  field of the custom log entry, or on the request path — `/commands/{command}`, `/events/{listener}`,
  `/triggers/{trigger}`.
- Names longer than the Container Apps 32-character limit are truncated and suffixed with a
  seven-character digest by `modules/container-app-name`, so derive an app name from
  `az containerapp list --query "[].name"` rather than assuming the full one.
- A message that exhausted `max_delivery_count` is in that queue's or subscription's **dead-letter
  sub-queue**, not lost. Peeking it is how you see what the handler choked on.

## Investigation workflow

1. Narrow by environment and time.
2. Find the request, entity, or trace using the highest-signal identifier available.
3. Follow linked logs, child spans, retries, exceptions, and validation events.
4. For validator retries, search adjacent messages for `There was a problem with the result:` and inspect Pydantic errors for schema failures.
5. Summarize evidence and uncertainty. Avoid returning full prompts, raw PII, or large payloads when counts or short excerpts are enough.

If Log Analytics or Cosmos DB access is missing or broken, read [azure-access.md](references/azure-access.md).
