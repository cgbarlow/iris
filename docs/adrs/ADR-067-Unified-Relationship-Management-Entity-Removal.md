# ADR-067: Unified Relationship Management & Entity Removal from Canvas

## Proposal: Create relationships from both canvas and Relationships tab, with "Add to canvas?" prompt; provide node removal dialog with cascade entity deletion option

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-067 |
| **Initiative** | Unified Relationship Management |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-03 |
| **Status** | Approved |
| **Dependencies** | ADR-066 (Import All Skipped Items, Model Relationships) |

---

## ADR (WH(Y) Statement format)

**In the context of** the Relationships tab showing relationships read-only with no way to create them, modelref-to-modelref canvas connections creating visual edges but no backend model_relationships records, no visible button to remove a node from the canvas (only keyboard Delete), and no option for cascade deletion of entities across all models,

**facing** incomplete relationship management (users must use canvas connections for entity relationships but have no way to create model relationships from the tab), orphaned visual edges that don't persist as backend records for modelref connections, poor discoverability of node removal (keyboard-only Delete), and inability to remove an entity from all models at once when it's no longer needed,

**we decided for** enabling relationship creation from both canvas and Relationships tab with an "Add to canvas?" prompt, auto-creating model_relationships when modelref-to-modelref edges are saved on canvas, adding a visible "Remove" button in the canvas toolbar, implementing a two-option NodeDeleteDialog ("Remove from this model" vs "Delete entity and all relationships"), and adding cascade entity deletion (`?cascade=true`) that removes the entity from all model canvases and soft-deletes all relationships,

**and neglected** implementing drag-and-drop relationship creation from the tab (overengineered for current needs), automatic canvas updates when relationships are deleted from the tab (would require complex bidirectional sync), and hard-deleting entities on cascade (soft-delete preserves audit trail),

**to achieve** complete relationship management from both canvas and tab interfaces, consistent backend persistence for all relationship types, discoverable node removal with clear consequences, and safe cascade deletion with proper cleanup,

**accepting that** model relationship "Add to canvas" only adds the target as a modelref node (no edge drawn since the current model has no self-node), the NodeDeleteDialog adds a new component, and cascade deletion modifies canvas data in all affected models which creates new model versions.

---

## Decisions

1. **Auto-create model_relationships from canvas**: When `update_model()` saves canvas data containing edges between modelref nodes, automatically create `model_relationships` rows (mirroring existing entity relationship auto-creation)
2. **Frontend modelref connection handling**: `handleRelationshipSave()` creates `POST /api/models/{id}/relationships` when both connected nodes are modelrefs
3. **Add Entity Relationship from tab**: Multi-step flow using EntityPicker (source → target) then RelationshipDialog, followed by "Add to canvas?" prompt
4. **Add Model Relationship from tab**: ModelPicker then RelationshipDialog flow, followed by "Add to canvas?" prompt
5. **"Add to canvas?" prompt**: After creating relationship from tab, offer to add nodes/edges to canvas; for model relationships only target modelref node is added (documented limitation)
6. **EntityPicker/ModelPicker title props**: Add optional `title` and `subtitle` props for reuse in different contexts (DRY)
7. **Cascade entity deletion**: New `cascade_delete_entity()` service removes entity from all model canvases, soft-deletes all relationships, and soft-deletes the entity
8. **`?cascade=true` query param**: Existing DELETE endpoint gains optional cascade parameter
9. **NodeDeleteDialog component**: Two-option dialog for node removal; cascade option only shown for entity nodes, not modelref nodes
10. **Keyboard Delete opens dialog**: Both Delete key and toolbar button open NodeDeleteDialog instead of direct removal

---

## Specification

See [SPEC-067-A](specs/SPEC-067-A-Unified-Relationships-Entity-Removal.md).
