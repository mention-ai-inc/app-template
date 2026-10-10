# Services image

This directory is a backend language slot. `main` holds only this README; the language branch adds
the `Dockerfile` (and its sibling `Dockerfile.dockerignore`) that builds the image for one service
under `services/`.

The contract the cloud branches build and deploy against, without knowing the language:

- build-arg `SERVICE` names the directory under `services/` to build;
- build-arg `FEATURE_ENVIRONMENT` is baked in as the environment variable of the same name;
- the image puts `run-server-rest`, `run-pool-<name>`, `run-job-<name>` and `run-worker-<name>` on
  `PATH` for every component the service declares, and the deploy target supplies the command;
- the image installs every provider under `control-plane/providers/*`, so the cloud is selected by
  what is installed.

The recipe under `infrastructure/docker/provider/services/` only names this `Dockerfile`, and the
build context is the repository root, so `Dockerfile.dockerignore` next to it decides what the
context contains.
