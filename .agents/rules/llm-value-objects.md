## LLM responses emit value objects, not primitives

When an infrastructure service under `services/<svc>/<svc>_service/infrastructure/services/<name>/` calls an LLM, the response model in `models.py` should type its fields with the same value objects the domain interface expects. Do **not** type fields as `str` / `int` / enum-strings and then wrap them into value objects at the call site (in `service.py` or in a `to_domain()` method).

The good shape:

```python
# models.py
class GeneratedFoo(BaseModel):
    title: NoteTitle = Field(description="...")
    markdown: LLMMarkdown = Field(description="...")
```

```python
# service.py
return Foo(title=result.output.title, markdown=result.output.markdown)
```

**Not** the older pattern:

```python
# models.py
class GeneratedFoo(BaseModel):
    title: str
    markdown: str

# service.py
return Foo(title=NoteTitle(result.output.title), markdown=LLMMarkdown(result.output.markdown))
```

### Why

- Pydantic coerces strings to `StringValueObject` / `IDValueObject` / `EnumValueObject` subclasses via their `__get_pydantic_core_schema__`, so the JSON schema sent to the model is unchanged.
- Validation runs once, at the LLM-output boundary. Double-wrapping (`NoteTitle(result.output.title.title)`) is dead work and reads as if the type system was being defeated.
- The service file becomes a pass-through, which makes it obvious what the LLM is responsible for producing.

### When primitives are correct

- The domain itself uses a primitive. E.g. a domain interface whose result is a plain `str` — the LLM model should also return `str`.
- The field is a genuine `int` / `bool` / `float` (a score, a flag) with no corresponding value object.
- The field is a `Literal[...]` representing a small enumeration that lives only inside the LLM response (e.g. a tri-state decision tag that is destructured by the service before becoming domain data).

### Prompt-context models follow the same rule

`*Context` models that wrap prompt inputs (the `user_prompt` payload) should also use value objects when the source data is already in value-object form. This keeps schemas consistent across sibling services — two context models that both carry note IDs and bodies should type them as `NoteID` / `NoteBody`, not `str` / `str`.

### Normalization belongs at the boundary, not in the service

If the LLM tends to return strings with trailing whitespace, leading headings, etc., put the cleanup in a `@field_validator` on the response model — not as `.strip()` + re-wrap in the service. The field validator returns the normalized value object; the service still passes through.

```python
class GeneratedTitle(BaseModel):
    title: NoteTitle = Field(description="...")

    @field_validator("title", mode="after")
    def strip_title(cls, v: NoteTitle) -> NoteTitle:
        return NoteTitle(v.strip())
```

### Plain-text LLM output

For services that want **text output** (not structured JSON) — e.g. a chatbot reply — use `output_type=TextOutput(MyValueObject)` rather than `output_type=str` followed by a wrap. pydantic-ai will call `MyValueObject(text)` for you. The check `if output is str:` in pydantic-ai's `_output.py` only treats the literal `str` type as text output; a bare `StringValueObject` subclass would otherwise be treated as structured output.

### Reference implementations

Fully migrated services to mirror when adding new ones:

- `services/notes/.../infrastructure/services/summarizer/`
