# SPEC-051-A: Sequence Diagram Browse Mode

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-051-A |
| **ADR Reference** | [ADR-051: Sequence Diagram Browse Mode](../ADR-051-Sequence-Diagram-Browse-Mode.md) |
| **Date** | 2026-03-01 |
| **Status** | Accepted |

---

## Overview

This specification details the enhancement of the sequence diagram component to support browse-mode interaction. Participants with linked entities become clickable, triggering a callback that enables the parent page to display entity details in the `EntityDetailPanel`. A synthetic `CanvasNode` is constructed from participant data to satisfy the panel's expected input type.

---

## A. Participant Type Extension

### entityId Field

The `Participant` type is extended with an optional `entityId` field that links the participant to an entity in the data model.

**File:** `src/lib/canvas/sequence/types.ts` (or equivalent)

```typescript
export interface Participant {
    id: string;
    name: string;
    type?: string; // e.g., 'actor', 'system', 'component'
    // Browse mode entity linking (WP-7)
    entityId?: string;
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `entityId` | `string` | No | The linked entity ID for browse-mode navigation |

When `entityId` is present, the participant is interactive in browse mode. When absent, the participant is display-only and clicking has no effect.

### Data Source

The `entityId` is populated when the sequence diagram is saved as part of a model's canvas data. Entity linking occurs in edit mode (e.g., when creating a participant from an existing entity via the entity picker).

---

## B. onparticipantselect Callback

### SequenceDiagram Props

**File:** `src/lib/canvas/sequence/SequenceDiagram.svelte`

```typescript
interface Props {
    // ... existing props ...
    participants: Participant[];
    messages: Message[];
    editable?: boolean;
    // Browse mode callback (WP-7)
    onparticipantselect?: (participant: Participant) => void;
}
```

### Participant Click Handler

```typescript
function handleParticipantClick(participant: Participant) {
    if (!participant.entityId) return;
    onparticipantselect?.(participant);
}
```

### Participant SVG Rendering Update

The participant header box becomes clickable when `entityId` is present and `onparticipantselect` is provided:

```svelte
<!-- Participant header -->
<g
    class="participant-header"
    class:clickable={participant.entityId && onparticipantselect}
    onclick={() => handleParticipantClick(participant)}
    role={participant.entityId ? 'button' : undefined}
    tabindex={participant.entityId ? 0 : undefined}
    aria-label={participant.entityId ? `View details for ${participant.name}` : undefined}
    onkeydown={(e) => {
        if (participant.entityId && (e.key === 'Enter' || e.key === ' ')) {
            e.preventDefault();
            handleParticipantClick(participant);
        }
    }}
>
    <rect ... />
    <text ...>{participant.name}</text>
</g>
```

### Clickable Styling

```css
.participant-header.clickable {
    cursor: pointer;
}

.participant-header.clickable:hover rect {
    stroke: var(--color-primary);
    stroke-width: 2;
}

.participant-header.clickable:focus-visible rect {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
}
```

---

## C. Synthetic CanvasNode Construction

### Purpose

The `EntityDetailPanel` component expects a `CanvasNode` as input to display entity details. Since sequence diagram participants are not @xyflow nodes, a synthetic `CanvasNode` must be constructed from the participant data when a participant is clicked.

### Construction Function

**File:** `src/routes/models/[id]/+page.svelte` (or co-located utility)

```typescript
function participantToCanvasNode(participant: Participant): CanvasNode {
    return {
        id: participant.id,
        type: participant.type ?? 'component',
        position: { x: 0, y: 0 },
        data: {
            label: participant.name,
            entityType: participant.type ?? 'component',
            entityId: participant.entityId,
            description: '',
        },
    };
}
```

### Integration in Model Detail Page

```typescript
function handleParticipantSelect(participant: Participant) {
    if (!participant.entityId) return;
    // Construct synthetic node for EntityDetailPanel
    const syntheticNode = participantToCanvasNode(participant);
    selectedBrowseNode = syntheticNode;
    showEntityPanel = true;
}
```

The `selectedBrowseNode` state variable is the same one used by the @xyflow canvas node click handler, so the `EntityDetailPanel` renders identically for both canvas nodes and sequence participants.

---

## D. EntityDetailPanel Compatibility

### No Changes Required

The `EntityDetailPanel` component works with the synthetic node because it only uses:

- `node.data.entityId` to fetch entity details from the API
- `node.data.label` as fallback display text
- `node.data.entityType` for type badge rendering

All of these fields are populated by `participantToCanvasNode()`.

### Panel Behaviour

When a linked participant is clicked:

1. `EntityDetailPanel` opens (same as clicking a canvas node in browse mode)
2. Panel fetches entity details via `GET /api/entities/{entityId}`
3. Panel displays entity name, type, description, tags, relationships, and "Used in Models"
4. Panel includes "View details" link to the entity detail page
5. Clicking another participant or the background closes the current panel

---

## E. Browse Mode Guard

### Edit Mode Behaviour

In edit mode, participant clicks should open the edit dialog (existing behaviour), not trigger browse navigation. The `onparticipantselect` callback is only passed in browse mode:

```svelte
<SequenceDiagram
    {participants}
    {messages}
    editable={$canvasMode === 'edit'}
    onparticipantselect={$canvasMode === 'browse' ? handleParticipantSelect : undefined}
/>
```

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| Participant type includes optional `entityId` | TypeScript interface has `entityId?: string` field |
| Linked participants are clickable in browse mode | Click participant with `entityId`; verify callback fires |
| Unlinked participants not clickable | Click participant without `entityId`; verify no action |
| `onparticipantselect` fires with correct participant | Log callback argument; verify participant object matches |
| Synthetic CanvasNode has correct entityId | Verify `participantToCanvasNode` output includes `entityId` |
| EntityDetailPanel opens on participant click | Click linked participant; verify panel displays entity details |
| EntityDetailPanel shows entity name and type | Verify panel header matches participant's linked entity |
| Participant hover shows primary colour border | Hover linked participant; verify stroke change |
| Keyboard accessible (Enter/Space) | Tab to linked participant, press Enter; verify panel opens |
| Focus visible indicator | Tab to linked participant; verify focus outline |
| ARIA button role on linked participants | Inspect linked participant `<g>`; verify `role="button"` |
| Not clickable in edit mode | Switch to edit mode; click participant; verify no browse panel |
| Clicking background closes panel | Click outside participant; verify panel closes |

---

*This specification implements [ADR-051](../ADR-051-Sequence-Diagram-Browse-Mode.md).*
