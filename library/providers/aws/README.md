# library-provider-aws

The Amazon Web Services data plane behind the ports in `library/library/application/ports/`:
DynamoDB as the document store and transaction, SNS as the event bus, SQS as the task queue, S3 as
the blob store, Secrets Manager, KMS-backed identity, DynamoDB Streams as the document change feed,
and an SQS long-polling pool driver.

Installing this distribution is what selects AWS — it registers `aws` in the `acme.cloud_provider`
entry-point group, and `library.providers.registry` picks it up. Nothing in `library` imports it.

Run its suite with `m test-provider-aws`. It needs no AWS credentials: the tests stand up a
[moto](https://github.com/getmoto/moto) server and point the adapters at it with `AWS_ENDPOINT_URL`.

`tests/test_conformance_suite.py` runs the shared behavioural suite in
`library/tests/application/ports/conformance/` against these adapters. It imports the suite's test
classes and its `tests/conftest.py` re-exports the suite's fixtures, overriding only
`provider_under_test` so the entry in `tests/aws_under_test.py` is the one under test. That is a
detour: `PROVIDERS_UNDER_TEST` lives in a file `main` owns, and a cloud branch may not edit it, so
the registry cannot yet accept a provider from a branch. `tests/` deliberately has no `__init__.py`
and the manifest sets `pythonpath = ["../.."]`, which is what lets `tests.application.ports...`
resolve to the suite in `library/tests/` rather than to this directory.

## How the document store is laid out

One DynamoDB table holds every collection.

| | |
| --- | --- |
| `pk` | `<feature environment><service>_<collection>#<document id>` |
| `sk` | `root` for the document, `sub#<subentity name>#<subdocument id>` for a subentity |
| `_collection` | the collection id, on root items only — the hash key of the `collection-index` GSI |
| `_document_id` | the document id — the range key of that GSI |
| `_version` | an integer bumped on every write; the optimistic-concurrency token |
| `_subcollection_metadata` | subdocument ids per subentity name, as on the other providers |

A document and its subentities share one partition key, so reading a document deeply is one `Query`
and writing it is one transaction. Collection-wide reads (`query`, `count`, `query_ids`) go through
the sparse `collection-index` GSI, which only root items enter.

A unit of work buffers its writes and commits them with one `TransactWriteItems`. Every document
read inside the block is pinned: a write to that document carries `ConditionExpression
_version = <the version that was read>`, and a document that was only read gets a `ConditionCheck`.
DynamoDB cancels the transaction if any condition fails, and the adapter turns that into
`ApplicationError(TRANSACTION_CONFLICT)`.

## Configuration

| Variable | Meaning |
| --- | --- |
| `AWS_REGION` | Region for every client. |
| `AWS_ACCOUNT_ID` | Deployment id; looked up with STS when absent. |
| `AWS_ENDPOINT_URL` | Points every client at a local emulator. Presigning ignores it. |
| `DYNAMODB_TABLE_NAME` | The one document table. |
| `EVENT_TOPIC_ARNS_JSON` | Topic name to topic ARN, for the event bus. |
| `SQS_EXECUTOR_QUEUES_JSON` | `"<service>:<command>"` to queue URL. |
| `SQS_LISTENER_QUEUES_JSON` | `"<service>:<listener>"` to the list of queue URLs. |
| `SQS_TRIGGER_QUEUES_JSON` | `"<service>:<trigger>"` to queue URL. |
| `EXECUTOR_POOLS_JSON` | `"<service>:<command>"` to pool name, for `ITaskQueue.get_url`. |
| `CONTAINER_CONCURRENCY` | Messages a pool handles at once. |
| `HANDLER_TIMEOUT` | Seconds a pool gives one handler. |
| `S3_PRESIGN_ENDPOINT_URL` | Overrides the endpoint presigned URLs point at. |

## The pool driver

Every other cloud pushes work at a pool over HTTP. SQS cannot push, so `AwsProvider.pool_driver()`
returns an `SqsPoolDriver` that replays the push that never arrived: it long-polls the queues named
for the routes the pool serves, and dispatches each message into the same FastAPI app in process,
over `httpx.ASGITransport`, at the path the cloud would have called.

- A command message is an envelope from `SqsTaskQueue.add_task`, so the driver unwraps it and
  restores the body, query parameters, and headers the executor route expects.
- A listener message is the SNS notification, posted through unchanged for `SnsMessageParser`.
- A trigger message is an EventBridge Pipes batch of DynamoDB stream records, so the driver posts
  each record separately and keeps the message until every one of them is accepted.

A message is deleted only after the route answers 2xx; anything else leaves it for redrive to the
dead-letter queue the Terraform provisions. `SIGTERM` stops the pollers so ECS can drain a task, and
`CONTAINER_CONCURRENCY` bounds how many messages are in flight.

## Where AWS cannot keep the port's promise

- **Collection queries read the whole collection.** DynamoDB has no ad-hoc query planner, so
  filters, sorting, and cursors are applied in the adapter after the GSI hands back the collection.
  Everything correct, nothing pushed down; a collection that outgrows a page of results wants its
  own GSI.
- **Collection queries are eventually consistent.** A GSI cannot be read consistently, so `query`,
  `count`, `query_ids`, and `query_one` may not see a write that has just committed. `get`,
  `get_many`, and `exists` read the base table consistently and always do.
- **A unit of work may touch at most 100 documents.** That is the `TransactWriteItems` limit,
  counting condition checks on documents that were only read.
- **`ArrayUnion` and `ArrayRemove` cost a read.** DynamoDB cannot deduplicate a list server side, so
  the adapter reads the document, computes the new list, and writes it back under a version
  condition. `Increment` and plain assignments are native `ADD` and `SET` and cost nothing extra.
- **Scheduled tasks reach 15 minutes.** `DelaySeconds` caps there, and the adapter clamps to it.
  Anything further out wants EventBridge Scheduler rather than a delayed message.
- **`ITaskQueue.get_url` names a pool that does not listen.** An ECS pool has no inbound address at
  all — it polls. The URL identifies the pool and the command, and is the path the driver replays.
- **`IIdentity.id_token` is a KMS-signed JWT.** AWS has no equivalent of GCP's minted ID token; a
  caller that wants AWS-native authentication wants SigV4.
- **Secret versions are stages.** Secrets Manager has no integer version sequence: `latest` maps to
  `AWSCURRENT`, a UUID maps to `VersionId`, and anything else is treated as a version stage label.
- **`get_saved_at` is recorded by the adapter.** S3's `LastModified` only has whole-second
  resolution, so `insert` stamps `x-amz-meta-saved-at` and `get_saved_at` prefers it, falling back
  to `LastModified` for objects written by a presigned upload.
