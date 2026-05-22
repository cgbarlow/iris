# ADR-213: `aggregation_list` diagram type

Status: Accepted (2026-05-22)

Builds on: [ADR-186](./ADR-186-Dynamic-List-Diagram-Type.md), [ADR-187](./ADR-187-Synthesised-Content-On-Read.md), [ADR-205](./ADR-205-Smart-Markdown-View-Type.md), [ADR-212](./ADR-212-Aggregation-Profiles-And-Engine.md).

## Context

ADR-212 ships the aggregation engine as a first-class Iris operation — callable over REST / MCP / CLI. That covers agent and automation surfaces, but Iris also needs a *visual* surface so users can pin a long-running rollup (e.g. "this week's shopping list") inside the diagram canvas and treat it like any other markdown view.

Two existing patterns suggest the shape:

- ADR-186 / ADR-187 — `dynamic_list` is a synth-on-read diagram type: storage is minimal config (`data.dynamic_source`), the resolver runs at GET time and writes the result into a synthesised `data.content`.
- ADR-205 — `smart_markdown` is a similar synth-on-read type: storage is `data.markdown_source`, resolver writes `data.content`.

A third sibling — `aggregation_list` — fits naturally.

## Decision

Register a new diagram type `aggregation_list` under the existing `markdown` notation.

### Storage

`diagrams.data` JSON:

```json
{
  "source_diagram_id": "<uuid>",
  "profile_id": "<uuid>"
}
```

That's it. No persisted markdown, no profile-data-inline. The aggregation_list is a *reference* — it points at a source diagram and a profile and the engine fills the content at read time.

### Resolution

Extend `backend/app/diagrams/service.py::_maybe_synthesise_content` with a new branch for `diagram_type == "aggregation_list"`:

```python
if diagram_type == "aggregation_list":
    from app.aggregation import engine as agg_engine
    data = diagram.get("data") or {}
    src = data.get("source_diagram_id")
    profile = data.get("profile_id")
    if src and profile:
        try:
            result = await agg_engine.run(
                db, profile_id=profile, source_diagram_id=src,
            )
            data["content"] = result.markdown
        except (AggregationProfileNotFound, AggregationSourceNotFound):
            data["content"] = "_Source or profile missing — pick a valid pair in the diagram editor._"
        except Exception as exc:
            data["content"] = f"_Aggregation failed: {exc}_"
    else:
        data["content"] = "_Select a source diagram and profile to compute._"
    data["is_content_locked"] = True
    diagram["data"] = data
    return
```

The wrapper is thin: the engine does the real work; the diagram type owns nothing beyond dispatch.

### Editing model

`aggregation_list` is **synth-on-read** — the user does not author content directly. The "edit" interaction is choosing the source diagram + profile; the canvas reads `data.content` and renders it the same way `smart_markdown` does.

For v6.21.0 the create/edit dialog supplies the source + profile pickers. The full admin/set-editor profile editor lives in this PR too — a single reusable `AggregationProfileEditor.svelte` component used both at create-diagram time (inline profile picker) and at admin/set-edit time (profile management).

### Surface parity

The diagram type adds no new write surfaces — `aggregation_list` rides on the existing `POST/PUT/DELETE /api/diagrams/...` endpoints. The diagram-type registration in the seed migration is data-only. ADR-182 parity is satisfied without changes to the parity script.

## Consequences

**Positive:**

- One more sibling in the synth-on-read family, matching the established pattern.
- Engine has TWO consumers in the codebase now (the `/api/aggregation/run` endpoint and this diagram type). Reinforces the genericness — different surfaces, same engine.
- "Pin this rollup" UX is a single new diagram_type registration plus a thin synth-on-read dispatch. The frontend gets a reused canvas (read view = `MarkdownView`, edit view = source/profile pickers).

**Negative / accepted trade-offs:**

- The aggregation runs on every read. Each `GET` recomputes — at the demo scale (30+ recipes × 10 ingredients) it's well under 200ms. If this ever becomes a bottleneck, a per-diagram cache keyed on `(source_id, source_version, profile_id, profile_version)` is straightforward.
- The user authoring the profile sees raw JSON for v6.21.0; a form-based editor is a v6.21.x follow-up. The five seeded profiles cover the common cases without authoring.

## References

- [SPEC-213-a — `aggregation_list` registration, dispatch, frontend](./specs/SPEC-213-a-Aggregation-List-Diagram-Type.md)
- [ADR-212](./ADR-212-Aggregation-Profiles-And-Engine.md) — the engine.
- [`docs/plans/issue-211-shopping-list-implementation.md`](../plans/issue-211-shopping-list-implementation.md) §4.3, §9 — frontend layout.
