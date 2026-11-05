---
paths:
  - "docs/product/glossary.md"
  - "docs/product/prds/**"
  - "library/library/domain/**/*.py"
  - "services/*/*/domain/**/*.py"
---

## Name the domain with the glossary

The product's domain vocabulary lives in `docs/product/glossary.md`. A word means one thing everywhere: in the PRDs, in the kernel's events and commands, and in the services' code. A term used without a definition, or two words for one thing, is how a PRD ends up saying something nobody decided.

### In PRDs

- Read the glossary before writing.
- The glossary holds only terms, their definitions, and words to avoid. It names no service, vendor, or number that may change, and says nothing about how or when a term came to be. Use its terms as written, and never a word its entry says to avoid.
- A noun the domain relies on that is not in the glossary is either a new term or a sign the sentence should use an existing one. A new term goes into the glossary in the same change.
- Definitions live only in the glossary. A PRD's **Terms** section lists the terms it introduces and the ones it uses from earlier PRDs, and defines none of them.
- A PRD that refines a term updates its glossary entry, not a copy of it.
- If a term means two things, bring it to the user with a recommendation. Do not pick a meaning silently.

### In code

- Aggregates, value objects, events, commands, tools, and their fields are named with glossary terms (`Note`, `NoteSummarized`, `Summary`), never synonyms (`Memo`, `Digest`, `Abstract`).
- A domain concept with no glossary term is a gap in the PRD. Stop and add the term, correcting the PRD in the same change, before naming it in code.
- Infrastructure names that are not domain concepts (a repository, a collection, a model client) are not glossary terms and need no entry.

### Review checklist

- Does every domain noun in the change appear in the glossary, with the same meaning?
- Does the change use any word a glossary entry says to avoid?
- Does a PRD define a term that only the glossary should define?
- Does new code name a domain concept the glossary does not have?
