# library-provider-azure

The Microsoft Azure data plane behind the ports in `library/library/application/ports/`: Cosmos DB
for NoSQL as the document store and transaction, Service Bus as the event bus and task queue, Blob
Storage as the blob store, Key Vault for secrets and signing keys, and a pool driver that turns a
pull-based estate back into the push-based one the handlers expect.

Installing this distribution is what selects Azure — it registers `azure` in the
`acme.cloud_provider` entry-point group, and `library.providers.registry` picks it up. Nothing in
`library` imports it.

Run its suite with `m test-provider-azure`.

## How the Azure model differs from the Firestore one

**One container per service.** Firestore names a collection per service and partition; Cosmos DB
gets one container per service, named after the service, inside the database named by
`COSMOS_DATABASE`. What Firestore expresses as a collection id, Cosmos expresses as the
`documentType` field, so `{feature_environment}{service}_{collection}` becomes a discriminator
rather than a path. A subcollection is `{collection_id}|{document_id}|{subentity_name}` in the same
field, stored in the same logical partition as its parent.

Because a container is shared, the Cosmos item id has to carry the discriminator too:
`{documentType}:{documentId}`. The entity's own identity is kept beside it in `entityId`, in
whatever JSON shape it dumps to, because an integer or composite identity does not survive being
squeezed into the item id.

**The partition key is a field, not a path.** `partitionKey` is the partition the store was
connected to, or the document's own `organization_id` when it was not, or the document id when it
carries neither. That is what lets an aggregate and the command it dispatches — different
`documentType`s, one organization — land in one transactional batch.

**A unit of work is a transactional batch.** One container, one logical partition, at most 100
operations, and no server-side read set. Reads taken inside the block record the item's `_etag`,
and the writes that follow carry it as `if_match_etag`, so a document that changed underneath the
block aborts the commit with `ApplicationError(TRANSACTION_CONFLICT)`. A unit of work that spans
two logical partitions raises rather than writing non-atomically.

**Pools consume instead of being pushed.** Service Bus has no push delivery, so `pool_driver()`
returns a driver that receives from the queue or subscription, then replays the push that never
arrived into the same FastAPI app in-process over `httpx.ASGITransport`. Handlers, dependencies,
`publish_command_result` and the exception wrapping all run unchanged.

## Running the suite without a subscription

`m test-provider-azure` runs the unit tests and skips every behavioural conformance module whose
estate is absent. Two emulators cover the two ports that have one, and each module is gated on its
own environment rather than on the estate as a whole, so either can be run alone.

Cosmos DB, which covers `test_document_store.py` and `test_transactions.py` in full:

```
docker run -d --name cosmos-emulator -p 8081:8081 -e PROTOCOL=https \
  mcr.microsoft.com/cosmosdb/linux/azure-cosmos-emulator:vnext-preview
```

with `COSMOS_ENDPOINT=https://localhost:8081`, `COSMOS_DATABASE=acme`, `COSMOS_TLS_VERIFY=false`
and `COSMOS_KEY` set to the emulator's well-known key. The database and one container per service
have to exist first; the estate's Terraform creates them in a real environment.

Azurite, which covers `test_blob_store.py` apart from signing:

```
docker run -d --name azurite -p 10000:10000 \
  mcr.microsoft.com/azure-storage/azurite:latest azurite-blob --blobHost 0.0.0.0
```

with `BLOB_ACCOUNT_URL=http://127.0.0.1:10000/devstoreaccount1` and `BLOB_ACCOUNT_KEY` set to the
emulator's well-known key. `BLOB_ACCOUNT_KEY` and `COSMOS_KEY` exist for exactly this: the deployed
estate disables local authentication, so in a real environment neither is set and both clients
authenticate as the container's managed identity. A user-delegation SAS needs Entra ID, which
Azurite does not have, so the presigned-URL tests declare themselves unsupported and skip.

Service Bus and Key Vault have no emulator. `test_event_bus.py`, `test_task_queue.py`,
`test_identity.py` and `test_secret_store.py` skip unless `SERVICE_BUS_NAMESPACE` and
`AZURE_KEY_VAULT_URI` point at a real namespace and vault.
