# ADR-217: Aggregate output provenance flag

Status: Accepted (2026-05-24)

Builds on: [ADR-212](./ADR-212-Aggregation-Profiles-And-Engine.md), [ADR-214](./ADR-214-Genericness-Invariant-Shopping-List.md).

## WH(Y)

**In the context of** the generic aggregation engine (ADR-212), which
renders deduplicated, summed-up markdown shopping-list output from
meal-plan-style smart-markdown diagrams,

**facing** the need for downstream bash orchestrators to look up
per-row metadata — for example, retailer-cached SKU values that the
maintainer pins inside each element's Product-attribute `notes` —
*without* an LLM round-trip to map "Pork mince 500 g" back onto an
element id,

**we decided for** an opt-in `output.include_provenance` flag on the
aggregation profile that causes each rendered list line to end with
` <!-- iris:element=<uuid> -->`, while leaving headings and blank
lines untouched and preserving any per-source breakdown text in front
of the comment,

**and neglected** embedding retailer-specific SKU data directly in
the aggregate output (would re-introduce domain coupling and drift
toward the risk codified in ADR-214), a JSON sidecar response shape
that returns rows + element ids structurally (bigger API surface
change for a marginal gain when consumers are already grepping
markdown), and making the comment mandatory on every aggregate run
(would alter every existing consumer's output without consent),

**to achieve** LLM-free per-line provenance lookup for downstream
consumers, with zero impact on existing aggregate consumers and zero
new write endpoints,

**accepting that** the trailing HTML comment slightly inflates each
rendered line (typically ~50 bytes) and that any future renderer
choosing to strip HTML comments would silently drop the provenance —
both deemed acceptable as the flag is opt-in and the format is widely
recognisable.

## Decision

Add `include_provenance: bool = False` to
`backend/app/aggregation/models.py::OutputConfig`. When true, the
aggregation engine appends ` <!-- iris:element=<element_id> -->` to
each rendered shopping-list line *after* any per-source breakdown
text, so the comment is always the last thing on the line. Headings
(`## ...`) and blank section dividers are untouched. The flag defaults
to false; no migration flips seeded profiles in this change. A future
PR may opt specific seeded profiles in via a paired migration.

### Genericness invariant (ADR-214)

The comment carries only the opaque `element_id` UUID and the literal
prefix `iris:element=`. No retailer terminology, no domain vocabulary,
no banned strings (per ADR-214's word-boundary check). The flag is
named `include_provenance`, not `include_skus` or similar — the
mechanism is generic and the downstream use (Woolworths SKU lookup,
EAN barcodes, supplier codes, whatever) lives entirely in the
consumer.

## Consequences

**Positive:**

- Downstream bash orchestrators get cheap, structural per-line
  provenance without parsing or LLM mapping.
- Mechanism is reusable beyond the meal-plan workflow — any
  aggregation consumer wanting element traceability can flip the flag
  on its own profile.
- No new endpoints, no surface-parity exception needed.

**Negative / accepted trade-offs:**

- Lines get slightly longer when the flag is on.
- A markdown renderer that strips HTML comments would lose the
  provenance silently. The expected consumers are bash/grep pipelines
  and CLI/MCP callers, not browser-rendered markdown, so we accept it.

## Rejected alternatives

- **Embed retailer-specific SKU data in aggregate output.** Would
  drag domain terminology into the engine and break the ADR-214
  genericness invariant. The whole point of putting SKUs in element
  attribute notes is so the engine doesn't need to know about them.
- **JSON sidecar response shape (rows + element ids structurally).**
  Larger API surface change for marginal benefit; existing consumers
  already work in markdown; a sidecar adds a parallel format to
  maintain.
- **Mandatory comment on every aggregate run.** Would alter every
  existing consumer's output without consent — opt-in via the profile
  is friction-free.

## References

- [SPEC-217-a — flag shape, comment format, acceptance criteria](./specs/SPEC-217-a-Aggregate-Output-Provenance.md)
- [ADR-212](./ADR-212-Aggregation-Profiles-And-Engine.md) — aggregation engine
- [ADR-214](./ADR-214-Genericness-Invariant-Shopping-List.md) — genericness invariant (explicitly satisfied: comment carries only opaque element_id)
