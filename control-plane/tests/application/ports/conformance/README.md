# Port conformance suite

Every cloud provider adapter must pass this suite. It is the behavioural half of
`library/tests/application/ports/test_conformance.py`: that module checks the adapters have the
right *shape*, this package checks they have the right *behaviour*.

The tests only ever touch the ports in `library/library/application/ports/`. They reach every
collaborator through the `ICloudProvider` returned by the registry, never through a concrete class,
and they never branch on `isinstance`. When an adapter cannot satisfy a test, the entry declares a
capability flag and the test skips itself.

## Registering a new provider

Add one entry to `PROVIDERS_UNDER_TEST` in `providers.py`:

```python
AWS = ProviderUnderTest(
    name="aws",
    factory=lambda: AWS_PROVIDER,
    reset=reset_aws,
    skip_reason=None if os.getenv("AWS_CONFORMANCE_ENDPOINT") else "no local AWS endpoint configured",
    recorded_messages=aws_recorded_messages,
    recorded_tasks=aws_recorded_tasks,
)

PROVIDERS_UNDER_TEST: list[ProviderUnderTest] = [LOCAL, AWS]
```

Every test then runs a second time with the id `aws`.

## What an entry has to supply

| Field | Meaning |
| --- | --- |
| `name` | The pytest parameter id. |
| `factory` | Returns the `ICloudProvider`. It is installed with `set_cloud_provider` for the test. |
| `reset` | Puts the provider back to empty state. Called before and after every test. |
| `skip_reason` | Set it to skip the whole suite for this provider, e.g. when credentials are absent. |
| `recorded_messages` | Reads back what `IEventBus.publish` sent. Absent means the event-bus recording tests skip. |
| `recorded_tasks` | Reads back what `ITaskQueue.add_task` enqueued. Absent means the task-queue recording tests skip. |

`reset` must clear everything the suite writes to: documents, published messages, enqueued tasks,
and the blobs in the conformance bucket (`CONFORMANCE_SERVICE` / `CONFORMANCE_BUCKET`). Without it
the tests are order-dependent.

`recorded_messages` and `recorded_tasks` exist because `IEventBus` and `ITaskQueue` are write-only
ports: nothing in the contract reads back what was sent, so the suite needs a provider-supplied
window onto the transport. Normalise into `RecordedMessage` / `RecordedTask`; the tests never see
the provider's own types.

## Capability flags

A test that cannot apply to a provider must be turned off by a flag on the entry, never by a check
inside the test. The flags default to "the adapter does this":

| Flag | Turned off means |
| --- | --- |
| `supports_presigned_urls` | `IBlobStore.get_presigned_url` is not implemented. |
| `presigned_urls_create_missing_objects` | Signing a path that holds no object does not create an empty one. |

Prefixing `FEATURE_ENVIRONMENT` in `IRuntimeContext.scope_resource_name` is **not** a flag. Every
resource name and hostname in every estate carries that prefix, so an adapter that ignores it is
wrong rather than different. Read it from the environment on each call, as `local` and `gcp` both do.

## Adding a test

One module per port. Use the entity fixtures in `tests/infrastructure/persistence/mocks.py` rather
than new ones, and assert only what the port promises: anything you can see solely through one
adapter's internals belongs in that adapter's own test module, not here.
