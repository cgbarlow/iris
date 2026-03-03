# SPEC-069-A: Note and Boundary Import Label Derivation

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-069-A |
| **ADR** | [ADR-069](../ADR-069-Note-Boundary-Import-Label-Derivation.md) |
| **Status** | Draft |
| **Date** | 2026-03-03 |

---

## Overview

SparxEA Note elements store content in the `Note` HTML column and have `Name=NULL`. The current import uses `elem.Name or f"Element {elem.Object_ID}"` which produces generic names. This spec adds a utility to derive meaningful labels from HTML content and ensures canvas nodes always have descriptions.

## Changes

### 1. `derive_note_label(html_content, fallback)` utility

**Location:** `backend/app/import_sparx/service.py`

**Behaviour:**
- Strip all HTML tags from `html_content`
- Take the first non-empty line
- Truncate to 60 characters (append "..." if truncated)
- Return `fallback` if content is None or empty after stripping

### 2. Entity name derivation in import loop

For elements with `iris_type` in `('note', 'boundary')` and `elem.Name` is None/empty:
- Call `derive_note_label(elem.Note, f"Note {elem.Object_ID}")` for notes
- Call `derive_note_label(elem.Note, f"Boundary {elem.Object_ID}")` for boundaries

### 3. Canvas node description population

In the diagram node construction loop, always populate `description` from the element's `Note` content (if available), regardless of element type.

## Acceptance Criteria

1. `derive_note_label` strips HTML tags and truncates correctly
2. `derive_note_label` returns fallback for None/empty input
3. Note entities get content-derived names (not "Element N")
4. Boundary entities get meaningful names
5. All canvas nodes from import have `description` populated when element has Note content
