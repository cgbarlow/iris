# SPEC-090-A: EA Default Colors Implementation

**ADR:** ADR-090
**Date:** 2026-03-07

## Changes

### 1. converter.py — `build_node_visual()`

Always emit bgColor and borderColor using EA defaults when values are -1:
- `bg == -1` → `bgColor = "#ffffff"` (EA default white)
- `lc == -1` → `borderColor = "#000000"` (EA default black)
- `fc == -1` → no change (font defaults handled by CSS)

### 2. converter.py — `build_edge_visual()`

Always emit lineColor using EA default when value is -1 or None:
- `lineColor is None or lineColor < 0` → `lineColor = "#000000"` (EA default black)

### 3. service.py — Edge stereotype as label

When building edge_data, if the connector has a stereotype but no name:
- Set `edge_data["label"]` to `«{stereotype}»`

## Test Plan

- Unit tests in `test_import_sparx/test_geometry_parser.py` for converter changes
- Unit tests verifying stereotype label logic
