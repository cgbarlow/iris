# SPEC-210-a: Smart-markdown value overrides

Implements: [ADR-210](../ADR-210-Smart-Markdown-Value-Overrides.md)

## 1. Token grammar

```
TOKEN          := "{{" ENTITY_TYPE ":" ENTITY_ID [ ":" FIELD_SPEC ] "}}"
ENTITY_TYPE    := "element" | "package" | "diagram" | "set" | "collection" | "image"
ENTITY_ID      := [^:}]+
FIELD_SPEC     := FIELD_PATH [ "=" OVERRIDE_VALUE ]
FIELD_PATH     := "name" | "description" | "attr:" ATTR_PATH | IMAGE_SIZING
ATTR_PATH      := SEGMENT ( "/" SEGMENT )*
SEGMENT        := [^/=}]+         ; no slash, equals, or close-brace
OVERRIDE_VALUE := [^}]*           ; any text except close-brace; may be empty
IMAGE_SIZING   := "width:" NUMBER UNIT | "height:" NUMBER UNIT | "original"
```

The regex in `_TOKEN_RE` is unchanged from ADR-209 — its third capture group already accepts `[^}]*`, which subsumes the `=value` suffix.

## 2. Resolver precedence

In `backend/app/diagrams/smart_markdown.py::_resolve_one`:

```
1. If entity_type == "image":
       return _resolve_image(...)
2. If field_spec is None or empty:
       return None  (strikethrough)
3. Split field_spec at first "=":
       (field_spec_path, override_value)
       where override_value is None if no "=" was present.
4. If override_value is not None and override_value != "":
       raw_value = override_value
5. Elif override_value is not None and override_value == "":
       return None  (fillable-slot marker; renders strikethrough)
6. Else:
       raw_value = <existing per-entity-type lookup of field_spec_path>
7. If raw_value is None:
       return None
8. Look up entity display name. If None:
       return None  (dangling reference takes precedence over override)
9. Return wrapped link: "[" escape(raw_value) "](iris://" type "/" id ' "' escape(name) '")'
```

## 3. Edge cases

| Case | Token | Result |
|---|---|---|
| Stored value resolves | `{{element:UUID:attr:Unit/type}}` | `[g](iris://element/UUID "Pork mince")` |
| Override non-empty | `{{element:UUID:attr:Quantity/type=500}}` | `[500](iris://element/UUID "Pork mince")` |
| Override empty (fillable) | `{{element:UUID:attr:Quantity/type=}}` | `~~{{element:UUID:attr:Quantity/type=}}~~` |
| Override on non-attr field | `{{element:UUID:name=Custom Label}}` | `[Custom Label](iris://element/UUID "Pork mince")` |
| Override on package | `{{package:UUID:name=Aisle 7}}` | `[Aisle 7](iris://package/UUID "Pantry")` |
| Override contains `=` | `{{element:UUID:attr:foo=k=v}}` | `[k=v](iris://element/UUID "X")` — split on **first** `=` |
| Override with markdown brackets | `{{element:UUID:attr:x=hello [world]}}` | text escaped as `hello \[world\]` |
| Deleted entity + override | `{{element:DELETED:attr:x=500}}` | `~~{{...}}~~` — dangling beats override |
| Stored value present + no override | `{{element:UUID:attr:Unit/type}}` (stored=g) | `[g](iris://element/UUID "...")` (existing behaviour) |
| No override + stored blank | `{{element:UUID:attr:Quantity/type}}` (blank) | `~~{{...}}~~` (existing behaviour) |
| Image token, unaffected | `{{image:UUID:width:50%}}` | unchanged |

## 4. Backend implementation

### 4.1 Function-level changes

In `_resolve_one(db, entity_type, entity_id, field_spec)`:

```python
async def _resolve_one(db, entity_type, entity_id, field_spec):
    if entity_type == "image":
        return await _resolve_image(db, entity_id, field_spec)
    if not field_spec:
        return None

    # ADR-210: split off =value override
    if "=" in field_spec:
        field_spec_path, override_value = field_spec.split("=", 1)
    else:
        field_spec_path, override_value = field_spec, None

    if override_value is not None:
        if override_value == "":
            return None  # fillable-slot marker
        raw_value: str | None = override_value
    else:
        # existing per-entity-type lookup, using field_spec_path
        ...

    if raw_value is None:
        return None

    name = await _fetch_entity_display_name(db, entity_type, entity_id)
    if name is None:
        return None  # dangling reference
    title = _markdown_escape_title(name)
    text = _markdown_escape_link_text(str(raw_value))
    return f'[{text}](iris://{entity_type}/{entity_id} "{title}")'
```

### 4.2 Backwards compatibility

- Tokens without `=` resolve identically to today. Existing recipes and existing tests pass unchanged.
- The default fallback (`title = name or entity_id`) at line 355 of the existing implementation is **tightened** to `title = name; return None if name is None`. This is technically a behaviour change for the case "entity missing but field returned a value somehow" — which is unreachable in current code paths (every fetch_*_field returns None for missing entities). Defensive change captured in tests.

## 5. Canvas behaviour (frontend)

### 5.1 Inline editable spans for fillable slots

In `SmartMarkdownCanvas.svelte` edit mode:

1. After every resolve, scan `data.markdown_source` for tokens matching `\{\{[^}]+=\}\}` (the empty-override regex).
2. For each match in the rendered output (which the resolver wrote as strikethrough), replace the strikethrough fragment in the **edit-mode preview overlay** with a `contenteditable` span:

   ```svelte
   <span class="iris-fillable-slot"
         contenteditable="plaintext-only"
         data-token-start={start}
         data-token-end={end}
         on:blur={() => persistSlot(start, end, $$node.textContent)}>
   </span>
   ```

3. `persistSlot(start, end, value)` rewrites the substring of `data.markdown_source[start:end]` from `{{...path=}}` to `{{...path=<value>}}` (with `}` and `\` escaped) and re-renders.

The read-mode view is unchanged — fillable slots in a non-editable view render as strikethrough.

### 5.2 Picker integration

In `EntityPicker.svelte` (the ADR-206 picker), the field-step gains a new top option visible whenever the selected field is `attr:<path>`:

```
► Insert as fillable placeholder
  name
  description
  attr ► attributes ► Quantity ► type   (currently focused)
  attr ► attributes ► Unit ► type
  ...
```

Picking it inserts the token with `=` at the end and no override value. Picking the regular field option inserts the token without `=`.

### 5.3 No `{@html}` paths

The inline span is a real DOM element bound by the canvas component; no `{@html}` is used to render it. Token resolution → markdown → marked → DOMPurify → HTML remains the unchanged pipeline (protocol §7). The fillable-slot replacement happens **after** marked rendering, by walking the rendered DOM and swapping strikethrough fragments that contain the empty-override token text.

## 6. Test matrix

`backend/tests/test_diagrams/test_smart_markdown.py` gains a new test class `TestValueOverrides` with one test per edge-case row in §3 above. Existing tests remain unchanged (backward compatibility).

Frontend tests in `frontend/src/lib/canvas/text/SmartMarkdownCanvas.test.ts` (new) cover:
- The strike-through→input swap on edit-mode mount.
- Blur-persists-into-markdown-source.
- Two fillable slots in the same diagram are independently editable.
- Switching to read-mode hides the inputs (strikethrough only).
- Source-pane edit bypasses the inline UX entirely.

## 7. Migration

None. Pure additive grammar extension. Existing tokens resolve identically; existing markdown_source values are untouched. The recipe-migration script (PR 6 / SPEC-214) rewrites pre-existing free-text quantities into the new override form — separate work.

## 8. Out of scope

- Multi-value overrides (e.g. `{{...:attr:list=[a,b,c]}}`) — paths returning lists already render the JSON literal; overrides accept any string.
- Type coercion (`=500` is the string "500", not the integer). Consumers (aggregation engine) coerce per their own rules.
- Override on the `image` entity type — image tokens have their own sizing grammar, unrelated.
- Escape grammar for `=` or `}` in override values — both are technically already unescapable (the regex stops at `}`; `=` only matters at split-point). Edge case documented; no escaping syntax in v1.
