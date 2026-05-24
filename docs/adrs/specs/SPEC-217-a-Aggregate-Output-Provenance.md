# SPEC-217-a: Aggregate output provenance

Implements: [ADR-217](../ADR-217-Aggregate-Output-Provenance.md).

## 1. Profile shape

A new optional boolean field on `OutputConfig` in
`backend/app/aggregation/models.py`:

```python
class OutputConfig(BaseModel):
    # … existing fields …
    show_per_source_breakdown: bool = False
    breakdown_format: str = " ({sources_joined})"
    include_provenance: bool = False
```

- Type: `bool`.
- Default: `False` — existing consumers see no change.
- Scope: per-profile. Each aggregation profile opts in (or not)
  independently via `profile_data.output.include_provenance`.
- No migration in this change. Seeded profiles keep their existing
  `profile_data` shape; pydantic supplies the default at load time.

## 2. Comment format

When `include_provenance` is `True`, every rendered shopping-list line
in the engine's output has the following string appended verbatim
*after* any per-source breakdown text:

```
 <!-- iris:element=<element_id> -->
```

- Single leading space.
- Literal prefix `<!-- iris:element=`.
- `<element_id>` is the row's token id (a UUID).
- Literal closing ` -->`.

The comment is always the **last** thing on the line.

## 3. Engine behaviour

In `backend/app/aggregation/engine.py::_format_output`, after the
existing per-source breakdown append:

```python
if output.show_per_source_breakdown:
    line += _render_breakdown(output.breakdown_format, r.sources)
if output.include_provenance:
    line += f" <!-- iris:element={r.token_id} -->"
out_lines.append(line)
```

The comment is appended only to lines produced by `_render_line` (the
shopping-list rows). Group headings (`## <group>`) and blank section
dividers are produced separately and are unaffected.

## 4. Acceptance criteria

Mirrored from the two new tests in
`backend/tests/test_aggregation/test_engine.py`:

1. **`test_include_provenance_off_omits_comments`** — With
   `include_provenance` unset (or `False`), the rendered markdown
   contains zero occurrences of the substring `<!-- iris:element=`.
2. **`test_include_provenance_on_appends_comment_per_line`** — With
   `include_provenance=True`:
   - Every line beginning with `- ` (a rendered list row) ends with
     ` -->` and contains a `<!-- iris:element=<uuid> -->` comment.
   - The `<uuid>` matches the correct row's element id (verified by
     matching the visible element name on the line).
   - No heading line (`## ...`) carries the comment.
   - No blank line carries the comment.
   - When per-source breakdown is also enabled, the breakdown text
     (e.g. `(Recipe A 500)`) appears in the line *before* the
     provenance comment.

## 5. Out of scope

- Flipping any seeded profile's `include_provenance` to `True`. That
  would be a paired SQLite/Supabase migration in a future PR.
- A frontend toggle in the profile editor — the editor already
  round-trips arbitrary `profile_data` JSON; a labelled checkbox can
  be added later.
- An MCP/CLI flag override at run time. The flag is per-profile by
  design — the consumer that wants provenance configures its own
  profile.
- Carrying additional metadata in the comment (bucket, source label,
  etc.). Out of scope; the element id is sufficient for the
  downstream lookup use case in ADR-217. A v2 comment format could be
  added later if needed.
