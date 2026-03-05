# ADR-083: Comprehensive Seed Diagrams

## Status
Accepted

## Date
2026-03-05

## What
Expand the example seed to create diagrams covering all 31 valid (diagram_type, notation) permutations in the registry, reorganise the package hierarchy by notation, and add notation-appropriate elements and relationships — all describing the Iris system itself.

## Why
The current v2 seed creates only 7 diagrams covering 4 of 31 valid combinations. New users see a sparse example set that does not demonstrate the full range of diagram types and notations available. A comprehensive seed provides:
- Out-of-the-box demonstration of every diagram type
- Visual examples of each notation's element styles
- A realistic package hierarchy organised by notation
- Self-documenting architecture (Iris describing itself)

## How
1. Reorganise 4-package hierarchy into 5 packages grouped by notation (Simple, UML, ArchiMate, C4) under root "Iris"
2. Add ~40 new elements across UML (12), ArchiMate (18), and C4 (10) notations
3. Add ~30 new relationships for UML, ArchiMate, and C4 notations
4. Create 32 diagrams (31 permutations + 1 overview) with notation-appropriate nodes and edges
5. Implement v2→v3 seed migration using existing deterministic ID pattern
6. Use _grid_nodes helper to reduce diagram builder boilerplate

## Alternatives Considered
- **Keep minimal seed, add optional "demo pack" import**: Rejected — adds import complexity and doesn't provide immediate out-of-box experience
- **Auto-generate diagrams from registry at runtime**: Rejected — diagrams need curated, meaningful content to be useful examples
- **Separate seed modules per notation**: Rejected — adds file sprawl; single module with clear sections is more maintainable

## Consequences
- Every valid diagram type/notation combination has a working example
- New users see the full capability of Iris immediately
- Seed data grows from ~7KB to ~40KB but remains fast (single transaction)
- v2→v3 migration clears old seed and reseeds cleanly
