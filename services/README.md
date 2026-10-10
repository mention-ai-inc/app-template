# Services

This directory is a backend language slot. On `main` it holds only this file; the language branch
adds one directory per service, `notes` being the sample that ships with the template.

Whatever the language, a service is one deployable unit with its own tests, its own dependency
manifest and lockfile, and the components the cloud branches deploy without reading its code:

| Component | Executable on `PATH` in the services image | Deploy target |
| --- | --- | --- |
| REST server | `run-server-rest` | `m deploy-<service>-server-rest` |
| Pool | `run-pool-<name>` | `m deploy-<service>-pool-<name>` |
| Job | `run-job-<name>` | `m deploy-<service>-job-<name>` |
| Worker | `run-worker-<name>` | `m deploy-<service>-worker-<name>` |

`infrastructure/docker/services/Dockerfile` (also from the language branch) builds that image from
build-arg `SERVICE`, and `infrastructure/cli/language/service-components` lists the components each
service declares. Services talk to each other only through commands and events over the outbox; see
`.agents/rules/service-communication.md`.

`docs/add-service.md` lists every place a new service is registered and `docs/remove-sample.md`
retires `notes`.
