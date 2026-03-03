# SPEC-068-B: Notation-Aware Rendering

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-068-B |
| **ADR** | [ADR-068](../ADR-068-Canvas-Consolidation.md) |
| **Status** | Draft |
| **Date** | 2026-03-03 |

## Notation Context

UnifiedCanvas sets notation via `setContext('notation', notation)`. DynamicNode/DynamicEdge read it via `getContext('notation')`. This determines which renderer to use.

## Type Equivalences

Cross-notation mapping for element reuse across diagram notations:

```typescript
const TYPE_EQUIVALENCES = {
  component: { simple: 'component', uml: 'component_uml', archimate: 'application_component' },
  actor: { simple: 'actor', archimate: 'business_actor' },
  interface: { simple: 'interface', uml: 'interface_uml', archimate: 'application_interface' },
  package: { simple: 'package', uml: 'package_uml' },
  service: { simple: 'service', archimate: 'application_service' },
};
```

## Renderer Dispatch Logic

```
DynamicNode:
  if type is 'note'|'boundary'|'modelref' → use universal component (NoteNode/BoundaryNode/ModelRefNode)
  else if notation is 'uml' → UmlRenderer
  else if notation is 'archimate' → ArchimateRenderer
  else if notation is 'simple' → SimpleRenderer
  else → BaseNode (fallback)
```
