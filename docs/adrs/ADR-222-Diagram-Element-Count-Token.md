# ADR-222: Smart-markdown diagram element-count token

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-222 |
| **Initiative** | Let smart-markdown show a live count of the elements in a referenced view |
| **Proposed By** | Engineering |
| **Date** | 2026-05-29 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** the #242 capability demo, where a "capability count"
was a hand-typed literal (`{{element:…:attr:…/Capabilities/type=10}}`)
claiming to be "real … straight from the elements" when it was not — and
more generally, authors wanting a smart-markdown figure that reflects the
*actual* contents of a view rather than a number they have to maintain by
hand,

**facing** that the smart-markdown resolver (ADR-205/209/210) only renders
entity *fields* and `=value` overrides, and the aggregation engine
(ADR-212) only sums/counts values already present as tokens — neither can
count the nodes drawn on a canvas/class diagram,

**we decided to** add a new smart-markdown field-spec on **diagram**
tokens: `{{diagram:<id>:element_count}}` resolves to the number of
**element nodes** on that diagram's current canvas — nodes whose
`data.entityType` is set and is not a structural decoration
(`diagram_frame` / `note`). The value is wrapped in the usual
`iris://diagram/<id>` link (ADR-209), so the count is clickable and drills
into the view it counts. A missing/deleted diagram resolves to `None` →
the standard strikethrough fallback.

**to achieve** a genuinely live figure: when the view gains or loses
elements, the rendered count follows on next read (smart-markdown is
computed on read, ADR-187). For the #242 demo this lets each **zone**
heading show the real number of capabilities in that zone's view, instead
of a hand-maintained per-area literal.

**accepting** that:
- The count is **per referenced view**, so it reflects whatever that view
  contains. In the #242 demo the views are *zone* diagrams, so the count
  is a per-zone figure (the demo places it on the zone heading, not on the
  individual capability-area lines — those would all show the same zone
  number).
- "Element node" is defined structurally (has `entityType`, not
  `diagram_frame`/`note`). It counts drawn nodes, not distinct underlying
  elements — if the same element is drawn twice it counts twice. This
  matches "how many things are on this view".
- This is a **smart-markdown render** feature only. The aggregation engine
  is unchanged; rollups that want a real count would need a separate
  follow-up (the engine still only sees tokenised values).

## Rejected alternatives

- **Teach the aggregation engine to count canvas nodes.** Heavier (engine
  + profile-schema change) and only needed if rollups must sum live
  counts. Deferred; the demo's need is a single per-zone figure, which a
  render-time token covers.
- **Materialise the count into an element attribute.** A stored snapshot
  isn't live and needs a recompute path; the whole point was to stop
  hand-maintaining the number.

## Dependencies

- Builds on ADR-205 (smart-markdown tokens) and ADR-209 (`iris://` link
  wrapping). Related to ADR-221 (an element's detail view is a natural
  target for this token).

## Consequences

- Spec: SPEC-222-A. New token documented for the picker/help in a
  follow-up if needed.
- No migration, no surface-parity impact (render-only).
