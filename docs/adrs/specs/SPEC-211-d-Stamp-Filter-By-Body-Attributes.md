# SPEC-211-d: Stamp filter by body-referenced attributes

Implements: [ADR-215](../ADR-215-Stamp-Filter-By-Body-Attributes.md). Extends [SPEC-211-a §3](./SPEC-211-a-Element-Template-Stamps.md).

## 1. Algorithm

In `backend/app/element_templates/service.py::list_stamps_for_element`, after the existing scope and `element_type` filters, apply:

```python
import re

_BODY_ATTR_TOKEN_RE = re.compile(
    r"\{\{self:attr:attributes/([^/}]+)/[^}]+\}\}"
)


def _required_attr_names(stamp_body: str | None) -> set[str]:
    """Return the set of attribute NAMEs referenced by self:attr tokens
    in the stamp body. Matches {{self:attr:attributes/<NAME>/<anything>}}
    — the same shape the seeded stamps use and that ADR-210 documented."""
    if not stamp_body:
        return set()
    return set(_BODY_ATTR_TOKEN_RE.findall(stamp_body))


def _element_attr_names(element_data: dict[str, Any]) -> set[str]:
    """Return the set of attribute names on element.data.attributes."""
    attrs = element_data.get("attributes")
    if not isinstance(attrs, list):
        return set()
    out: set[str] = set()
    for a in attrs:
        if isinstance(a, dict):
            name = a.get("name")
            if isinstance(name, str):
                out.add(name)
    return out
```

The filter inside `list_stamps_for_element`:

```python
# After fetching candidate stamps in scope, before returning:
required = _required_attr_names(stamp_body)
if required and not required.issubset(element_attr_names):
    continue   # stamp doesn't apply
```

- `required` is empty → no `attr:` tokens in the body → the body filter passes trivially (stamps that only reference `name`/`description` still show).
- `required` non-empty but a subset of `element_attr_names` → stamp applies.
- `required` non-empty and at least one name missing on the element → stamp hidden.

## 2. Endpoint shape

Unchanged. `GET /api/element-templates/stamps?element_id=<id>` still returns `{items: [...]}` with the same shape; the body filter is purely a server-side narrowing.

## 3. Backwards compatibility

- Existing five seeded stamps each reference attributes in their bodies. After the filter ships:
  - **Ingredient** (a.k.a. Quantified item — being renamed in PR 13): body references Quantity + Unit. Shows for elements with both.
  - **Sized story**: body references Points.
  - **Logged work**: body references Hours.
  - **Line item**: body references Amount + Currency.
  - **Read entry**: body references Pages + Author.
- The 178 live grocery items in the user's UAT have Quantity + Unit (after the v6.22.0 backfill) → Ingredient stamp will show; the other four won't. Exactly the requested behaviour.
- User-authored stamps whose body uses attributes the element doesn't have → silently hidden. Documented in the stamp-editor help text in a future polish PR.

## 4. Tests

`backend/tests/test_element_templates/test_stamps.py` gains a new section `test_body_attribute_filter` with cases:

- Stamp body referencing only `name` → applies to any matching-element_type element.
- Stamp body referencing `{{self:attr:attributes/Points/type=}}` → applies only to elements that have a `Points` attribute.
- Stamp body referencing `{{self:attr:attributes/Quantity/type=}} {{self:attr:attributes/Unit/type}}` → applies to elements with both Quantity and Unit; hidden from elements missing either.
- Stamp body that doesn't follow the `attributes/<NAME>/<path>` shape (e.g. `{{self:attr:topLevel/type}}`) — required set is empty (regex doesn't match top-level paths), filter is permissive. Documented as an edge case.

`SPEC-211-a §7` tests assertion that the seeded globals all appear for a `class`-typed element with no attributes: this assertion gets refined — only the body-trivial seeded stamps appear (none of them are body-trivial), so an `element_type=class` element with no attributes now sees zero seeded stamps. Updated to assert this matches the spec.

## 5. Edge cases

| Case | Behaviour |
|---|---|
| Stamp body has multiple references to the same attribute | `required` is a set → deduplicated, no effect. |
| Stamp body has a typo in attribute name | Required set contains the typo → no element has that attribute → stamp hidden. The author sees absence and fixes the body. |
| Element has the attribute name with different case (e.g. `quantity` vs `Quantity`) | Case-sensitive match. Mismatch → hidden. Iris's existing attribute model is case-sensitive everywhere. |
| Stamp body references an attribute path that uses non-trivial drill (e.g. `attributes/Products/0/name`) | Regex captures the first segment after `attributes/` → `Products`. Hidden unless the element has a `Products` attribute. Reasonable. |
| Empty stamp body (rare — should be rejected at write time by SPEC-211-a §3) | `required` empty → passes the body filter. Element_type filter still applies. |
| Stamp body uses `{{element:UUID:attr:...}}` (concrete element, not `self`) | Regex matches on `self:attr:`, not `element:`; concrete-element tokens contribute nothing to `required`. This is correct — concrete-element stamps don't templatise. |

## 6. Genericness (ADR-214)

The filter logic is generic — no domain terminology. The seeded stamps' applicability flows from data, not code.

## 7. Risk

- Low. Pure additional filter on top of existing logic. Stamps that previously appeared and shouldn't have will now be hidden; stamps that previously appeared and should appear continue to do so (the seeded stamps' bodies all reference attributes that exist in the user's data).
- If a stamp body is authored badly (e.g. references an attribute that no element has), it disappears entirely. Mitigation: stamp editor could surface "this stamp will apply to N elements" as a hint — future polish.

## 8. Out of scope

- Updating the stamp editor UI to warn when a body references attributes not on the source element.
- Bulk previewing "which elements would see this stamp" for a given stamp.
- Mixing "any-of" semantics for some stamps.
