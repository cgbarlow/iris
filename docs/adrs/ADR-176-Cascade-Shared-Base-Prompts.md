# ADR-176: Generic creation-cascade shared base prompts

Status: Accepted (2026-05-16)
Extends: [ADR-162](ADR-162-Generic-MCP-Diagram-Creation-Workflow.md)

## Context

The first end-to-end UAT of the v6.0.15 DoView creation cascade (issue #133, the Banana Monoculture flow) surfaced a series of conversational defects that were each fixable in the `_DOVIEW_NOTATION_PROMPT` seed at `backend/app/migrations/m028_ai_creation_prompts.py:117`. But every defect generalised:

- The info-source question collapsed to a binary instead of allowing paste-or-upload — true for any cascade that needs user-supplied source material, not just DoView.
- No default name was suggested for the DoView — true for any cascade that asks the user to name what they're creating.
- The Sources subpage contained names without URLs — true for any notation with a sources/references/citation concept.
- The cascade jumped from Stage 1 (structure proposal) straight to Stage 2 (detail) without asking — true for any multi-stage creation cascade.
- No save-destination chooser fired — true for every cascade in every Set, not just for cascades originating from the Outcomes Theory Book.

Patching only `_DOVIEW_NOTATION_PROMPT` would fix the DoView path and leave the same defects waiting for every other notation that goes through this same UAT later. The plan for issue #133 instead lifts these cross-notation rules into shared base-layer prompts that compose into every notation's cascade.

Three concerns separate cleanly:

1. **Conversational shape** — how to ask the questions (always via the client's question tool when available), where to insert paste/upload affordance, when to suggest a default name, when to ask about skip-detail.
2. **Citation discipline** — how source-reference elements are formatted (raw URLs, fixed `Author/Org · Title · YYYY · URL` template).
3. **Save destination** — where the bundle lands once drafting is complete (which Iris location, which artefact formats).

Each concern is generic. Each currently lives nowhere (or in a single notation prompt). Each will keep recurring across future notations.

## Decision

Introduce **three new rows** in the `ai_creation_prompts` table at `layer=base`, `notation=NULL`, `diagram_type=NULL`, `purpose='creation_format'`, in this `display_order`:

| display_order | id | Concern |
|---|---|---|
| 1 | `creation-cascade-shared-v1` | Conversational shape (ASKING QUESTIONS, info-source paste/upload, default name, skip-detail) |
| 2 | `creation-cascade-citations-v1` | Citation discipline (raw URLs, label format) |
| 3 | `creation-cascade-destination-v1` | Save-destination chooser |

These compose into every notation's `creation_format` cascade via the existing layered-prompt composer at `backend/app/ai/creation.py:_build_layered_prompt`. The composer concatenates `layer=base` rows in `display_order` ascending, so the three new rows appear in the order above at the top of every cascade. The existing `creation-base-v1` row (DoView-era JSON output format) remains at `display_order=0`.

`creation-doview-notation-v1` is updated to defer to the shared cascade — the duplicated paste/upload, default-name, skip-detail, and destination guidance is removed from its body and lives once at the base layer.

`creation-outcomes-map-v1` is updated to reference `creation-cascade-citations-v1` instead of restating the URL rule — every source_reference element follows the shared format.

## Why three rows, not one

Each concern has a distinct life cycle:

- The conversational-shape rules apply to every cascade turn.
- The citation rules apply only when the diagram includes source-reference / citation / annotation elements — many notations skip them entirely.
- The destination chooser fires once per cascade, just before generation.

Splitting allows future ADRs to evolve any single concern (e.g. add new destination options when Phase 2 ships the renderer, change the citation label format) without rewriting unrelated rules. The cost is three rows to maintain instead of one — acceptable given the seed function re-applies all three on every startup.

## Why base layer, not new notation rows

A new `layer=base` row composes into every cascade automatically. A new notation row would have to be duplicated for every existing notation (doview, bpmn, simple, uml, archimate, c4) and would have to be added for every future notation. The base layer is the correct one because the rules are universal.

## Why update `_DOVIEW_NOTATION_PROMPT` and `_OUTCOMES_MAP_PROMPT` rather than letting the shared prompts add to them

If the notation prompt still restated the paste/upload / default-name / skip-detail / destination guidance, the model would see the same instruction twice in the composed prompt — once from the shared layer, once from the notation layer. That risks the model either obeying both (over-prompting the user) or treating one as authoritative and ignoring updates to the other (drift). Updating the notation prompts to defer to the shared layer makes the shared layer the single source of truth.

## Consequences

- New SQLite migration `m{next}_cascade_ux_polish.py` and Supabase mirror `m{next}_cascade_ux_polish.sql` INSERT the three new rows (idempotent via `INSERT OR IGNORE` on `id`).
- The same migration UPDATEs `creation-doview-notation-v1` (DoView defers to shared) and `creation-outcomes-map-v1` (cites by reference) so existing deploys pick up the changes.
- `backend/app/seed/creation_prompts.py` is updated to re-apply the three new base-layer rows + the updated DoView notation prompt on every startup, matching the existing pattern that overwrites admin edits with the canonical content.
- Composed `creation_format` cascade body grows by ~2 KB (the three new sections). Negligible at any client context budget; the more important review at Phase 1 close is whether the model parses the longer body cleanly (see ADR-177 verification).
- Notations that don't have a citations/sources concept are unaffected — the citations rules apply only when the model emits source-reference elements; they do not force a Sources page where the notation has none.

## Verification

- `pytest backend/tests/migrations/test_m{next}_cascade_ux_polish.py` green.
- `GET /api/ai/response-prompts/composed?notation=doview&diagram_type=outcomes_map&purpose=creation_format` body contains every new section.
- `GET /api/ai/response-prompts/composed?notation=bpmn&purpose=creation_format` body contains the same shared sections (cascade-generality proof).
- Manual UAT replay of the banana-monoculture flow (regression) and a fresh BPMN cascade (generality) per the Phase 1 acceptance gates in `docs/plans/issue-133-doview-mcp-polish.md`.

## See also

- [ADR-162](ADR-162-Generic-MCP-Diagram-Creation-Workflow.md) — original generic creation workflow design.
- [ADR-177](ADR-177-AskUserQuestion-MCP-Convention.md) — companion ADR landing the MCP-wide user-question rule that this cascade reinforces.
- [SPEC-176-A](specs/SPEC-176-A-Cascade-Shared-Base-Prompts.md) — schema, prompt bodies, composition rules, test plan.
- [`docs/prompts/creation-cascade-shared.md`](../prompts/creation-cascade-shared.md), [`creation-cascade-citations.md`](../prompts/creation-cascade-citations.md), [`creation-cascade-destination.md`](../prompts/creation-cascade-destination.md) — canonical paste-ready bodies.
- Issue [#133](https://github.com/cgbarlow/iris/issues/133) — UAT report and feedback.
- [`docs/plans/issue-133-doview-mcp-polish.md`](../plans/issue-133-doview-mcp-polish.md) — multi-phase plan that this ADR is part of.
