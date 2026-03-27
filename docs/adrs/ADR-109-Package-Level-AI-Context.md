# ADR-109: Package-Level AI Context

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-109 |
| **Initiative** | Package-Level AI Context |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-25 |
| **Status** | Approved |
| **Supersedes** | — |
| **Superseded By** | — |
| **Related ADRs** | ADR-093 (AI Model Management Foundations), ADR-108 (Bulk DoView PPTX Import) |

---

## ADR (WH(Y) Statement format)

**In the context of** Ask AI with sets containing multiple packages (e.g., after bulk DoView import via ADR-108, where each imported PPTX file creates a separate package within the same set), where packages represent distinct architectural concerns, programme areas, or organisational units,

**facing** the need to constrain AI context to specific packages within a set, because the current multi-set Q&A implementation (ADR-093) builds context from all diagrams and entities across all selected sets with no ability to filter below the set level — resulting in unfocused AI responses when a set contains dozens of packages spanning unrelated domains, wasted tokens on irrelevant context, and inability to ask targeted questions about a specific programme area or architectural concern,

**we decided for** adding an optional `package_ids` field to the `MultiSetQARequest` and filtering the context building pipeline to include only diagrams whose `parent_package_id` is within the selected packages (including descendant packages), so that users can drill into specific packages within their selected sets for focused AI analysis while maintaining full backward compatibility when no packages are selected,

**and neglected** package-only endpoints that bypass set selection entirely (breaks the established multi-set Q&A pattern, creates a parallel API surface, and loses the ability to cross-reference across sets) and client-side filtering of AI responses after generation (wastes tokens by sending irrelevant context to the LLM, produces lower quality responses, and does not reduce API costs),

**to achieve** focused AI responses scoped to specific architectural concerns within large multi-package sets, reduced token usage through precise context selection, and the ability to ask targeted questions about individual programme areas or organisational units without noise from unrelated packages,

**accepting that** the UI requires additional complexity for package drill-down within the set selector, users must understand the package hierarchy to make effective selections, and the `package_ids` filter adds a new dimension to context building that must be tested across all AI provider integrations.

---

## Problem Statement

After bulk DoView import (ADR-108), a single set may contain many packages — one per imported PPTX file — each representing a distinct programme area or strategic theme. When a user asks AI questions about such a set, the current multi-set Q&A system (ADR-093) builds context from all diagrams and entities across the entire set, including packages unrelated to the user's question. This produces unfocused AI responses, wastes LLM tokens on irrelevant context, and makes it impossible to ask targeted questions like "What are the key causal pathways in the Health Programme?" without also including context from Education, Environment, and other unrelated packages. Users need the ability to select specific packages within their sets to scope AI context precisely.

---

## Decision Details

### 1. API Extension

The existing `MultiSetQARequest` model is extended with an optional `package_ids` field:

```python
class MultiSetQARequest(BaseModel):
    question: str
    set_ids: list[UUID]
    package_ids: list[UUID] | None = None  # NEW: optional package filter
    conversation_id: UUID | None = None
```

When `package_ids` is `None` or an empty list, the context builder includes all diagrams from the selected sets (existing behaviour, no regression). When `package_ids` contains one or more UUIDs, only diagrams whose `parent_package_id` matches a selected package (or a descendant of a selected package) are included in the context.

### 2. Context Builder Filtering

The context building pipeline is modified to accept the optional `package_ids` parameter:

1. **Resolve descendant packages** — for each selected `package_id`, recursively collect all descendant package IDs (packages whose `parent_package_id` chain leads to a selected package). This ensures selecting a top-level package includes all nested sub-packages.
2. **Filter diagrams** — when querying diagrams for context, add a `WHERE parent_package_id IN (expanded_package_ids)` clause. This filters at the database level before any context serialisation, ensuring irrelevant diagrams never consume memory or tokens.
3. **Filter entities** — entities are included only if they appear on at least one diagram that passed the package filter. Entity filtering is derived from diagram filtering (not independent), maintaining consistency.

### 3. Backward Compatibility

The `package_ids` field is optional and defaults to `None`. When not provided:

- The context builder behaves identically to the pre-ADR-109 implementation
- All diagrams from selected sets are included
- No descendant package resolution occurs
- Existing API clients and frontend flows continue to work without modification

### 4. UI Integration

The frontend `MultiSetSelector` component is enhanced to support package drill-down:

- Each selected set is expandable to show its package hierarchy
- Packages are displayed as a tree with checkboxes
- Selecting a parent package automatically includes all descendants
- Deselecting all packages reverts to full-set context (no filter)
- The selected `package_ids` are included in the `MultiSetQARequest` when the user submits a question

---

## Consequences

**Positive:**
- Focused AI responses scoped to specific architectural concerns within multi-package sets
- Reduced token usage through precise context filtering at the database level
- Backward compatible — no regression for users who do not use package filtering
- Supports the bulk import workflow (ADR-108) where sets naturally contain many packages
- Package tree in the UI provides clear visibility into set structure

**Negative / Risks:**
- UI complexity increases with the package drill-down in the set selector
- Users must understand the package hierarchy to make effective selections
- Descendant package resolution adds a recursive query that could be slow for deeply nested hierarchies
- The `package_ids` filter must be tested across all AI provider integrations to ensure consistent behaviour
- Risk of confusion if users forget they have packages selected and receive unexpectedly narrow results

---

## Attribution

The DoView methodology is created by Dr Paul Duignan and is open to use under the [DoView Planning Attribution & Trademark Use Policy](https://www.doviewplanning.org/trademarkuse). This implementation is not created or endorsed by DoViewPlanning.org.
