# PRDs

Product requirements for the app described in `docs/product/overview.md`. Terms are defined in `docs/product/glossary.md`. Every PRD follows `TEMPLATE.md`.

Groups are ordered by dependency. A group depends on the groups above it. This is the reading order, not the build order.

**This table is generated.** Run `m sync-prd-links` after editing any PRD, and `m check-prd-links` before you finish; the latter runs as part of `m run-checks`.

## How to read these

Every PRD describes the product as it is meant to be today. A later decision that changes a requirement is folded into the PRD that owns it, so one document always answers "what does this do now" — you never have to diff a chain of amendments in your head.

Each PRD's header names what it connects to. `Depends on` and `Changes` and `Supersedes` are written by hand; their three inverses are generated, so both ends of every relationship always agree. References bind at requirement granularity — a `Changes` field reading `PRD NN (Name) §2, §5, §18-20` names requirements in the target's own numbering, and requirement numbers are permanent so those references never rot.

Why a requirement says what it says lives in the owning PRD's `## Decision log`, appended oldest first and never edited. The PRD that argued for a change keeps the argument; the requirements move. `.agents/rules/prd-structure.md` is the full contract.

Bugs that need no product decision are not PRDs. They live in `docs/product/defects.md`.

## Index

No PRDs yet. Add the first as `01-<slug>.md` from `TEMPLATE.md`, then run `m sync-prd-links` — it writes the rows of this table from the files, so do not hand-maintain it.

| # | PRD | Group | Status |
| --- | --- | --- | --- |

## Groups

Add a heading per group as the set grows, saying what the group covers and why its PRDs must be built in the order given. A group note is the place to record an ordering constraint that the dependency edges alone do not make obvious.
