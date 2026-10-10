# Add a service: the Python backend

Sections 1 to 3 of `docs/add-service.md`, for a backend written in Python. The section numbers
match that file.

## 1. The package

Create `services/<name>/` with `pyproject.toml`, `README.md`, `<name>_service/`, and `tests/`.

- `pyproject.toml`: project name `<name>-service`, dependencies on `control-plane` and `library`
  through the path sources, the dev group and pytest settings from `services/notes/pyproject.toml`,
  and a `[project.scripts]` entry for every server, pool, and job: `run-server-rest`,
  `run-pool-<name>`, `run-job-<name>`, `run-worker-<name>`. A service has exactly three pool
  scripts — `run-pool-executors`, `run-pool-listeners`, `run-pool-triggers` — and the trigger one
  points at `library.presentation.service.triggers.pool:main`, which every service runs unchanged.
- `<name>_service/presentation/pools/` holds `executors.py` and `listeners.py`, each mapping the name
  Terraform routes to onto the handler that serves it. The listener pool includes the shared
  `acknowledge_command_result` listener from `library.presentation.service.listeners.acknowledge`;
  every service runs it.
- `README.md` must exist: `pyproject.toml` names it as the readme, so the environment and the image
  build fail without it.
- The package is `<name>_service`, laid out as `domain/`, `application/`, `infrastructure/`,
  `presentation/`. The `build-feature` skill and its `LANGUAGE.md` fill these in.
- `tests/` mirrors the package, with `conftest.py` (which sets `SERVICE` to the directory name)
  and `stubs/`. Follow `python-service-tests`.
- Every REST route declares an explicit `summary` and `tags`; `m compile-api` refuses a route
  without them.

`m init` loops over `services/*/pyproject.toml`, creates the virtual environment, installs every
cloud provider under `control-plane/providers/*` into it, and writes `uv.lock`.
`infrastructure/docker/services/Dockerfile` builds with `--frozen`, so commit the lock.
`m create-venv-<name>` recreates the environment on its own; `m test-service-<name>` runs the suite
with `SERVICE` set from the directory name.

## 2. The shared kernel

| File | What |
| --- | --- |
| `library/library/domain/value_objects/<name>.py` | ID value objects other services or surfaces will reference. |
| `library/library/domain/events/<name>.py` | Event payloads the service publishes, subclassing `EventPayload`. |
| `library/library/domain/commands/<name>.py` | Command payloads the service executes, subclassing `CommandPayload`, each with `SERVICE: ClassVar[Service]` set to the new member of the `Service` enum in `control-plane`. |

The `Service` enum itself and `SERVICE_BUCKETS` are in `control-plane`, as `docs/add-service.md`
section 2 says. Run `m update-local-dependencies` after any `control-plane` or `library` change
before testing the service (`library-dependency-sync`).

## 3. Repository tooling

| File | What |
| --- | --- |
| `infrastructure/cli/language/pyright.json` | Add an execution environment for `services/<name>` with its `.venv` site-packages on `extraPaths`, copied from the `services/notes` entry. `m init` and the check scripts merge it into the git-ignored `/pyrightconfig.json`. |

Nothing else enumerates services: `infrastructure/cli/language/helpers/packages.sh` discovers them
from `services/*/pyproject.toml`, and the OpenAPI generator, the test runner, the environment
scripts and `service-components` all go through it.
