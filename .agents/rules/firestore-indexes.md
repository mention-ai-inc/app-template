## A query that needs a composite index ships with it

Firestore serves a query only from an index. Single-field indexes are automatic; anything else needs a composite index declared in Terraform, and a query without one fails at runtime with `FAILED_PRECONDITION`. Nothing local catches it: the in-memory test repository and the `local` provider run any query.

Every organization-scoped query already filters `_partition ==` (the control plane's document store adds it), so a query needs a composite index when it also has:

- an `order_by`, including the one a cursor adds;
- a range or `!=` / `not_in` filter;
- an equality or `array_contains*` filter together with another filter on a different field;
- a vector search (`find_nearest`), which needs a vector index whatever else it filters on.

A query whose only other filter is a single equality needs none.

### Declaring one

- The index goes in the same change as the query, in the service's `firestore_indexes` list in `infrastructure/terraform/configurations/services/terraform.tfvars`:

  ```hcl
  firestore_indexes = [
    { collection = "note", fields = [{ path = "_partition" }, { path = "status" }, { path = "created_at" }] },
    { collection = "note", fields = [{ path = "_partition" }, { path = "tags", array = "CONTAINS" }] },
  ]
  ```

- Its fields are `_partition` first, then the query's equality filters, then the range or sort field, matching the query's directions. `array = "CONTAINS"` marks an `array_contains*` field; `vector_dimension = <n>` marks the embedding field of a vector search.
- Run `m terraform-services` before `m deploy-<service>`. An index takes minutes to build; the feature-environment check after deploying exercises the query.

### Review checklist

- Does a new or changed query in `infrastructure/persistence/` or `infrastructure/queries/` match a shape above?
- Is its index in `terraform.tfvars`, led by `_partition`?
- Does anything query Firestore without the control plane's document store? It must not.
