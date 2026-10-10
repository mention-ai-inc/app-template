# Control plane

The language-neutral Python kernel that `admin`, the cloud provider distributions, and every
product backend share. It owns the ports (`application/ports/`), the domain primitives and value
objects every stored document is built from, the audit model and its publisher, the FastAPI
scaffolding under `presentation/api/`, the provider registry, the `local` provider, the Clerk
client, the cache, and logging.

## Scope

`control-plane/` holds what must behave identically regardless of which language a product's
services are written in:

- **Ports** — the protocols a cloud provider implements. `application/ports/provider.py` imports
  every port, so all of them live here.
- **Domain primitives** — `domain/entities.py`, `domain/value_objects/{core,common,users}.py`,
  the audit model under `domain/audit/`, and the command and event envelopes' shared base
  (`domain/events/base.py`).
- **Operational infrastructure** — unit of work, Sentry, the Redis cache, the users client, the
  audit publisher and snapshot context.
- **API scaffolding** — `presentation/api/` builds the FastAPI applications, pools and runners that
  services and `admin` serve from, and `presentation/auth/impersonation.py` mints
  service-to-service tokens.
- **Providers** — `providers/registry.py` resolves the installed cloud provider; `providers/local/`
  is the in-memory provider the test suites run against. Cloud providers are distributions of
  their own under `control-plane/providers/<cloud>/`, added by the cloud branches.

Product concerns — aggregates, repositories, the outbox, the LLM slice, service listeners — belong
in the language kernel (`library/` for Python), never here. If a module would need to import the
kernel, it is not control plane.

## Stored document shapes

`tests/fixtures/documents/` holds the golden shapes of every document the platform stores or
transmits — commands, events, audit events, the sample `Note`, task bodies and headers, and
outbound messages — with fixed ids and timestamps. Every language kernel must emit them
byte-for-byte after key sort; the Python kernel's suite asserts that it does.

## Tests

`m test-control-plane` runs this distribution's suite, including the provider conformance suite
under `tests/application/ports/conformance/`, which every cloud provider must also pass.
