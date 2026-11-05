# Glossary

Every PRD, and every aggregate, value object, event, and command in the code, uses these terms with
exactly these meanings. Definitions live only here: a PRD that needs a new term adds it here in the
same change and lists it in its Terms section, and a PRD that refines a term updates the entry here.
The `glossary` rule is the full contract.

- **Term.** What it means, in one or two sentences, and any words to avoid for it. Name the PRD that
  owns it where one does.

## Names fixed by the foundation PRDs

As PRDs settle an object's shape, record the fixed names here with the PRD that fixed them, so a later
PRD cannot quietly rename a field other PRDs depend on.

## User-facing words

Two vocabularies usually exist: the one the code and these documents use for objects and fields, and
the one that reaches a screen. Where they differ, keep a table mapping the internal term to the words
shown, and say which internal terms must never appear in a user-facing string.

| Internal term | On screen |
| --- | --- |
