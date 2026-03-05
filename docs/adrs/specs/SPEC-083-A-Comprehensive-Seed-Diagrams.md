# SPEC-083-A: Comprehensive Seed Diagrams

**ADR Reference**: [ADR-083](../ADR-083-Comprehensive-Seed-Diagrams.md)

## Overview

Expand `backend/app/seed/example_models.py` to create one diagram for every valid (diagram_type, notation) permutation in the registry, reorganised into notation-based packages.

## Package Hierarchy (5 packages)

```
Iris (pkg-0, root)
├── Simple Notation (pkg-1)    — 10 diagrams
├── UML Notation (pkg-2)       — 8 diagrams
├── ArchiMate Notation (pkg-3) — 7 diagrams
├── C4 Notation (pkg-4)        — 6 diagrams
└── [Iris System Overview at root level]
```

## Diagrams (32 total)

31 permutations covering all valid (diagram_type, notation) pairs plus 1 System Overview at root level.

### Simple Notation (10)
component, sequence, deployment, process, roadmap, free_form, use_case, state_machine, system_context, container

### UML Notation (8)
component, sequence, class, deployment, process, free_form, use_case, state_machine

### ArchiMate Notation (7)
component, deployment, process, roadmap, free_form, motivation, strategy

### C4 Notation (6)
component, sequence, deployment, free_form, system_context, container

## Elements (55 total)

- Simple: 15 existing (indices 0-14)
- UML: 12 new (indices 15-26) — class, interface_uml, abstract_class, enumeration, use_case, state
- ArchiMate: 18 new (indices 27-44) — business, application, technology, motivation, strategy layers
- C4: 10 new (indices 45-54) — person, software_system, container, c4_component

All elements tagged ['iris', 'example']. Notation set per element.

## Relationships (50 total)

- Simple: 20 existing (indices 0-19)
- UML: 10 new (indices 20-29) — association, dependency, realization, generalization, composition
- ArchiMate: 12 new (indices 30-41) — serving, flow, assignment, access, archimate_composition
- C4: 8 new (indices 42-49) — c4_relationship with technology labels

## Idempotency (v2→v3 Migration)

- Check for pkg-4 (C4 Notation package) as v3 marker
- If root exists but not pkg-4: v2→v3 upgrade (clear old seed, reseed)
- If both exist: already v3, skip
- If neither: fresh seed

## Test Plan

- Assert 5 packages in Default set
- Assert 32 diagrams
- Assert 55 elements
- Assert 50 relationships
- Assert correct diagram_type and notation per diagram
- Assert all elements have 'example' tag
- Assert v2→v3 migration works
- Assert idempotency (run twice, no duplicates)

## Additional Changes

- Padlock icon for Locks admin nav item
- Bookmarks moved above Import in nav order
