# control-plane-provider-gcp

The Google Cloud data plane behind the ports in `control-plane/control_plane/application/ports/`:
Firestore as the document store and transaction, Pub/Sub as the event bus, Cloud Tasks as the task
queue, Cloud Storage as the blob store, Secret Manager, and IAM-backed identity.

Installing this distribution is what selects GCP — it registers `gcp` in the `acme.cloud_provider`
entry-point group, and `control_plane.providers.registry` picks it up. Nothing in `control-plane`
imports it.

The admin control plane's adapters live here too: `control_plane_provider_gcp/cloud/run.py`,
`logging.py`, and `compute.py` are the REST clients behind `IJobRunner`, `ILogReader`, and
`IOperatorAuth`. This distribution depends on `control-plane`, never the other way round, and the
product kernel in `library` never imports it.

Run its suite with `m test-provider-gcp`.
