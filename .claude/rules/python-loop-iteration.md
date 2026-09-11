---
paths:
  - "**/*.py"
---

## For-loop iteration variables

Name the loop variable as the **singular** of the iterable being walked—never a single-letter placeholder such as `i`, `x`, or `e`.

- Prefer `for item in items`, `for note in notes`, `for row in rows`.
- Avoid `for i in items`, `for x in notes`, etc., unless the domain genuinely uses a conventional letter (e.g. mathematical indices in numeric code).

Nested loops should still use meaningful singular names (often combining with qualifiers): `for outer_item in outer_items` / `for inner_item in outer_item.children`, or distinct singular nouns per collection.
