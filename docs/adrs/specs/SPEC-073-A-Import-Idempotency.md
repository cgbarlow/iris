# SPEC-073-A: Import Idempotency

**ADR:** [ADR-073](../ADR-073-Import-Idempotency.md)
**Status:** Approved
**Date:** 2026-03-04

---

## Overview

Make SparxEA imports idempotent by matching items via ea_guid and skipping duplicates.

## Backend Changes

### GUID index (`_build_guid_index`)
- Scans packages, elements, and diagrams metadata for ea_guid values
- Returns `dict[ea_guid, iris_id]` for the target set

### Import skip logic
- Before creating each package/element/diagram, check GUID index
- If found: reuse existing ID in mapping, increment skip counter
- If not found: create as before

### ea_guid storage
- Elements: store `ea_guid` in metadata dict
- Diagrams: store `ea_guid` in metadata dict
- Packages: already stored (ADR-072)

### Force-delete cascade
- `force_delete_set()` now cascades packages and package_relationships

## Frontend Changes
- ImportSummary includes `packages_skipped` and `diagrams_skipped`
- Import results page shows skip count cards

## Acceptance Criteria
1. Second import of same .qea file creates zero new items
2. Skip counts reported in ImportSummary
3. Force-delete set removes packages and package_relationships
4. Frontend displays skip counts
