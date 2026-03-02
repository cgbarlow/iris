# SPEC-057-A: UML New Node Types

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-057-A |
| **ADR** | [ADR-057](../ADR-057-UML-Type-Expansion.md) |
| **Status** | Accepted |
| **Date** | 2026-03-02 |

---

## Overview

Add 5 new UML node types and 1 new edge type to the Full View UML canvas, expanding coverage of standard UML structural diagram elements.

## New Node Types

| Type Key | Component | Icon | Stereotype/Tag | Compartments | aria-label |
|----------|-----------|------|----------------|--------------|------------|
| `interface_uml` | InterfaceNode.svelte | ◯ | `<<interface>>` | Operations only | `{label}, Interface` |
| `enumeration` | EnumNode.svelte | ▤ | `<<enumeration>>` | Literals (string[]) | `{label}, Enumeration` |
| `abstract_class` | AbstractClassNode.svelte | ▭ | `{abstract}` | Attributes + Operations | `{label}, Abstract Class` |
| `component_uml` | UmlComponentNode.svelte | ⊞ | None | None | `{label}, Component` |
| `package_uml` | UmlPackageNode.svelte | ▤ | None | None (tab-folder style) | `{label}, Package` |

## New Edge Type

| Type Key | Component | Style | aria-label |
|----------|-----------|-------|------------|
| `usage` | UsageEdge.svelte | Dashed (stroke-dasharray: 6 3) | `Usage` |

## Type System Changes

### `UmlEntityType` (canvas.ts)

Add to union: `'interface_uml' | 'enumeration' | 'abstract_class' | 'component_uml' | 'package_uml'`

### `UML_ENTITY_TYPES` array (canvas.ts)

```ts
{ key: 'interface_uml', label: 'Interface', icon: '◯', description: 'Contract specifying operations' },
{ key: 'enumeration', label: 'Enumeration', icon: '▤', description: 'Set of named literal values' },
{ key: 'abstract_class', label: 'Abstract Class', icon: '▭', description: 'Class that cannot be instantiated' },
{ key: 'component_uml', label: 'Component', icon: '⊞', description: 'Modular deployable unit' },
{ key: 'package_uml', label: 'Package', icon: '▤', description: 'Namespace grouping container' },
```

### `UmlRelationshipType` (canvas.ts)

Add `'usage'` to the union type.

### `UML_RELATIONSHIP_TYPES` array (canvas.ts)

```ts
{ key: 'usage', label: 'Usage', description: 'Source uses target' },
```

## Node Registry (uml/nodes/index.ts)

```ts
interface_uml: InterfaceNode,
enumeration: EnumNode,
abstract_class: AbstractClassNode,
component_uml: UmlComponentNode,
package_uml: UmlPackageNode,
```

## Edge Registry (uml/edges/index.ts)

```ts
usage: UsageEdge,
```

## Component Design Notes

- All node components use Svelte 5 runes (`$props`)
- All node components include Handle elements at 5 positions: Top, Bottom, Left, Right, and Center (per ADR-053)
- InterfaceNode and EnumNode display stereotype text (`<<interface>>`, `<<enumeration>>`) above the label
- AbstractClassNode displays `{abstract}` tag and renders the label in italic
- UmlComponentNode places the icon in the top-right corner (UML component notation)
- UmlPackageNode uses tab-folder CSS notation with a small tab on the top-left
- UsageEdge follows the same pattern as DependencyEdge (dashed bezier path with reconnect anchors)

## Acceptance Criteria

1. All 5 new node types render correctly in the UML canvas
2. The usage edge type renders as a dashed line
3. All new types appear in `UML_ENTITY_TYPES` and `UML_RELATIONSHIP_TYPES` arrays
4. All new components include proper aria-label attributes
5. All new node components include Handle elements at Top/Bottom/Left/Right/Center
6. TypeScript types are updated (`UmlEntityType`, `UmlRelationshipType`)
7. Node and edge registries include all new components
