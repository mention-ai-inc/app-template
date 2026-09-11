---
paths:
  - "**/*.py"
---

## Do not wrap value objects in `str()` or `int()`

Domain value objects subclass their primitive base type:

- `StringValueObject` → `str`
- `IDValueObject` → `str`
- `IntegerValueObject` → `int`
- `EnumValueObject` → `StrEnum`

Because they **are** the primitive, `str(my_id)` and `int(my_count)` are no-ops that hide the type and clutter diffs. Use the value object directly anywhere a `str`, `int`, or enum string is expected — function args, f-strings, dict keys, `.startswith()`, `.encode()`, comparisons with plain strings, logging fields typed as `str`, etc.

```python
# ❌ redundant
namespace=str(organization_id)
cache_key = str(note_id)
title_by_id = {note.id.to_id(): str(note.title) for note in notes}
if str(note.id) == requested:
    ...

# ✅ use the value object as-is
namespace=organization_id
cache_key = note_id
title_by_id = {note.id.to_id(): note.title for note in notes}
if note.id == requested:
    ...
```

When writing or reviewing code, strip unnecessary `str(...)` / `int(...)` on value objects in the same diff — do not leave new wraps in place "because the surrounding file still does it."

### When wrapping **is** correct

- **Constructing a different value object** from raw input: `NoteTitle(raw_string)`, `NoteID(...)`. That is validation/coercion, not `str()`.
- **Converting between value object types** when the types differ: `NoteSummaryID(note.id)` — call the target constructor, not `str(note.id)`.
- **Non–value-object values**: `str(exc)`, `str(uuid.uuid4())`, `str(time.time())`, plain variables typed as `object` or unknown externals.
- **`ModelValueObject`** (Pydantic models): not a `str` subclass. Use `.to_id()`, field access, or an explicit serializer — not bare `str(model_vo)`.

### Tests

Prefer direct comparison without `str()` when asserting on value objects:

```python
# ❌
assert str(note.id) == "note-1"
assert {str(note.id) for note in notes} == {"note-1"}

# ✅
assert note.id == "note-1"
assert {note.id for note in notes} == {"note-1"}
```

See also the `llm-value-objects` rule: the LLM boundary should emit value objects directly; downstream code should pass them through without re-wrapping.
