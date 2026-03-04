# SPEC-074-A: C4 Element Types and Rendering

**ADR:** [ADR-074](../ADR-074-C4-Model-Support.md)
**Status:** Approved
**Date:** 2026-03-04

---

## Overview

Add C4 notation support with element types, relationship types, and notation-aware renderers.

## C4 Element Types

| Element | Level | Icon | Description |
|---------|-------|------|-------------|
| person | system_context | 👤 | A user or actor |
| software_system | system_context | ▣ | Internal software system |
| software_system_external | system_context | ▢ | External system |
| container | container | ▤ | Application, data store, or service |
| c4_component | component | ⬡ | Module within a container |
| code_element | code | ▭ | Class, interface, or function |
| deployment_node | deployment | ⬢ | Server, VM, or cloud region |
| infrastructure_node | deployment | ◆ | Load balancer, firewall, DNS |
| container_instance | deployment | ▥ | Running container instance |

## C4 Relationship Type

Single type: `c4_relationship` — labeled arrow with optional technology annotation.

## Visual Design

- Internal systems: blue (#1168bd)
- External systems: grey (#999999)
- Containers: medium blue (#438dd5)
- Components: light blue (#85bbf0)
- Deployment nodes: white with blue border
- All with dark mode variants

## Acceptance Criteria

1. C4 types defined in canvas.ts with C4EntityType union
2. C4 types registered in unified registry
3. DynamicNode dispatches to C4Renderer for c4 notation
4. DynamicEdge dispatches to C4EdgeRenderer for c4 notation
5. C4Renderer renders with level labels and C4 colour scheme
6. Type equivalences include C4 mappings
