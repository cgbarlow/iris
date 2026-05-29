# ADR-224: Smart-markdown `:raw` modifier

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-224 |
| **Initiative** | Let smart-markdown tokens be embedded inside Mermaid fenced code blocks |
| **Proposed By** | Engineering |
| **Date** | 2026-05-29 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** wanting smart-markdown dashboards to drive **Mermaid
charts** (pie / xychart-beta / flowchart) from live model state — counts
of approved capabilities, per-zone element counts, hub relationship
counts — so the charts track the model instead of being a snapshot,

**facing** that smart-markdown resolves tokens BEFORE the markdown
renderer hits fenced code blocks, and the resolver wraps every value in
an ``[N](iris://…)`` markdown link (ADR-209). That link syntax is
correct for prose but **breaks Mermaid's parser** inside a ` ```mermaid `
block, so today's chart values have to be hand-typed,

**we decided to** add a tiny modifier to the token grammar: a trailing
``:raw`` suffix on the field-spec returns the resolved value **without**
the iris:// link wrap.

  - `{{element:<id>:meta:status:raw}}` → `Approved`
  - `{{element:<id>:relationship_count:raw}}` → `19`
  - `{{diagram:<id>:element_count:raw}}` → `13`
  - `{{element:<id>:detail_diagram:raw}}` → `CSE.00 Security capability zone`

Stripping happens **before** the ADR-210 ``=value`` override split and
before the ADR-221 ``detail_diagram`` special-case, so the modifier
composes with every existing token form. Outside fenced blocks the
default link-wrapped form is unchanged.

**to achieve** a one-line authoring change for any chart that wants live
numbers — wrap the chart's value with `{{…:raw}}` instead of hand-typing
it. No new tokens, no new entity types, no schema change.

**accepting** that:
- The ``:raw`` value carries no link, so the reader can't click through
  to the source — that's the point inside a chart, but it's a UX
  trade-off the author chooses per use. Outside fenced blocks, the
  default (link-wrapped) form remains the right pick.
- Aggregation engine values are already unwrapped, so the engine needs
  no change. The modifier is a render-time concern only.
- The modifier is on the **trailing** end of the field-spec. So
  ``meta:status:raw`` parses as field-spec ``meta:status`` with raw on.
  Reserving the literal token suffix ``:raw`` means a hypothetical
  future field named ``raw`` would collide; not a concern today
  (no such field exists), and we keep the option of a non-suffix
  alternative (``{{!element:…}}``, etc.) if it ever comes up.

## Rejected alternatives

- **Skip token substitution inside fenced code blocks.** Cleaner in
  theory — Mermaid blocks would be inert — but it ALSO loses the live
  numbers we wanted there. The whole point was to inject live values.
- **A separate token prefix** (``{{=element:…}}`` or ``{{!element:…}}``).
  Cleaner grammatically but it duplicates every existing token form;
  the suffix modifier is one regex, one branch.

## Dependencies

- Builds on ADR-205 (smart-markdown tokens) and ADR-209 (the link wrap
  this modifier suppresses). Composes with ADR-210 (``=value``
  overrides) and the special-case resolvers in ADR-221 / ADR-222 /
  ADR-223.

## Consequences

- Spec: SPEC-224-A.
- No migration, no surface-parity impact, no engine algorithm change.
- Authors can now make Mermaid pie/bar/flowchart values dynamic against
  the model.
