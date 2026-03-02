# SPEC-059-D: Import UI

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-059-D |
| **ADR** | [ADR-059](../ADR-059-SparxEA-Import.md) |
| **Status** | Implemented |

## Overview

Frontend import page for uploading SparxEA .qea files.

## Page: `/routes/import/+page.svelte`

### Features

- **Drag-and-drop zone**: Accepts `.qea` files via drag-and-drop or file picker
- **File validation**: Only `.qea` extension accepted
- **Upload progress**: Visual progress bar with status messages
- **Results summary**: Grid showing models, entities, relationships, diagrams created, and elements/connectors skipped
- **Warnings list**: Scrollable list of import warnings (unmapped types, etc.)
- **Navigation**: "View Models" link to tree view, "Import Another" to reset

### Navigation

Import link added to AppShell sidebar between Entities and Bookmarks.

### API Integration

Uses native `fetch` with `FormData` for multipart upload to `POST /api/import/sparx`.
Auth token injected from auth store.
