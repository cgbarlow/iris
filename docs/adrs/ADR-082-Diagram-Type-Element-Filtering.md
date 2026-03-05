# ADR-082: Diagram-Type Element Filtering

## Status
Accepted

## Date
2026-03-05

## What
Filter the element types shown in the canvas EntityDialog based on the current diagram type, so users only see relevant element types for the diagram they are working on. Also adds 6 new diagram types (Use Case, State Machine, System Context, Container, Motivation, Strategy) and 2 quick-win notation mappings.

## Why
When adding elements on a diagram canvas, users currently see ALL entity types for the selected notation regardless of diagram type. For example, on a UML Class diagram they see `use_case`, `activity`, `node` etc., which are irrelevant to class diagrams. This creates cognitive overhead and increases the chance of placing inappropriate elements.

Additionally, several standard diagram types are missing from the registry:
- UML: Use Case and State Machine diagrams
- C4: System Context and Container diagrams
- ArchiMate: Motivation and Strategy viewpoint diagrams

## How
1. **Migration m023**: Adds 6 new diagram types to the registry with notation mappings, plus adds `archimate` to `roadmap` and `c4` to `sequence` as quick-win mappings.
2. **Filter constants**: Three mapping objects (UML, ArchiMate, C4) define which element types/layers/levels are appropriate for each diagram type. `null` means no filtering (show all).
3. **EntityDialog filtering**: New `diagramType` prop enables filtering of the type dropdown. ArchiMate constrains the Layer dropdown; C4 constrains the Scope dropdown; UML directly filters type keys.
4. **Override toggle**: A "Show all types" checkbox lets users bypass filtering when needed.
5. **Simple notation**: No filtering applied (only 7 types, all generally applicable).

## Alternatives Considered
- **Server-side filtering**: Rejected — adds API complexity and latency for what is purely a UX concern. The filter rules are static and belong in the frontend.
- **Hard block (no override)**: Rejected — users may legitimately need to place unconventional elements. The toggle provides flexibility.
- **Per-diagram custom type lists**: Rejected — too much configuration overhead. Static per-diagram-type rules cover 95% of cases.

## Consequences
- Users see only relevant element types by default, reducing errors
- Power users can still access all types via the override toggle
- 6 new diagram types expand coverage for UML, C4, and ArchiMate workflows
- DiagramDialog fallback mapping updated to include new types
