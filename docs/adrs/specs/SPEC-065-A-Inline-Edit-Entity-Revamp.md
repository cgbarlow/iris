# SPEC-065-A: Inline Edit, Entity Detail Revamp, Extended Import

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-065-A |
| **ADR** | ADR-065 |
| **Date** | 2026-03-03 |

---

## 1. Backend — Reader Enhancements

### QeaElement — add 9 fields

| Field | SQL source | Type |
|-------|-----------|------|
| `Scope` | `t_object.Scope` | `str \| None` |
| `Abstract` | `t_object.Abstract` | `str \| None` |
| `Persistence` | `t_object.Persistence` | `str \| None` |
| `Author` | `t_object.Author` | `str \| None` |
| `Complexity` | `t_object.Complexity` | `str \| None` |
| `Phase` | `t_object.Phase` | `str \| None` |
| `CreatedDate` | `t_object.CreatedDate` | `str \| None` |
| `ModifiedDate` | `t_object.ModifiedDate` | `str \| None` |
| `GenType` | `t_object.GenType` | `str \| None` |

### QeaAttribute — add 6 fields

| Field | SQL source | Type |
|-------|-----------|------|
| `Notes` | `t_attribute.Notes` | `str \| None` |
| `Default` | `t_attribute."Default"` | `str \| None` |
| `LowerBound` | `t_attribute.LowerBound` | `str \| None` |
| `UpperBound` | `t_attribute.UpperBound` | `str \| None` |
| `Stereotype` | `t_attribute.Stereotype` | `str \| None` |
| `Scope` | `t_attribute.Scope` | `str \| None` |

Note: `Default` is a SQL reserved word and must be quoted in queries.

---

## 2. Backend — Import Service Enhancements

### Entity metadata expansion

Add to `em` dict (only when non-null/non-default):
- `scope` ← `elem.Scope`
- `abstract` ← `True` only if `elem.Abstract == "1"`
- `persistence` ← `elem.Persistence`
- `author` ← `elem.Author`
- `complexity` ← `elem.Complexity` (skip if default "2")
- `phase` ← `elem.Phase`
- `created_date` ← `elem.CreatedDate`
- `modified_date` ← `elem.ModifiedDate`
- `gen_type` ← `elem.GenType`

### Attribute format change

Change from string list to rich object list:
```python
entity_data["attributes"] = [
    {"name": a.Name or "", "type": a.Type or "", "notes": a.Notes,
     "default": a.Default, "lower_bound": a.LowerBound,
     "upper_bound": a.UpperBound, "stereotype": a.Stereotype, "scope": a.Scope}
    for a in obj_attrs
]
```

---

## 3. Frontend — Model Detail Tab Rename

- Tab label: `"Overview"` → `"Details"`
- `activeTab` union type: `'overview'` → `'details'`
- All conditionals and smart default logic updated

---

## 4. Frontend — Model Inline Editing

### Remove
- `showEditDialog` state, `handleEdit()` (replaced), `<ModelDialog mode="edit">` instance

### Add state
- `editingOverview: boolean` — inline edit mode active
- `overviewDirty: boolean` — unsaved changes exist
- `savingOverview: boolean` — save in progress
- `editName, editDescription, editTags: string[]` — edit buffers
- `editIsTemplate: boolean` — template toggle buffer

### Toolbar above accordion
- Browse mode: Blue "Edit Metadata" button
- Edit mode: Save (disabled until dirty) + Discard + "Unsaved changes" indicator

### Inline editable fields (Summary group)
- Name: `<input>` (editable)
- Description: `<textarea>` (editable)
- Tags: `<TagInput>` (editable)
- Type, Set: read-only

### Inline editable fields (Details group)
- Template: `<input type="checkbox">` (editable)
- All others: read-only

### Functions
- `enterOverviewEdit()` — populate edit buffers from model
- `saveMetadata()` — DOMPurify sanitize, PUT with If-Match, sync tags, reload
- `discardOverviewChanges()` — reset buffers and exit edit mode

---

## 5. Frontend — Entity Detail Revamp

### Entity clone button
POST `/api/entities` with same type + `" (Copy)"` name suffix, navigate to new entity.

### Accordion layout
Import `{ Accordion } from 'bits-ui'`. Config: `type="single" value="summary"`.

| Group | Default | Fields |
|-------|---------|--------|
| Summary | open | Description, Type, Set, Tags |
| Details | collapsed | ID, Version, Created, Created By, Modified, Modified By |
| Extended | collapsed | metadata fields, tagged values table, fallback text |

### Inline editing
Same pattern as models: "Edit Metadata" button, edit buffers, DOMPurify sanitize, PUT with If-Match, tag sync.

### Remove
- `showEditDialog` state, Edit button from header, `<EntityDialog mode="edit">`

---

## 6. Canvas Backward Compatibility

ClassNode and AbstractClassNode: update `attributes` type to `(string | { name: string; type: string })[]` and render accordingly.

---

## 7. Tests

### Backend — 7 new tests

| Test class | Test | Assertion |
|-----------|------|-----------|
| TestReaderMetadata | `test_read_elements_has_scope` | Elements with non-null Scope exist |
| TestReaderMetadata | `test_read_elements_has_created_modified_date` | Elements with CreatedDate/ModifiedDate exist |
| TestReaderMetadata | `test_read_elements_has_abstract` | Elements with Abstract field exist |
| TestReaderMetadata | `test_read_attributes_has_notes` | Attributes with Notes field exist |
| TestImportMetadata | `test_import_entity_metadata_has_scope` | Imported entity metadata contains `scope` |
| TestImportMetadata | `test_import_entity_metadata_has_created_date` | Imported entity metadata contains `created_date` |
| TestImportMetadata | `test_import_attributes_include_notes` | Imported attributes are dicts with `notes` key |
