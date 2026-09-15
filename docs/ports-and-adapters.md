# Ports and adapters

`docs/cloud-providers.md` splits the repository into a cloud-agnostic `main` and one branch per
cloud, and names the one rule that keeps them mergeable: a cloud branch adds files, it never edits a
file `main` also has. The deploy-time slots already obey it. The application code does not.

`library/library/infrastructure/` used to import Firestore, Pub/Sub, and Cloud Tasks from generic
classes that every cloud needs — `repository.py`, `unit_of_work.py`, `outbox.py`, the trigger
modules. Those files are on `main`. A second cloud would have to edit them, which the one rule
forbids. This document is the plan for moving the provider out from under them.

Nothing here is Terraform. This work lands entirely on `main` (except its last step) and merges
outward, and it is the prerequisite for `cloud/aws` and `cloud/azure` being anything but a checklist.

**Status: done.** The ports exist, four providers satisfy them — `local` on `main`, and one on each
cloud branch — the generic classes resolve through a registry rather than naming a cloud, each
provider is a distribution of its own under `library/providers/`, and one behavioural suite holds
them all to the same contract. Stage 6 moved every provider off `main` onto the branch that deploys
it, so `main` now resolves `local` with nothing installed and no configuration.

What is left is the one deferral below: `admin` is still GCP-only. `docs/cloud-providers.md` is the
reference for the result; this document records how it was arrived at and why.

## 1. What is coupled

Roughly 3,450 lines. What matters is not the volume but which of three groups a file is in.

| Group | Files | Lines | What to do |
| --- | --- | --- | --- |
| Adapters already | `infrastructure/cloud/*.py`, `persistence/firestore.py`, `persistence/firestorage.py` | ~1,630 | Move to a provider package, satisfy a port. No redesign. |
| Generic code importing concretes | `repository.py`, `outbox.py`, `unit_of_work.py`, `audit/publisher.py`, `persistence/storage.py`, `application/events.py`, `application/triggers.py`, `presentation/service/triggers/*`, `presentation/api/commands.py`, `presentation/auth/{direct,impersonation}.py` | ~1,400 | Invert. This is the work. |
| Admin control plane | `admin/client/api.py`, `admin/common/environment.py`, `admin/server/{auth,dependencies,jobs}.py`, `admin/server/routers/runs.py` | ~420 | Deferred. See section 7. |

Three subsystems that look cloud-coupled and are not, and so are out of scope entirely:

- **Redis** (`infrastructure/persistence/cache/`) speaks the Redis wire protocol. Memorystore,
  ElastiCache, and Azure Cache for Redis are interchangeable behind it.
- **Clerk** (`infrastructure/users.py`) is a third-party identity provider, not a cloud service.
- **The LLM layer** (`infrastructure/llm/`) goes through pydantic-ai, which already fronts Vertex,
  Bedrock, and Azure OpenAI.

One asset worth naming before starting: `library/library/_testutils/` already holds
`InMemoryRepository`, `FakeUnitOfWork`, and fake dispatcher, publisher, and cache implementations,
each with its own tests under `library/tests/_testutils/`. A second adapter set already exists, and
it already reproduces the read-before-write lease semantics that `read-after-write.md` enforces. It
becomes the `local` provider in section 5.

## 2. The decisions

These four were settled before any port was written, because each one changes signatures rather than
implementations.

### Transactions are optimistic, not leased

A read returns a version token; a commit is conditional on it. The port does not promise Firestore's
transaction semantics.

Today `unit_of_work()` opens a Firestore transaction holding a read lease and writes the aggregate,
its events, its audit events, and its commands atomically. Note the partition keys: aggregates,
events, and audit records partition by `OrganizationID`, but `CommandDispatcher` partitions by
`CommandID`, so a single unit of work already spans partitions. Firestore allows that and DynamoDB
allows it (`TransactWriteItems`, up to 100 items, across tables). Cosmos DB NoSQL does not: a
transactional batch is one container and one partition key, and it has no read lease at all —
concurrency there is ETag-based.

Optimistic concurrency is the contract all four stores can honour:

| Store | How it satisfies the port |
| --- | --- |
| Firestore | Native transaction |
| DynamoDB | `TransactWriteItems` with condition expressions |
| Cosmos DB NoSQL | ETag plus transactional batch |
| PostgreSQL | Native |

It also preserves the read-before-write discipline the codebase already enforces, so
`read-after-write.md` stays true as written and `FakeTransactionState` keeps catching the same bug.

The cost is one schema change on GCP: repartition the `commands` collection by `OrganizationID` so a
unit of work stays within one partition. That is free in a template and a data migration in a live
system — anyone who has already deployed from `cloud/gcp` needs to know that before merging.

### Subcollections stay in the port

`persistence/firestore.py` models nested entities hierarchically: `get_subentity_names()`,
`_subcollection_metadata`, `mode="deep"`, a collection ref per subentity. The port keeps that.

The domain genuinely has nested entities, so flattening would not remove the complexity, only move it
into each adapter and into every aggregate that has subentities. Keeping it means the document-store
port is the widest one in the system and each non-Firestore adapter maps subcollections onto
composite sort keys, with the deep read becoming a query:

| Store | Subentity layout |
| --- | --- |
| Firestore | Native collection references |
| DynamoDB | `PK = document`, `SK = sub#<name>#<id>` |
| Cosmos DB | Same partition key, type discriminator |

The rejected alternative — one document per aggregate — would have inherited per-document size
limits (400KB on DynamoDB, 2MB on Cosmos) and made every subentity write a full parent rewrite.

### The change feed is pumped, not pushed

On GCP the outbox drains through Eventarc, which pushes a CloudEvent over HTTP into the trigger pool.
That shape does not exist on the other two clouds: DynamoDB Streams invokes Lambda, and the Cosmos
change feed is a host-bound pull processor.

Rather than let each cloud drain the outbox its own way, the adapter runs a change-feed pump inside
the existing trigger pool container and calls the same handlers:

```
trigger pool container
  GCP    HTTP push          -> publish_event / submit_command / publish_audit_event
  AWS    pump(streams)      -> the same handlers
  Azure  pump(change feed)  -> the same handlers
```

One component shape across every cloud, comparable Terraform, and
`library/library/presentation/service/triggers/` stays as it is. The cost is a long-running consumer
process on AWS and Azure where a serverless push would have been cheaper.

### Admin is deferred

`CloudRun`, `CloudLogging`, `Compute`, and the project-number IAP verification in
`admin/admin/server/auth.py` stay GCP for now. They are the control plane, not the request path, and
porting them is a separable job with its own ports (`IJobRunner`, `ILogReader`, instance lookup).

The consequence is explicit: **`admin/` runs on GCP only until that work is done.** A cloud branch
that is not `cloud/gcp` has no working admin control plane, and its `deploy-admin` target has nothing
to deploy. Section 7 carries the follow-up.

## 3. The ports

They live under `library/library/application/ports/`. `IAsyncCache`, `IUsersClient`, and
`IUnitOfWork` moved in alongside them so the layer has one convention rather than two, and
`ICloudProvider` in `ports/provider.py` is the factory surface that ties the rest together.
Domain ports stay where they are: `IRepository` in
`domain/repositories.py` and `ICommandDispatcher` / `IEventPublisher` in `domain/outbox.py` are
already provider-neutral and do not change.

| Port | Replaces | Notes |
| --- | --- | --- |
| `IDocumentStore` | `Firestore` | The widest. `ArrayUnion`, `ArrayRemove`, and `Increment` become neutral field mutations. The `in` filter's 30-item validator is a Firestore limit currently leaking into `QueryFilter`. |
| `ITransaction` and the unit-of-work factory | `UOW = NewType(firestore.AsyncTransaction)` | Optimistic, per section 2. The `Aborted` / `ServiceUnavailable` / `DeadlineExceeded` mapping to `TRANSACTION_CONFLICT` moves into the adapter; the contract that contention raises `ApplicationError(TRANSACTION_CONFLICT)` stays on `main`. |
| `IEventBus` | `Pubsub` | Publish side, plus the inbound push envelope in `application/events.py`. |
| `ITaskQueue` | `Tasks` | Queue naming splits: the conventions stay on `main`, the resolution to a queue path moves to the adapter. |
| `IDocumentChangeFeed` | `FirestoreDocument` in `application/triggers.py` | Parses the after-image out of whatever the provider delivers, and hosts the pump. |
| `IBlobStore` | `Storage` | `ServiceBucket` in `persistence/storage.py` is already close to the port. Presigned URLs go through `IIdentity`. |
| `ISecretStore` | `SecretManager` | Small and uncontroversial. |
| `IIdentity` | `AuthenticatedClient`, `IAM` | Access token for an audience, sign a JWT, resolve a service's identity. Feeds `presentation/auth/impersonation.py` and blob presigning. |
| `IRuntimeContext` | `get_project_id()`, `REGION`, `PROJECT_NUMBERS_BY_ID`, `scope_resource_name` | Unblocks `presentation/auth/direct.py`, whose `JWK_DOMAINS_BY_PROJECT` is keyed by GCP project id. |

Two renames fall out of this and touch files outside `library/`:

- The neutral types `DocumentID`, `QueryFilter`, `SortBy`, `QueryResult`, `FieldUpdate`, and
  `Primitive` move out of `persistence/firestore.py` into the port module. That changes imports in
  `services/notes/notes_service/infrastructure/persistence/notes.py` and
  `.../infrastructure/queries/notes.py`, and the corresponding section of `docs/add-service.md`.
- `EventPayload.pubsub_event_name()` in `library/library/domain/events/base.py` becomes
  `event_name()`. A domain method should not be named after one cloud's message broker.

`infrastructure/cloud/constants.py` splits. `COMMAND_PATH_PREFIX`, `EVENT_PATH_PREFIX`,
`TRIGGER_PATH_PREFIX`, `DEAD_LETTER_PATH_SUFFIX`, `APP_DOMAIN`, and `DOMAIN` are application
conventions and stay on `main`. The project ids, project numbers, region, and bucket name go behind
`IRuntimeContext`.

## 4. How a provider is selected

`library` must never import a provider, and `library/pyproject.toml` lives on `main` where a cloud
branch cannot edit it to add an SDK dependency. Three mechanisms together satisfy both:

**Discovery by entry point.** A provider registers itself:

```toml
[project.entry-points."acme.cloud_provider"]
gcp = "library_provider_gcp.registry:PROVIDER"
```

`library` resolves it with `importlib.metadata.entry_points(group="acme.cloud_provider")`. Selection
is therefore driven by what is installed, with no environment variable to forget; `CLOUD_PROVIDER`
exists only to disambiguate when more than one provider is present, and to assert the expected one at
startup.

**The provider is its own distribution**, at `library/providers/<cloud>/`, depending on `library` plus
that cloud's SDKs, with its own lock file. The dependency runs provider to library, which is the
direction ports and adapters requires, and it keeps the SDKs out of `library/pyproject.toml`.

**Installation hooks on `main`.** `m create-venv-%` and `infrastructure/docker/*/Dockerfile` gain a
loop over `library/providers/*/pyproject.toml`. Both files stay on `main`; both are no-ops when only
`local` is present. `m update-local-dependencies` copies provider packages into dependent virtual
environments the same way it copies `library`.

## 5. The `local` provider

`main` ships a provider of its own. It is **not** the fakes in `library/library/_testutils/`
promoted: `InMemoryRepository` and `FakeUnitOfWork` implement `IRepository` and `IUnitOfWork`, the
seam a service test stubs, which is a layer above the provider seam and could never have satisfied
`IDocumentStore`. The fakes stay where they are and keep doing their job. The `local` provider is a
separate in-memory implementation one level down, and both are wanted.

It lives at `library/library/providers/local/` until stage 4 promotes it to a distribution of its
own at `library/providers/local/`.

This is what keeps the ports honest. Without it, `main` has ports that nothing implements and no way
to tell whether they are implementable; with it, `main` is runnable rather than merely testable, the
conformance suite in section 6 has a reference implementation, and every future port change is
proved against two adapters before it is merged.

`library/tests/providers/local/` covers it directly, and
`library/tests/application/ports/test_conformance.py` holds both adapter sets to the same protocols
at type-check time.

## 6. Sequence

Stages 1 to 5 happen entirely on `main` and merge outward cleanly, because `cloud/gcp` owns none of
these files.

**1. Neutral vocabulary. Done.** Move the shared types out of `persistence/firestore.py`, rename
`pubsub_event_name()`, split `cloud/constants.py`, update the service imports and
`docs/add-service.md`. Still GCP throughout, no behaviour change. Gate: `m run-checks` and
`m run-tests-backend`.

**2. Declare the ports, implement nothing. Done.** Write the protocols and make the existing GCP classes
structurally satisfy them. Gate: pyright proves conformance with no runtime change at all — if a GCP
class cannot satisfy a port, the port is wrong and this is the cheapest possible place to find out.

**3. Invert the generic classes. Done.** `Repository`, `CommandDispatcher`, `EventPublisher`,
`AuditEventPublisher`, `unit_of_work()`, `ServiceBucket`, `MessageParser`, the three trigger modules,
`publish_command_result`, and both auth modules stop importing concretes and resolve through the
registry. Promote `_testutils` to the `local` provider. Gate: the whole backend suite green against
`local`, with the GCP path still green. This is the bulk of the work.

**4. Package split. Done.** GCP adapters move to `library/providers/gcp/`, the Google SDKs come out of
`library/pyproject.toml`, and the virtual-environment and Docker hooks land. Gate: `m run-checks` and
`m run-tests-backend` green with the GCP provider installed.

**5. Conformance suite.** One parametrised suite that every provider must pass. `local` passes it on
`main`. Running it against a real `gcp` needs an emulator, which the repository does not have today
(section 7), so that is its own piece of CI work on the cloud branch. A new cloud is done when it
passes this suite, which is the only definition of done a provider branch gets.

**6. The git move.** The same deletion-in-shared-ancestry ordering that `docs/cloud-providers.md`
describes:

```
commit A   stages 1-5, library/providers/gcp/ present and green
commit B   delete library/providers/gcp/
           git switch cloud/gcp && git merge main        # the deletion lands here
           git checkout A -- library/providers/gcp && git commit
```

The deletion is then in shared ancestry, so every later `git merge main` stays clean. Add the slot to
the table in `docs/cloud-providers.md` and delete its "What is not yet split" section.

The pyright `executionEnvironments` entry for the provider root goes on `main` and is harmless while
the directory is absent, exactly as the `infrastructure/cli/provider/helpers` entry already is.

## 7. What stages 1 to 3 changed about this plan

**`FieldUpdate` was a union over Firestore's own sentinels.** Any caller typing
`dict[str, FieldUpdate]` therefore depended on the SDK. Nothing outside the two adapter files ever
constructed one, so replacing them with neutral mutation types cost no call site anything.

**GCP reached into the domain layer.** `PresignedURL` refused any URL not containing
`storage.googleapis.com`. It now checks what a domain object can know — that the value is an
absolute https URL — and the host belongs to whichever adapter signed it.

**`FireStorage.query` returned no entities.** Certifying it against `IDocumentStore` surfaced a bug:
it built its result list only when asked to load blobs, so `Repository.get_all` — its only caller —
got accurate counts and an empty list. Nothing in the template sets `use_storage=True`, so the path
had never run.

**The `commands` repartition is not a type annotation.** Only aggregate stores call
`connect_to_partition`; events, commands, and audit records go to flat collections. Changing the
declared partition key moves no data. Doing it properly changes collection layout, which the GCP
branch's Eventarc triggers are keyed on, so it belongs with the Cosmos adapter.

**There is no emulator.** Nothing in the repository runs one, and CI runs only `m init` and
`m run-checks`. Stage 5 cannot check GCP against an emulator without first introducing one, which is
CI work on a cloud branch.

## 8. Risks and follow-ups

**Private Firestore APIs.** `_commit_once` in `unit_of_work.py` drives `client._firestore_api`,
`_write_pbs`, `_database_string`, and `_rpc_metadata` directly. It works, but nothing about it
generalises, and it limits what the commit port can promise. Read it before designing `ITransaction`.

**Stale virtual environments.** `.agents/rules/library-dependency-sync.md` exists because this trap
recurs, and stage 4 made it worse by adding a second local distribution. Every symptom looks like a
real result. `m update-local-dependencies` now refreshes each `library/providers/*` package into every
dependent environment, and refreshes `library` inside each provider's own environment as well.

**The commands repartition.** Section 2 changes the partition key of the `commands` collection.
Harmless in a fresh template, a migration anywhere it has already been deployed. Not yet done, and
section 7 says why.

**Admin.** Section 2 defers it, and stages 1 to 3 left it alone. Until it is done, `admin/` is GCP-only and a non-GCP cloud branch has
no control plane. The ports it needs are `IJobRunner` (`CloudRun`), `ILogReader` (`CloudLogging`),
and an instance lookup (`Compute`), plus a replacement for the project-number IAP verification in
`admin/admin/server/auth.py`.
