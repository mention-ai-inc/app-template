# Remove the sample: the Python backend

The decisions, section 4 and section 6 of `docs/remove-sample.md`, for a backend written in
Python. The section numbers match that file.

## Decisions

- **The membership-role cache key.** `library/library/application/auth.py` namespaces the
  organization membership cache under `Service.NOTES`. Point it at the service that owns users, or
  at whichever service every deployment includes.

## 4. Shared kernel

| File | What |
| --- | --- |
| `library/library/domain/value_objects/notes.py`, `events/notes.py`, `commands/notes.py` | Delete. |
| `library/tests/domain/events/test_notes.py` | Delete. |
| `library/tests/application/test_message_parser.py` | Rewrite against the new service's events. |
| `library/tests/test_golden_documents.py` | Builds its command and event fixtures from `SummarizeNote` and `NoteCreated`. Rebuild them from the new service's payloads; the golden fixtures under `control-plane/tests/fixtures/documents/` describe the envelope, not the payload, so `command.json` and `event.json` only change where the payload fields do. |
| `library/tests/_testutils/`, `library/tests/infrastructure/` | Four tests use `Service.NOTES` or the string `notes` as the `SERVICE` under test (`test_fake_command_dispatcher.py`, `test_in_memory_repository.py`, `test_outbox.py`, `test_repository.py`). Switch them to the new member. The `notes` field on the audit test widget is unrelated and stays. |

Run `m update-local-dependencies` after the change (`library-dependency-sync`).

## 5. Repository tooling

| File | What |
| --- | --- |
| `infrastructure/cli/language/pyright.json` | Remove the `services/notes` execution environment. |

## 6. Delete the service

| File | What |
| --- | --- |
| `services/notes/` | `git rm -r services/notes`. |
| `services/notes/tests/test_golden_documents.py` | Goes with the service; it asserts the `note.json` golden fixture. The service that replaces `notes` owns the fixture of its first aggregate and the test that asserts it, following this one's shape. |
| `backfills/backfills/migrations/20260911_note_word_count.py`, `backfills/tests/test_note_word_count.py` | Delete. This is the example backfill; write the first real one following its shape before removing it. |

Then recreate the environments and continue with `docs/remove-sample.md` section 6:

```
m init
```
