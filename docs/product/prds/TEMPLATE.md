# PRD NN: Title

**Status:** Draft
**Depends on:** PRD NN (Name), or "none"
**Depended on by:** PRD NN (Name), or "none"
**Changes:** PRD NN (Name) §a, §b-c — omit when this PRD rewrites nothing
**Changed by:** generated; omit when nothing changes this PRD
**Supersedes:** PRD NN (Name) §a-b — omit when this PRD retires nothing
**Superseded by:** generated; omit when nothing supersedes this PRD

Status is exactly `Draft`, `Reviewed`, or `Reviewed, deliberately out of v1`, and never names another
PRD. `Depends on`, `Changes` and `Supersedes` are written by hand; the three inverse fields are
generated. Run `m sync-prd-links` after editing, and `m check-prd-links` before finishing. The rules
are in `.agents/rules/prd-structure.md`.

## Problem

One paragraph. What the user cannot do today, or what the product cannot do, without this, and why it matters to the thesis in `docs/product/overview.md`.

## Grounding

The principle, model, or external standard this serves, in two or three sentences. Replace this heading with whatever discipline the product is built on, and delete the section only if genuinely inapplicable — saying so explicitly.

## Scope

### In scope

Bulleted.

### Out of scope

Bulleted, naming the PRD that owns each excluded item where one exists.

## User experience

A concrete walk-through from the user's point of view. Use a running example so the behavior is unambiguous. Cover the happy path and the one or two most likely detours. Every quoted on-screen string uses the words in `docs/product/glossary.md`.

## Requirements

Numbered. Each one testable. Use MUST for required behavior and SHOULD for strong defaults. Group under subheadings if there are more than eight.

Requirement numbers are permanent, because other PRDs and the header fields cite them. A changed requirement keeps its number and gets new text; a new one is appended with the next free number; a retired one becomes a stub reading `**Retired** by PRD NN §a-b on YYYY-MM-DD. See the Decision log.`

## Objects and contracts

The objects this PRD creates, reads, or changes, using the names in `docs/product/glossary.md`. For each: what it holds, who writes it, who reads it. Name the fields that other PRDs will depend on. Do not design storage or APIs.

## Behavior under uncertainty

What decisions the system makes on its own, what it needs as input to make them, and how a wrong decision is detected and corrected. Include the failure modes that matter most. Delete this section if nothing here is decided at runtime.

## Edge cases

Bulleted. Each names the situation and the required behavior.

## Acceptance criteria

The checklist that says this PRD is done. Each item observable in the app or in stored state.

## Open questions

Decisions this PRD leaves to the author of a later PRD or to the user, with a recommendation for each.

## Decision log

Required once anything changes or supersedes this PRD. Appended oldest first, one entry per decision, never edited once written:

- **YYYY-MM-DD — PRD NN §a-b.** What changed, why it was right, and which of this PRD's own requirements moved. The why cannot be recovered from a diff, so never omit it.
