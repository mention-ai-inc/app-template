---
name: investigate-systems
description: Investigate feature or production data, API logs, AWS service logs, and LLM traces using the configured DynamoDB, Athena, CloudWatch Logs, and Logfire tooling. Use for debugging incidents, retries, request failures, or stored application state.
---

# Investigate systems

## Safety and environment

- Default to feature-environment tools unless the user explicitly asks about production.
- Treat production writes as live changes. Do not write or mutate production data without explicit approval.
- Confirm the time range, environment, organization or entity identifiers, and observed symptom before broad queries.

## Choose the source

| Need | Source |
| --- | --- |
| Stored application state | the DynamoDB document table: `<environment>acme` for a feature environment, `acme` for production |
| Structured API request logs and usage | Athena over the event archive in S3, through the `event-export` and `audit-export` Glue databases |
| ECS, load balancer, and platform logs | CloudWatch Logs, log group `/ecs/<environment><service>-<kind>-<name>` |
| LLM calls, retries, validation failures, and traces | Logfire MCP |

Do not use the S3 event archive for LLM diagnosis; use Logfire traces.

## Data conventions

- Production resources have no environment prefix; every feature environment prefixes its own.
- One DynamoDB table holds every collection. A root item's partition key is
  `<environment><service>_<collection>#<document id>` with sort key `root`; subentities share the
  partition key with sort key `sub#<name>#<id>`. The `_collection` attribute carries the collection id
  and is the hash key of the collection index, which is the only way to read a collection whole.
- Athena tables in the `event-export` and `audit-export` Glue databases are partitioned by delivery
  time, so always bound a query by partition before anything else.
- LLM spans are named `llm.{service}.{operation}`. Correlate with `llm.trace_id`, OpenTelemetry trace IDs, organization IDs, and request logs.
- An ECS service is a **pool**, not a single entrypoint: `<environment><service>-p-<pool>` serves every
  executor, listener, or trigger routed to it, and its log group is `/ecs/<that name>`. Filtering on the
  log group narrows to the pool, never to one handler. To follow a single executor, listener, or
  trigger, filter on the `component_name` field of the custom log entry, or on the request path —
  `/commands/{command}`, `/events/{listener}`, `/triggers/{trigger}`.
- Names longer than the AWS limit are truncated and suffixed with a seven-character digest by
  `modules/resource-name`, so derive a log group from `aws logs describe-log-groups --log-group-name-prefix`
  rather than assuming the full name.
- A message that exhausted its attempts is in that queue's `-dl` dead-letter queue, not lost. Reading it
  with `aws sqs receive-message` is how you see what the handler choked on.

## Investigation workflow

1. Narrow by environment and time.
2. Find the request, entity, or trace using the highest-signal identifier available.
3. Follow linked logs, child spans, retries, exceptions, and validation events.
4. For validator retries, search adjacent messages for `There was a problem with the result:` and inspect Pydantic errors for schema failures.
5. Summarize evidence and uncertainty. Avoid returning full prompts, raw PII, or large payloads when counts or short excerpts are enough.

If CloudWatch Logs or DynamoDB access is missing or broken, read [aws-access.md](references/aws-access.md).
