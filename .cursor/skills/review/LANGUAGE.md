# Python review standards

## Tests

- Test paths mirror source paths; tests use `async def` without a decorator.
- Helpers and builders use double-underscore names and live at the bottom.
- Call records use `NamedTuple`; avoid `object`, broad `Any`, and dictionary-shaped records.
- Cross-service fakes live in `library/library/_testutils` and `control-plane/control_plane/_testutils`; service-specific stubs live in `tests/stubs`.
- Do not add type-ignore directives merely to make a test pass.
- `python-service-tests` is the full convention.

## Rules

- `aggregate-public-api`, `llm-value-objects`, `python-service-tests`, and the `*-python` companions of the layer-neutral rules apply alongside them.
- A kernel change that was not followed by `m update-local-dependencies` makes every service result suspect (`library-dependency-sync`).

## Verification

- `m test-service-<svc>`, `m test-library`, `m test-backfills` as the diff requires, then `m run-checks-backend`.
