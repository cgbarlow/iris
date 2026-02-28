# SPEC-011-C: Sequence Diagram Integration

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-011-C |
| **ADR Reference** | [ADR-011: Canvas Integration and Testing Strategy](../ADR-011-Canvas-Integration-Testing.md) |
| **Date** | 2026-02-28 |
| **Status** | Active |

---

## Overview

This specification defines how the existing SequenceDiagram component is integrated into the model canvas route. When a model has `model_type === 'sequence'`, the route renders SequenceDiagram instead of ModelCanvas or BrowseCanvas.

---

## Conditional Rendering

The model canvas route checks `model.model_type` and renders the appropriate component:

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

For the browse route, the same conditional applies with `readonly` mode enabled where applicable. SequenceDiagram is inherently read-only in browse mode (no editing of participants or messages).

---

## SequenceDiagramData Structure

The `model.data` field for sequence models is parsed as `SequenceDiagramData`:

```typescript
interface Participant {
    id: string;
    name: string;
    type: 'actor' | 'system' | 'database' | 'service';
}

interface Message {
    id: string;
    from: string;       // participant id
    to: string;         // participant id
    label: string;
    type: 'sync' | 'async' | 'reply' | 'create' | 'destroy';
    order: number;       // sequence position
}

interface Activation {
    id: string;
    participantId: string;
    startMessage: string;  // message id
    endMessage: string;    // message id
}

interface SequenceDiagramData {
    participants: Participant[];
    messages: Message[];
    activations: Activation[];
}
```

---

## Default Empty Sequence Data

When a new sequence model is created and has no `data` field (or `data` is null), the canvas initialises with a default empty structure:

```typescript
const defaultSequenceData: SequenceDiagramData = {
    participants: [],
    messages: [],
    activations: []
};
```

The SequenceDiagram component renders an empty canvas with instructions for adding the first participant.

---

## Data Parsing

On route mount:

1. Fetch model via `GET /api/models/{id}`
2. Check `model.model_type`
3. If `'sequence'`, parse `model.data` as `SequenceDiagramData`
4. Handle missing or null data by falling back to `defaultSequenceData`
5. Pass parsed data to SequenceDiagram component

```typescript
let sequenceData: SequenceDiagramData;

if (model.model_type === 'sequence') {
    sequenceData = model.data
        ? (model.data as SequenceDiagramData)
        : { participants: [], messages: [], activations: [] };
}
```

---

## Persistence

### Save

- Trigger: same as other canvas types (Ctrl+S or save button)
- Request: `PUT /api/models/{id}`
- Payload: `{ data: sequenceData }` where `sequenceData` contains `participants`, `messages`, `activations`

### Load

- On route mount, parse `model.data` as `SequenceDiagramData`
- SequenceDiagram component restores from parsed data

---

## Browse Mode

When accessed via the browse route:

- SequenceDiagram renders in read-only mode
- Participants and messages are displayed but cannot be edited
- No add/delete/reorder operations available
- Pan and zoom (if supported by the component) remain enabled

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| Sequence model renders SequenceDiagram | Create a sequence model; verify SequenceDiagram component renders, not ModelCanvas |
| Empty sequence model shows default state | Create a new sequence model with no data; verify empty canvas with instructions |
| Sequence data round-trips through save/load | Add participants and messages, save, reload; verify data is preserved |
| Browse mode is read-only | Navigate to browse route for sequence model; verify no editing controls |
| Non-sequence models do not render SequenceDiagram | Open a simple model; verify ModelCanvas renders, not SequenceDiagram |

---

*This specification implements [ADR-011](../ADR-011-Canvas-Integration-Testing.md).*
