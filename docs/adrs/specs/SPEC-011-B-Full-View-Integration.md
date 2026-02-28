# SPEC-011-B: Full View Integration

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-011-B |
| **ADR Reference** | [ADR-011: Canvas Integration and Testing Strategy](../ADR-011-Canvas-Integration-Testing.md) |
| **Date** | 2026-02-28 |
| **Status** | Active |

---

## Overview

This specification defines the FullViewCanvas.svelte orchestrator component and the mapping from model types to canvas components. It covers how UML and ArchiMate model types are rendered using the appropriate node and edge type registries, and how EntityDialog and RelationshipDialog adapt their options based on model type.

---

## FullViewCanvas.svelte

### Purpose

FullViewCanvas is an orchestrator component that wraps Svelte Flow and selects the appropriate node type and edge type registries based on the `viewType` prop.

### Props

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `viewType` | `'uml' \| 'archimate'` | Yes | Determines which node/edge type registries to use |
| `nodes` | `Node[]` | Yes | Initial nodes from model data |
| `edges` | `Edge[]` | Yes | Initial edges from model data |
| `readonly` | `boolean` | No | If true, disables editing (for browse mode) |

### Registry Selection

```
if viewType === 'uml':
    nodeTypes = umlNodeTypes
    edgeTypes = umlEdgeTypes
elif viewType === 'archimate':
    nodeTypes = archimateNodeTypes
    edgeTypes = archimateEdgeTypes
```

FullViewCanvas passes the selected registries to the underlying Svelte Flow instance. All other canvas behaviour (pan, zoom, select, connect) is identical to ModelCanvas.

---

## Model Type to Canvas Component Mapping

The route that renders a model canvas must select the correct component based on `model.model_type`:

| `model.model_type` | Component | Props |
|--------------------|-----------|-------|
| `simple` | ModelCanvas | nodes, edges |
| `component` | ModelCanvas | nodes, edges |
| `sequence` | SequenceDiagram | sequenceData (parsed from model.data) |
| `uml` | FullViewCanvas | viewType='uml', nodes, edges |
| `archimate` | FullViewCanvas | viewType='archimate', nodes, edges |

### Route Rendering Logic

```svelte
{#if model.model_type === 'sequence'}
    <SequenceDiagram data={sequenceData} />
{:else if model.model_type === 'uml'}
    <FullViewCanvas viewType="uml" {nodes} {edges} />
{:else if model.model_type === 'archimate'}
    <FullViewCanvas viewType="archimate" {nodes} {edges} />
{:else}
    <ModelCanvas {nodes} {edges} />
{/if}
```

The `simple` and `component` types both fall through to ModelCanvas (the default case).

---

## EntityDialog Adaptation

EntityDialog must present the correct set of entity types based on the model type. The available types are passed as a prop.

| Model Type | Entity Types Constant | Example Types |
|-----------|----------------------|---------------|
| simple | `SIMPLE_ENTITY_TYPES` | component, service, interface, package, actor, database, queue |
| component | `SIMPLE_ENTITY_TYPES` | component, service, interface, package, actor, database, queue |
| uml | `UML_ENTITY_TYPES` | class, interface, abstract-class, enum, package, object, component, node |
| archimate | `ARCHIMATE_ENTITY_TYPES` | business-actor, business-role, business-process, application-component, application-service, technology-node, technology-artifact |

EntityDialog receives `availableTypes` as a prop and renders a selector filtered to those types. The selected type is passed through to the canvas as the node type.

---

## RelationshipDialog Adaptation

RelationshipDialog must present the correct set of relationship types based on the model type.

| Model Type | Relationship Types | Example Types |
|-----------|-------------------|---------------|
| simple / component | Simple relationships | association, dependency, composition, aggregation, generalization |
| uml | UML relationships | association, directed-association, dependency, generalization, realization, composition, aggregation |
| archimate | ArchiMate relationships | composition, aggregation, assignment, realization, serving, access, influence, triggering, flow, specialization |

RelationshipDialog receives `availableRelationshipTypes` as a prop and renders a selector filtered to those types.

---

## Browse Mode

FullViewCanvas supports `readonly` mode for browse routes. When `readonly` is true:

- Drag is disabled
- Connect is disabled
- Node click opens EntityDetailPanel (same behaviour as BrowseCanvas)
- Pan and zoom remain enabled

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| UML model renders with UML node types | Open a UML model; verify class/interface nodes render correctly |
| ArchiMate model renders with ArchiMate node types | Open an ArchiMate model; verify business-actor/application-component nodes render correctly |
| EntityDialog shows correct types per model | Open EntityDialog in UML model; verify UML types shown, not simple types |
| RelationshipDialog shows correct types per model | Connect two nodes in ArchiMate model; verify ArchiMate relationship types shown |
| ModelDialog model types route correctly | Create each of the 5 model types; verify each renders the correct canvas component |

---

*This specification implements [ADR-011](../ADR-011-Canvas-Integration-Testing.md).*
