# ADR-043: Template Designation

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-043 |
| **Initiative** | Template Designation (WP-13) |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-01 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris modelling workflow where users create models that serve as reusable starting points (templates) for other models, but currently have no way to distinguish template models from regular working models in the model list or detail views,

**facing** the need for a simple mechanism to mark models as templates and filter the model list to show only templates, enabling users to quickly find and clone template models as starting points for new designs,

**we decided for** leveraging the existing tag management system (WP-9) to implement template designation as a special `template` tag, with a dedicated "Template" checkbox on the model detail overview tab that adds/removes the tag via the existing tag API endpoints, a "Templates" toggle button on the model list page that filters to models with the `template` tag, and a visual "Template" badge on model cards/list items that have the tag,

**and neglected** a dedicated `is_template` boolean field on the model schema (would require backend schema changes, migrations, and API modifications when the tag system already provides the needed semantics), and a separate template management page (templates are just tagged models and should remain in the main model list with filtering),

**to achieve** a lightweight template designation system that reuses existing infrastructure (tag API, tag display), requires no backend changes, and provides clear visual distinction between template and non-template models,

**accepting that** template designation is purely a tag convention with no special backend enforcement, meaning any user with tag permissions can add/remove the template tag, and that template models appear in the regular model list (filtered via the toggle) rather than in a separate area.

---

## Options Considered

### Option 1: Template Tag via Existing Tag API (Selected)

**Pros:**
- No backend changes required — tag API endpoints already exist
- Reuses existing tag infrastructure (add/remove/filter)
- Simple, convention-based approach with minimal code changes
- Consistent with the tag-based filtering already on the model list page

**Cons:**
- No backend enforcement of template semantics
- Template tag could be manually added/removed via the general tag input

**Why selected:** Maximum reuse of existing infrastructure with minimal code changes. The tag system was designed to support exactly this kind of categorization.

### Option 2: Dedicated `is_template` Boolean Field (Rejected)

**Pros:**
- Stronger backend semantics and potential for template-specific behavior
- Cannot be confused with user-created tags

**Cons:**
- Requires database migration, schema changes, API modifications
- Over-engineered for a feature that is purely a UI categorization concern
- Would need to keep in sync with any future tag-based filtering

**Why rejected:** Unnecessary complexity when the tag system provides identical functionality.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-03-01 | Accepted | Add template designation via tag system | 6 months | 2026-09-01 |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Architecture Team | 2026-03-01 |
| Accepted | Project Lead | 2026-03-01 |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Depends On | ADR-001 | Enhanced ADR Format | This ADR follows the enhanced WH(Y) format |
| Depends On | WP-9 | Tag Management | Template designation uses the tag API from WP-9 |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-043-A | Template Designation | Technical Specification | [specs/SPEC-043-A-Template-Designation.md](specs/SPEC-043-A-Template-Designation.md) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
