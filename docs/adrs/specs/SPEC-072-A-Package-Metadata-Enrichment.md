# SPEC-072-A: Package Metadata Enrichment

**ADR:** [ADR-072](../ADR-072-Package-Metadata-Enrichment.md)
**Status:** Approved
**Date:** 2026-03-04

---

## Overview

Enrich the SparxEA import pipeline to capture all available package metadata and display it in a dedicated package detail page.

## Backend Changes

### Import enrichment (`backend/app/import_sparx/service.py`)

For each package imported, populate `metadata` with:
- `ea_guid` — from `QeaPackage.ea_guid`
- `status`, `stereotype`, `version`, `scope`, `author`, `complexity`, `phase`, `createddate`, `modifieddate`, `gentype` — from the package-type element in `t_object`
- `tagged_values` — array of `{property, value}` objects from `t_objectproperties`

## Frontend Changes

### Package detail page (`frontend/src/routes/packages/[id]/+page.svelte`)

New page with three accordion sections:
1. **Overview**: Name, description, parent package, set
2. **Details**: ID, version, created/modified timestamps, created by
3. **Extended**: All metadata fields (stereotype, version, scope, author, etc.) and tagged values table

Follows the same pattern as the element detail page.

## Acceptance Criteria

1. Import captures ea_guid, all metadata fields, and tagged values for packages
2. Package detail page renders with Overview, Details, and Extended accordions
3. Extended accordion displays all available metadata fields
4. Tagged values render as a Property/Value table
5. Extended accordion shows "No extended metadata available" when empty
