# Defects

Bugs that need no product decision. A defect whose fix requires choosing what the product should do is
not a defect — it is a PRD, and belongs in `prds/`.

Each entry records what is wrong, where it lives, what has been confirmed against the code, what has
not, and what it would take to confirm. Separating the confirmed from the unconfirmed is the point: a
reader decides what to do next from how much is actually known, and "I read the line" and "I think so"
are different claims.

Entries are appended oldest first, numbered `D1`, `D2`, and so on. A fixed defect moves to **Fixed**
with the commit that fixed it, rather than being deleted, so a reader can tell the difference between
"never happened" and "happened and was dealt with".

## Open

### D1 — One-line summary of what is wrong

Reported YYYY-MM-DD. What the user saw, in their terms.

Where it lives, as `path/to/file.py:123`, and what the code actually does. Name the correct behavior
nearby if there is one — a second code path that gets the same thing right is the strongest evidence
that this one is a defect rather than a design.

**Confirmed:** what you verified, and how. **Not confirmed:** what you could not, and what it would
take — a log field in a feature environment, a repro on a device, a query against stored state.

## Fixed

Nothing yet.
