---
name: build-feature
description: Turn a PRD or feature request into working code, layer by layer - domain model and domain interfaces first with the developer confirming each, then application use cases and queries, then infrastructure and presentation autonomously, then the web, mobile, or MCP surface. Use when starting a new feature, a new aggregate, or a new service from product requirements.
---

# Build a feature from requirements

If `LANGUAGE.md` exists beside this file, read it first: it maps every layer below to the installed backend language's paths, base classes, test conventions, and language rules.

The order is fixed: domain, domain interfaces, application, infrastructure and presentation, surfaces. Each layer is finished, tested, and checked before the next starts. There are two mandatory pauses for human input: after the domain model and after the domain interfaces. Everything after them follows from contracts the developer has already confirmed, so proceed without checking in unless a real ambiguity appears.

## What a gate shows

At each pause, put everything needed to judge the work in the chat itself: the relevant code for every new or changed file in that layer, followed by the decisions it encodes and the alternatives you rejected. A review the developer cannot do from the chat alone is not a review.

Relevant code means every field with its type, every method signature, and every method body that enforces a rule or emits an event or command. Leave out imports, module boilerplate, and docstrings. Never stand in for a detail with `...`, a placeholder, or prose describing what the code does; if something is shown, show it as written. For a changed file, show the changed definitions, not the untouched ones around them.

When review feedback states a pattern that applies beyond the line it was raised on, apply it everywhere in the change, then record it as a rule in `.agents/rules/` scoped in `.agents/rules.json`, or extend the rule that already covers it, before continuing.

## 1. Read the requirements

- Read the PRD under `docs/product/prds/` and `docs/product/glossary.md`. Use glossary names for every object, field, and event (`glossary`). A concept the glossary lacks is added there, with the PRD corrected, before it is modelled.
- Read the PRDs it depends on. Their "Objects and contracts" sections say which aggregates and fields already exist or are promised.
- Read the smallest existing service end to end once. In the untouched scaffold that is `services/notes`, the reference implementation of every layer.
- Decide whether the feature lives in an existing service or needs a new one. A service owns the aggregates whose invariants the feature changes. A new service is warranted when the feature owns aggregates no existing service touches and has its own pools, document collections, and deploy target. Creating one follows `docs/add-service.md`.
- Trace every request path the feature adds and list the data each one reads. If any of it is owned by another service, resolve it per `service-communication` (command and reply, a local projection, or moving the capability) now, before modelling. A synchronous call between services is never the answer.
- For every external system the feature relies on as a record or a capability (the identity provider, a billing provider, a third-party API, a model provider), read its current documentation now, not when building infrastructure. Write down what it already enforces, what its API can and cannot do, and what it reports back (webhooks, response shapes). A rule the external system enforces is not modelled again; the aggregate records the outcome it reports. A capability the API lacks changes the feature (a link instead of an action, a webhook instead of a call), and is settled with the developer here.

Write the restatement back to the developer as a short list of **terms**, **rules**, and **reactions** (when X happens, Y follows), and for each external system, what it owns and what is left to the service. That list is what the domain layer encodes; disagreement is cheapest here.

## 2. Domain model, then stop and confirm

Write only the service's domain layer and the shared kernel pieces it needs, plus their tests.

- One module per aggregate, with its value objects beside it. Follow `aggregate-state-vs-status`, `no-schema-defaults`, and `id-field-names`.
- Draw each aggregate around the rules that must hold atomically; every other consequence travels as an event or command (`unit-of-work-scope`). If a rule needs two aggregates to change together, they are one aggregate.
- Cross-service identifiers, events, and commands live in the shared kernel under `library/`, in its domain value objects, events, and commands. Follow `library-dependency-sync`. An event only one service consumes stays in that service.
- Repository interfaces in the domain layer. External capability interfaces as domain interfaces beside them.
- Invariants raise a domain error with a `public_message` in the user-facing words from `docs/product/glossary.md`. Side effects are events and commands added on the aggregate, never calls out. Emit nothing for a failure or a no-op, and nothing only as history.
- A reaction that loops over many aggregates is a command the aggregate adds, run by an executor, not a listener (`unit-of-work-scope`).
- Logic that spans several aggregates and holds no state is a domain service; data another service owns that this one reads is a projection, rebuilt from that service's events.
- Domain tests per aggregate assert state, events, and commands.

Then present the model to the developer and ask before continuing. Cover, in this order:

1. The aggregates and their boundaries. Why each is one aggregate rather than two, and what is an entity or value object inside it.
2. Each lifecycle. The status values, which method moves between them, and what is refused.
3. The events and commands each transition emits, and who is expected to consume them.
4. Every PRD requirement or edge case that the model does not obviously cover, with a proposed answer.
5. Open questions the PRD deferred that the model had to decide.

Ask specific questions with a recommendation each. Do not ask the developer to review the code; ask whether the model matches their intent. Revise until they confirm. Record decisions that changed the PRD's meaning back into the PRD.

## 3. Domain interfaces, then stop and confirm

Everything the feature needs from outside the domain is an interface stated in domain terms, with no mention of how it is implemented:

- **Repositories** extend the kernel's repository interface. Add a custom finder only for a lookup a use case actually performs.
- **Capabilities** are domain interfaces for LLM judgements, external systems, and stores. Name the capability by what it decides or provides, take and return domain types, and keep return types as small as the caller needs.

An interface with no caller yet is not written.

Before the pause, check every interface backed by an external system against that system's documentation, and cite the source: each method maps to an endpoint, webhook, or link that exists. An interface you could not verify does not pass; verify it, or bring the gap to the developer as a decision.

Then show every interface and the types it takes and returns, and for each capability, say what decides it (a model, an external system, a store) and what the caller does with each possible return. Revise until the developer confirms.

## 4. Application layer

Write the feature's application layer and its tests. No human checkpoint unless a use case needs a contract the domain model did not settle.

- One use case per entry point, named after its verb, constructor taking interfaces only. Follow `application-layer-dependencies` and `read-after-write`.
- Units of work hold one aggregate, briefly (`unit-of-work-scope`): model calls and external calls happen outside the block, and the block re-reads the aggregate before applying their result.
- Every use case reached from an event or command is idempotent; delivery is at least once.
- Read models as DTOs and a query service interface beside them, shaped by `read-models`: only what a screen or tool acts on. Queries never load aggregates.
- Extract an application service only when two use cases need the same logic.
- Cross-service work is a command through `ICommandDispatcher` or an event through `IEventPublisher`, never a call to another service. Follow `service-communication`.
- Log through the request-scoped log context as the `logging` rule describes.
- One test module per use case, using the service's own stubs and the kernel's fakes. Cover each outcome branch, and run any loop over aggregates with at least two.
- Run `m run-code-formatting`, then `m run-checks-backend`.

## 5. Infrastructure and presentation

Proceed autonomously. Everything here implements an interface that already exists.

Start with the adapters to external systems, because they are where an assumption about another system is most likely to be wrong. When one is, stop and correct the inner layers and the PRD before writing the rest of the layer.

- Persistence adapters implementing each repository. Query services implementing each query interface. A query that needs a declared index ships with it (`query-indexes`).
- External services as infrastructure services, each with a client and its response models. LLM-backed ones return domain value objects, not primitives. These wrap third parties only; never build a client for another of our services (`service-communication`).
- Dependency wiring: one factory per repository, query service, and infrastructure service, and one per use case.
- Entry points, each delegating to exactly one use case: REST routes, listeners, executors, jobs.
- Register every new listener, executor, and trigger in its pool module, keyed by the name Terraform routes to it: a command's `executor_name`, a listener's `terraform.tfvars` key, a trigger's name. Only servers, pools, and jobs get a command, named by the image contract: `run-server-rest`, `run-pool-<name>`, `run-job-<name>`, `run-worker-<name>`.
- Declare every new executor in `terraform.tfvars` with the `pool` it belongs to — that entry is its own command queue — and every new listener with its subscriptions.
- Route tests per router. Infrastructure service tests where behavior beyond pass-through exists.
- Run `m run-code-formatting`, `m run-checks-backend`, then `m compile-api` when routes changed.

## 6. Surfaces

Build only the surfaces the PRD names as in scope. Each has its own skill and conventions.

Design each screen before writing it. The PRD's User experience prose explains behavior; it is not copy. Put on screen the strings the PRD quotes and the labels each control needs, show the primary object itself, and show status as a badge or icon rather than a sentence. Render only what the DTO carries (`read-models`).

- Web: follow `web-frontend`. Hooks come from `packages/acme-api-client`, generated by `m compile-api`.
- Mobile: follow `mobile-frontend`.
- MCP: add tools under `apps/mcp/src/tools/` with tests beside them, calling the REST client in `apps/mcp/src/client.ts`.
- Run `m run-code-formatting`, then `m run-checks-frontend`.

## 7. Finish

- Walk the PRD's acceptance criteria and say which are met, which need a feature environment to confirm, and which were consciously left out.
- Run `m run-checks` before handing over. The type checker must report zero errors on every package you touched; fix every error it reports, including ones you did not introduce. None is ever left as pre-existing.
- End with the deployment plan the `deployment-plan` rule requires, derived from the diff. A new executor's queue, a new listener's subscription, a new pool, and a new index are Terraform; the routes themselves ship with the service.
