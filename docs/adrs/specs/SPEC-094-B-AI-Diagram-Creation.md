# SPEC-094-B: AI Diagram Creation System

**ADR:** [ADR-094](../ADR-094-DoView-Notation-AI-Creation.md)
**Part:** B — Modular AI diagram creation system
**Status:** In Progress

---

## Overview

A modular AI-powered diagram creation system layered on top of the existing Ask AI infrastructure. System prompts are composed in layers (base + notation + diagram-type + optional override), stored in the database for admin editing, and served through a dedicated creation endpoint. DoView is the first supported creation type.

---

## Database Changes

### Migration: `m028_ai_creation_prompts.py`

```sql
CREATE TABLE IF NOT EXISTS ai_creation_prompts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    layer TEXT NOT NULL CHECK(layer IN ('base', 'notation', 'diagram_type', 'override')),
    notation TEXT,       -- NULL for base; 'doview'/'uml'/etc for notation/diagram_type layers
    diagram_type TEXT,   -- NULL for base/notation; 'outcomes_map'/etc for diagram_type layer
    prompt_text TEXT NOT NULL,
    display_order INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_by TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

**Seed prompts (idempotent on `id`):**

1. **`creation-base`** (layer=base): Iris canvas JSON output schema — defines the exact JSON structure the AI must produce, node/edge field names, coordinate system, valid entity types, valid relationship types.

2. **`creation-doview-notation`** (layer=notation, notation=doview): Full DoView guided conversation methodology adapted from doview-skill — 8 setup questions (format questions removed), This-Then logic, outcome phrasing rules, subpage structure, 3-stage flow with checkpoints.

3. **`creation-doview-outcomes-map`** (layer=diagram_type, diagram_type=outcomes_map): Column layout rules, fan-out arrow connections, box sizing (min 86px height), vertical/horizontal space budget, color cycling.

4. **`creation-doview-overview`** (layer=diagram_type, diagram_type=overview): Tile grid layout (3 cols), raised Final Outcomes box, navigation link (`linkedDiagramIndex`).

---

## Backend Changes

### `backend/app/ai/creation.py` (new)

```python
async def build_creation_system_prompt(
    db: aiosqlite.Connection,
    notation: str,
    diagram_type: str | None = None,
) -> str:
    """Compose layered system prompt for diagram creation."""
    # 1. Check for override
    override = await _get_active_prompt(db, layer='override', notation=notation, diagram_type=diagram_type)
    if override:
        return override['prompt_text']

    # 2. Compose: base + notation + diagram_type
    parts = []
    base = await _get_active_prompt(db, layer='base')
    if base:
        parts.append(base['prompt_text'])

    notation_prompt = await _get_active_prompt(db, layer='notation', notation=notation)
    if notation_prompt:
        parts.append(notation_prompt['prompt_text'])

    if diagram_type:
        type_prompt = await _get_active_prompt(db, layer='diagram_type', diagram_type=diagram_type)
        if type_prompt:
            parts.append(type_prompt['prompt_text'])

    return "\n\n---\n\n".join(parts)


async def create_diagrams_from_ai(
    db: aiosqlite.Connection,
    set_id: str,
    ai_json: dict,
    user_id: str,
) -> list[str]:
    """Parse AI diagram JSON output and create diagrams in the DB.

    Returns list of created diagram IDs (first = overview/primary).
    """
    # Parse diagrams array from AI output
    # For each diagram definition:
    #   1. Create diagram record (name, diagram_type, notation, set_id)
    #   2. Build canvas nodes/edges from AI node/edge definitions
    #   3. Create initial diagram version with canvas data
    #   4. Resolve linkedDiagramIndex references to actual diagram IDs
    # Return created diagram IDs
```

### `backend/app/ai/models.py`

Add Pydantic models:

```python
class CreateDiagramRequest(BaseModel):
    message: str = Field(max_length=8000)
    notation: str = "doview"
    diagram_type: str | None = None
    conversation_id: str | None = None  # for multi-turn

class CreateDiagramApplyRequest(BaseModel):
    diagrams_json: str  # raw JSON string from AI, validated server-side
    set_id: str

class CreationPromptResponse(BaseModel):
    id: str
    name: str
    description: str | None
    layer: str
    notation: str | None
    diagram_type: str | None
    prompt_text: str
    display_order: int
    is_active: bool
    created_at: str
    updated_at: str

class CreationPromptUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    prompt_text: str | None = None
    is_active: bool | None = None
```

### `backend/app/ai/router.py`

Add endpoints:

```python
@router.post("/sets/{set_id}/create-diagram")
async def create_diagram_chat(
    set_id: str,
    body: CreateDiagramRequest,
    stream: bool = Query(default=True),
    ...
):
    """Streaming/non-streaming creation conversation using layered prompts."""
    # Build system prompt via build_creation_system_prompt(notation, diagram_type)
    # Stream conversation (same SSE protocol as /ask)
    # AI signals completion with: {"done": true, "diagrams_json": "...", "conversation_id": "..."}

@router.post("/sets/{set_id}/create-diagram/apply")
async def apply_diagram_creation(
    set_id: str,
    body: CreateDiagramApplyRequest,
    ...
):
    """Parse AI JSON output and materialise diagrams in the DB."""
    # Validate diagrams_json is valid JSON
    # Call create_diagrams_from_ai()
    # Return {"diagram_ids": [...], "primary_diagram_id": "..."}

@router.get("/creation-prompts")
async def list_creation_prompts(db=...):
    """List all creation prompts (admin only)."""

@router.put("/creation-prompts/{prompt_id}")
async def update_creation_prompt(prompt_id: str, body: CreationPromptUpdate, db=...):
    """Update a creation prompt (admin only)."""
```

---

## Frontend Changes

### `frontend/src/lib/components/SetQA.svelte`

Add creation mode to existing Q&A component:

**New state:**
```typescript
let creationMode = $state(false);
let selectedNotation = $state('doview');
let pendingDiagramsJson = $state<string | null>(null);
let applyingDiagrams = $state(false);
```

**UI additions (when creationMode = true):**
- Notation selector: `<select bind:value={selectedNotation}>` with option `doview` (more added later)
- Chat messages show a subtle "Create Mode" badge/indicator
- SSE response parsing: detect `payload.diagrams_json` → store in `pendingDiagramsJson`
- Show "Create Diagrams" button when `pendingDiagramsJson` is set

**"Create Diagram" toggle button:** placed in the chat header/toolbar area.

**Apply flow:**
```typescript
async function applyDiagrams() {
    applyingDiagrams = true;
    const resp = await fetch(`/api/ai/sets/${setId}/create-diagram/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ diagrams_json: pendingDiagramsJson, set_id: setId }),
    });
    const data = await resp.json();
    // Navigate to first created diagram
    goto(`/diagrams/${data.primary_diagram_id}`);
}
```

**Creation endpoint:** uses `/api/ai/sets/{setId}/create-diagram?stream=true` (same SSE protocol as `/ask`).

### `frontend/src/routes/admin/ai/+page.svelte`

Add "Creation Prompts" tab alongside existing provider management:

- Table: name, layer badge (base/notation/diagram_type/override), notation, diagram_type, active toggle
- Edit button → modal with large textarea for `prompt_text`, name/description fields
- PUT to `/api/ai/creation-prompts/{id}`

---

## AI Output JSON Schema

The base prompt instructs the AI to output exactly this JSON when generation is complete:

```json
{
  "diagrams": [
    {
      "name": "string — diagram display name",
      "diagram_type": "outcomes_map | overview | free_form",
      "notation": "doview",
      "description": "optional description",
      "nodes": [
        {
          "id": "string — unique within this diagram",
          "type": "outcome_box | final_outcome | overview_tile | source_reference",
          "label": "string — outcome text",
          "position": { "x": 0, "y": 0 },
          "size": { "width": 200, "height": 86 },
          "visual": {
            "bgColor": "#FFF2CC",
            "borderColor": "#D6B656",
            "fontColor": "#333333",
            "borderWidth": 2,
            "bold": false
          },
          "stereotype": "page_yellow",
          "linkedDiagramIndex": null
        }
      ],
      "edges": [
        {
          "id": "string — unique within this diagram",
          "type": "causal_link",
          "source": "node-id",
          "target": "node-id",
          "visual": { "lineColor": "#C8C8C8", "lineWidth": 2 }
        }
      ]
    }
  ]
}
```

`linkedDiagramIndex` is an integer index into the `diagrams` array (0-based), used by `overview_tile` nodes to reference which diagram they navigate to. `create_diagrams_from_ai()` resolves these to actual diagram IDs after creating all diagrams.

---

## Tests

- `backend/tests/test_migrations/test_m028_ai_creation_prompts.py`
- `backend/tests/test_ai/test_creation_service.py` — `build_creation_system_prompt`, layer composition, override logic, `create_diagrams_from_ai` parsing
- `backend/tests/test_ai/test_creation_router.py` — endpoint request/response shapes, streaming, apply endpoint
- `frontend/tests/unit/setQACreationMode.test.ts` — toggle state, creation endpoint call, apply button visibility
