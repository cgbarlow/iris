# ADR-061: Sets Page & Dashboard Integration

## Proposal: Add Dedicated Sets Page, Dashboard Set Filtering, and Set Editing

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-061 |
| **Initiative** | Sets UI & Dashboard Integration |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-02 |
| **Status** | Approved |
| **Dependencies** | ADR-060 (Sets, Batch Operations & Pagination) |

---

## ADR (WH(Y) Statement format)

**In the context of** Iris having sets infrastructure (ADR-060) with CRUD API and set selector dropdowns on list pages but lacking a dedicated management interface,

**facing** the inability to browse sets at a glance, filter the dashboard by set, manage set thumbnails, or force-delete sets with contents from the UI,

**we decided for** adding a `/sets` page for browsing and managing sets with list/gallery views, integrating set-scoped filtering into the dashboard via URL parameters, creating a `/sets/[id]` edit page with thumbnail management and force-delete capability, and adding sidebar navigation for sets,

**and neglected** inline editing on the sets list (too complex for initial release), drag-and-drop reordering of sets (sets are alphabetically sorted), and set-scoped search (global search is sufficient at current scale),

**to achieve** a complete set management workflow where users can browse, create, filter by, edit, and delete sets from a dedicated UI,

**accepting that** set thumbnails add a new migration (m013) with BLOB storage, force-delete is destructive and requires confirmation, and the dashboard URL changes when filtering by set.

---

## Decisions

1. **Dedicated `/sets` page**: List and gallery views with client-side search, view mode persistence, edit mode toggle
2. **Dashboard integration**: `?set_id=` URL parameter filters entity/model counts; Sets card shows count or active filter with reset link
3. **Set edit page**: `/sets/[id]` with name, description, thumbnail management (none/model/image), and force-delete
4. **Set thumbnails**: Three-column migration (m013): `thumbnail_source`, `thumbnail_model_id`, `thumbnail_image` BLOB
5. **Force delete**: `DELETE /api/sets/{id}?force=true` soft-deletes all contents and the set; returns counts
6. **Thumbnail endpoints**: `POST /api/sets/{id}/thumbnail` for upload, `GET /api/sets/{id}/thumbnail` for retrieval
7. **Sidebar navigation**: Sets added between Entities and Import; `aria-current` uses `startsWith` for sub-pages

---

## References

- SPEC-061-A: Sets Page & Dashboard Integration specification
- ADR-060: Sets, Batch Operations & Pagination
