# ADR-064: Sparx EA Import Metadata & Accordion Overview

## Proposal: Thread SparxEA metadata through import pipeline, redesign model overview with accordion groups

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-064 |
| **Initiative** | SparxEA Import Enrichment & Model Detail UX |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-03 |
| **Status** | Approved |
| **Dependencies** | ADR-058 (SparxEA Integration), ADR-063 (Tree Explorer) |

---

## ADR (WH(Y) Statement format)

**In the context of** the SparxEA import pipeline discarding valuable metadata from `.qea` files (package Notes, element Status/Stereotype/Version/Tagged Values, diagram Notes, connector Notes) while the existing `metadata TEXT` column in `model_versions` and `entity_versions` tables remains unused, and the model overview tab presenting a flat definition list that doesn't scale well with additional fields,

**facing** loss of important architectural metadata during import, inability to display extended properties like stereotypes and tagged values, the Hierarchy button being visible only on the Canvas tab, toolbar buttons getting squished on narrow windows, and models defaulting to Canvas tab even when they have no canvas content,

**we decided for** enriching the SparxEA reader to extract Notes/Status/Stereotype/Version/Tagged Values, threading metadata through model and entity CRUD services using the existing `metadata` column, redesigning the overview tab with bits-ui Accordion groups (Summary, Details, Extended), moving the Hierarchy toggle to a shared position left of the tab bar, adding `flex-wrap` to canvas toolbars, replacing the Focus button text with a fullscreen icon, and defaulting to the Overview tab when a model has no canvas content,

**and neglected** creating a new database migration for metadata (the existing unused column suffices), using a custom accordion implementation (bits-ui is already installed), and keeping the flat definition list layout (doesn't accommodate the additional metadata fields well),

**to achieve** full preservation of SparxEA metadata through the import pipeline, rich display of extended properties in the model overview, consistent hierarchy navigation across all tabs, better toolbar responsiveness on narrow screens, and smarter default tab selection,

**accepting that** the accordion adds visual complexity to the overview tab and the metadata JSON structure is loosely typed.

---

## Decisions

1. **Reader enhancements**: Add `Notes` to `QeaPackage`/`QeaDiagram`/`QeaConnector`, add `Status`/`Stereotype`/`Version` to `QeaElement`, create `read_tagged_values()` function
2. **Metadata CRUD**: Thread `metadata: dict | None` through model and entity create/get/update/list services using existing `metadata TEXT` column in version tables
3. **Import enrichment**: Pass package `Notes` as model description, build metadata dicts from element Status/Stereotype/Version/Tagged Values, pass connector `Notes` as relationship description, pass diagram `Notes` as model description
4. **Accordion overview**: Replace flat `<dl>` with bits-ui `Accordion.Root` having three groups: Summary (open by default), Details (collapsed), Extended (collapsed, conditional on metadata presence)
5. **Hierarchy toggle**: Move from canvas toolbars to shared position left of tab bar using tree-view SVG icon, visible on all three tabs
6. **Responsive toolbars**: Add `flex-wrap` to canvas toolbar containers for narrow window support
7. **Fullscreen icon**: Replace "Focus" text label with standard fullscreen corner-bracket SVG icon
8. **Smart default tab**: Default to Overview when model has no canvas content; track `userSelectedTab` to preserve manual selection

---

## Specification

See [SPEC-064-A](specs/SPEC-064-A-Sparx-Import-Metadata-Accordion.md).
