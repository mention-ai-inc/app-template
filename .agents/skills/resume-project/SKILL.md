---
name: resume-project
description: Pick up a multi-session product effort where the last conversation left off - read the PRD handoff, report where things stand, and start the next step. Use at the start of any conversation about the product's PRDs or services, or when asked to continue, resume, or pick up the work.
---

# Resuming the product work

Product work spans many conversations. Its state lives in `docs/product/prds/README.md`, not in any conversation, so a new one starts from there.

## 1. Read the handoff

- Read `git log --oneline -15` and `git status` for anything since the README was last updated.
- Read `docs/product/prds/README.md` in full: the index, the groups, and **Where things stand** with its **Next step**, **Awaiting review**, and **Open questions**.
- Read `docs/product/overview.md`, `docs/product/glossary.md`, `docs/product/prds/TEMPLATE.md`, and every PRD the next step builds on.

## 2. Report where things stand

Tell the user briefly: what is done, what the next step is, and which **Awaiting review** items or open questions bear on it. Do not recap decisions they already made.

## 3. Do the next step

- **Writing a PRD:** follow `prd-structure`. Bring the user the decisions the PRD needs, each with a recommended default, before drafting. Any decision made while drafting that the user did not answer is listed for their review when the draft is handed over, and recorded under **Awaiting review** until they confirm it.
- **Building a feature:** use the `build-feature` skill. First raise any **Awaiting review** items for the PRD being built. Correct the PRD in the same change when building shows it is wrong; the PRDs stay the source of truth.

## 4. Leave the handoff current

Before the conversation ends, update the README so the next one can resume without this one:

- **Next step**;
- drafting decisions the user has not confirmed, under **Awaiting review**;
- questions deferred to later PRDs, under **Open questions** or the PRD that will decide them;
- the glossary, for every term introduced or refined, following the `glossary` rule;
- the PRD index, by running `m sync-prd-links`.

Commit and push only when the user asks.
