---
paths:
  - "services/*/*/infrastructure/**/*.py"
---

## A query that needs an index ships with it

A document store serves a query only from an index. The simple shapes are indexed automatically; anything the provider cannot serve from an automatic index needs one declared in the service's infrastructure, and a query without it fails at runtime, not at review. Nothing local catches it: the in-memory test repository and the `local` provider run any query.

The installed provider's rule says which query shapes need a declared index and where the declaration lives. Read it whenever you add or change a query in a repository or a query service, and ship the declaration in the same change as the query, applied before the service that runs it deploys.

### Review checklist

- Does a new or changed query combine a filter with an ordering, a range, an inequality, or a second filtered field?
- If so, is its index declared in the same change, and does the deployment plan apply it first?
- Does anything query the store without going through the control plane's document store? It must not.
