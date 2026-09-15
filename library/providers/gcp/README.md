# library-provider-gcp

The Google Cloud data plane behind the ports in `library/library/application/ports/`: Firestore as
the document store and transaction, Pub/Sub as the event bus, Cloud Tasks as the task queue, Cloud
Storage as the blob store, Secret Manager, and IAM-backed identity.

Installing this distribution is what selects GCP — it registers `gcp` in the `acme.cloud_provider`
entry-point group, and `library.providers.registry` picks it up. Nothing in `library` imports it.

The admin control plane (`library/library/infrastructure/cloud/run.py`, `logging.py`, `compute.py`)
stays in `library` for now; see "Admin is deferred" in `docs/ports-and-adapters.md`. This
distribution depends on `library`, never the other way round.

Run its suite with `m test-provider-gcp`.
