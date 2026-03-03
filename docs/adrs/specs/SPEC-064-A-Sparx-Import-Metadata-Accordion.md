# SPEC-064-A: Sparx EA Import Metadata & Accordion Overview

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-064-A |
| **ADR** | ADR-064 |
| **Date** | 2026-03-03 |

---

## 1. Backend — Reader Enhancements

### Dataclass changes

| Dataclass | New fields | SQL source |
|-----------|-----------|------------|
| `QeaPackage` | `Notes: str \| None` | `t_package.Notes` |
| `QeaElement` | `Status, Stereotype, Version: str \| None` | `t_object.Status, Stereotype, Version` |
| `QeaDiagram` | `Notes: str \| None` | `t_diagram.Notes` |
| `QeaConnector` | `Notes: str \| None` | `t_connector.Notes` |

### New dataclass and function

```python
@dataclass
class QeaTaggedValue:
    Object_ID: int
    Property: str | None
    Value: str | None

async def read_tagged_values(db_path: str) -> list[QeaTaggedValue]:
    # SELECT Object_ID, Property, Value FROM t_objectproperties
```

## 2. Backend — Metadata CRUD

Uses existing `metadata TEXT` column in `model_versions` and `entity_versions` (from m002 migration). No new migration needed.

### Schema additions

- `ModelCreate`, `ModelUpdate`, `ModelResponse`, `ModelVersionResponse`: `metadata: dict[str, object] | None = None`
- `EntityCreate`, `EntityUpdate`, `EntityResponse`, `EntityVersionResponse`: `metadata: dict[str, object] | None = None`

### Service changes

- `create_model/entity`: Accept `metadata` param, write `json.dumps(metadata)` to `metadata` column
- `get_model/entity`: Read `mv.metadata`/`ev.metadata`, parse with `json.loads()`, include in response
- `update_model/entity`: Accept `metadata` param, write to new version row
- `list_models/entities`: Include metadata in SELECT and response
- `get_model/entity_versions`: Include metadata in version responses

## 3. Backend — Import Service

- Package `Notes` → model `description`
- Package Status/Stereotype from `t_object WHERE Object_Type='Package'` → model `metadata`
- Element Status/Stereotype/Version/Tagged Values → entity `metadata`
- Diagram `Notes` → diagram model `description`
- Connector `Notes` → relationship `description`

### Metadata JSON structure

```json
{
  "status": "Proposed",
  "stereotype": "DataType",
  "version": "1.0",
  "tagged_values": [
    {"property": "isCollection", "value": "false"}
  ]
}
```

## 4. Frontend — TypeScript Types

Add `metadata?: Record<string, unknown> | null` to: `Model`, `Entity`, `ModelVersion`, `EntityVersion`

## 5. Frontend — Hierarchy Toggle

- Remove Hierarchy button from both canvas toolbars
- Add tree-view SVG icon button left of tab bar (same row as tabs)
- Visible on all three tabs (Overview, Canvas, Version History)
- Uses `aria-pressed` state with primary/muted color toggle

## 6. Frontend — Canvas Toolbar

- Change `flex items-center gap-4` to `flex flex-wrap items-center gap-2 gap-y-2`
- Replace "Focus" text with fullscreen corner-bracket SVG icon with `aria-label="Full screen"`

## 7. Frontend — Accordion Overview

Three accordion groups using `bits-ui` Accordion with `type="multiple"`:

### Summary (open by default)
- Description, Type, Set, Tags (own + inherited)

### Details (collapsed)
- ID, Version, Status (from metadata), Parent (with Change/Remove), Created, Created By, Modified, Modified By, Template

### Extended (collapsed, conditional)
- Only renders if `model.metadata` has `stereotype` or `tagged_values`
- Stereotype, Tagged Values (key-value table)

## 8. Frontend — Smart Default Tab

- Default to `'overview'` when model has no canvas content (no nodes/participants)
- Track `userSelectedTab` flag to preserve manual tab selection across model reloads

## 9. Tests

### Backend reader tests (7)
- Package Notes, Element Status/Stereotype, Diagram Notes, Connector Notes
- Tagged values (count and structure)

### Backend import tests (3)
- Package descriptions populated, entity metadata populated, metadata contains stereotype

### Backend CRUD tests (5)
- Create/get model with metadata, null metadata, create entity with metadata, update preserves metadata
