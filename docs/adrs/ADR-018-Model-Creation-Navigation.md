# ADR-018: Model Creation Navigation

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-018 |
| **Initiative** | Model Creation Navigation |
| **Proposed By** | Architecture Team |
| **Date** | 2026-02-28 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris models list page, where creating a new model via the "New Model" dialog leaves the user on the models list instead of taking them to the newly created model's detail page,

**facing** the need for a smoother creation workflow where users can immediately start working with a model after creating it, rather than having to locate and click on it in the list,

**we decided for** navigating the user to the new model's detail page (`/models/{id}`) immediately after successful creation, using SvelteKit's `goto()` with the ID returned from the POST response,

**and neglected** keeping the current behaviour of refreshing the models list after creation (which forces an unnecessary extra click to reach the new model), and showing a toast notification with a link to the new model (which adds UI complexity without improving the core workflow),

**to achieve** a streamlined model creation experience where users land directly on the detail page ready to add entities, configure the canvas, or edit metadata, reducing friction from two actions (create + navigate) to one,

**accepting that** the models list will not be visually updated until the user navigates back to it, and that users who want to create multiple models in succession will need to navigate back to the list each time.

---

## Options Considered

### Option 1: Navigate to Model Detail Page After Creation (Selected)

**Pros:**
- Eliminates the extra click to reach the new model
- Matches the common UX pattern of "create then edit"
- Simple implementation using `goto()` and the response ID

**Cons:**
- Users creating multiple models in succession must navigate back to the list
- Models list is not visually updated until revisited

### Option 2: Stay on Models List and Refresh (Current Behaviour, Rejected)

**Pros:**
- Users see the new model in context of all models
- Easy to create multiple models in succession

**Cons:**
- Requires an extra click to reach the new model
- The most common next action (editing the model) requires additional navigation

**Why rejected:** The extra navigation step adds unnecessary friction. Most users want to start working with a model immediately after creating it.

### Option 3: Toast Notification with Link (Rejected)

**Pros:**
- User stays on the list and can optionally navigate to the new model

**Cons:**
- Adds UI complexity (toast component, timing, positioning)
- Passive notification is easy to miss or dismiss accidentally
- Still requires a click to reach the new model

**Why rejected:** Adds complexity without meaningfully improving the workflow over direct navigation.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-02-28 | Accepted | Implement navigation after model creation | 6 months | 2026-08-28 |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Architecture Team | 2026-02-28 |
| Accepted | Project Lead | 2026-02-28 |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Depends On | ADR-001 | Enhanced ADR Format | This ADR follows the enhanced WH(Y) format |
| Depends On | ADR-002 | Frontend Tech Stack | Uses SvelteKit goto() navigation |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-018-A | Model Creation Navigation | Technical Specification | [specs/SPEC-018-A-Model-Creation-Navigation.md](specs/SPEC-018-A-Model-Creation-Navigation.md) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
