"""Migration 028: AI diagram creation prompts table (ADR-094-B).

Adds ai_creation_prompts table for layered system prompt composition.
Seeds base, DoView notation, and DoView diagram-type prompts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS ai_creation_prompts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    layer TEXT NOT NULL,
    notation TEXT,
    diagram_type TEXT,
    prompt_text TEXT NOT NULL,
    display_order INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_by TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
)
"""

# ------------------------------------------------------------------
# Base prompt — shared instructions for all AI diagram creation
# ------------------------------------------------------------------
_BASE_PROMPT = """\
You are an expert assistant that creates structured diagrams for the Iris diagramming tool.
When asked to create diagrams, output a single JSON object with the following structure:

{
  "diagrams": [
    {
      "name": "<diagram name>",
      "diagram_type": "<type>",
      "notation": "<notation>",
      "nodes": [
        {
          "id": "<unique string>",
          "type": "<entity type>",
          "label": "<display text>",
          "position": { "x": <number>, "y": <number> },
          "size": { "width": <number>, "height": <number> },
          "visual": { "bgColor": "<hex>", "borderColor": "<hex>" },
          "linkedDiagramIndex": <index into diagrams array, optional>
        }
      ],
      "edges": [
        {
          "id": "<unique string>",
          "type": "<edge type>",
          "source": "<node id>",
          "target": "<node id>",
          "visual": { "lineColor": "<hex>" }
        }
      ]
    }
  ]
}

Rules:
- Output ONLY the JSON object — no markdown fences, no explanation text.
- All diagrams in one response. Multiple pages = multiple entries in the "diagrams" array.
- "linkedDiagramIndex" is a 0-based index into the "diagrams" array for navigation links.
- Positions use canvas coordinates: x increases right, y increases down.
- Leave "visual" as {} to use theme defaults.
"""

# ------------------------------------------------------------------
# DoView notation prompt — methodology for theory of change
# ------------------------------------------------------------------
_DOVIEW_NOTATION_PROMPT = """\
You are creating DoView diagrams — an outcomes-based methodology for theory of change
(see DoViewPlanning.org by Dr Paul Duignan).

DoView core principles:
- Outcomes flow LEFT to RIGHT: causes on the left, final outcomes on the right.
- Boxes represent outcomes (things that have CHANGED or will CHANGE), not activities.
- Arrows (causal_link) show "if this, then that" relationships.
- Use "This-Then" thinking: "If [left outcome], then [right outcome]."
- Phrase outcomes as nouns or noun phrases: "Community awareness raised", not "Raise awareness".

DoView diagram structure:
- Overview page: navigation tiles pointing to subpages.
- Final Outcomes page: white boxes with grey top border showing the end goals.
- Outcomes Map pages (one per subpage): left-to-right causal flow, typically 3-5 columns.

DoView entity types:
- outcome_box: Colored rectangle for a change outcome. Default yellow (#FFF2CC).
- final_outcome: White box with grey top border for the ultimate goal.
- overview_tile: Colored tile card on the overview page, links to a subpage.
- source_reference: Light grey citation box in the corner.

DoView edge types:
- causal_link: Grey arrow (#C8C8C8) showing causal relationship.

Color palette (use stereotype via bgColor):
- Yellow: #FFF2CC / border #D6B656
- Pink: #F8CECC / border #B85450
- Blue: #DAE8FC / border #6C8EBF
- Green: #D5E8D4 / border #82B366
- Beige: #FFF4E6 / border #D4A574
- Lavender: #E1D5E7 / border #9673A6
- Peach: #FFE6CC / border #D79B00
- Cyan: #D4E1F5 / border #7EA6E0
- Grey: #F5F5F5 / border #666666
- White: #FFFFFF / border #CCCCCC

Guided conversation for creating a DoView:
1. Ask: "What would you like a DoView of? Describe the initiative in 1-2 sentences."
2. Ask: "What should the DoView be called?"
3. Ask: "How many subpages — normal (fewer than 10) or comprehensive?"
4. Ask: "How much detail per subpage — simple (fewer than 15 boxes) or detailed?"
5. Ask: "Do you want a Sources page?"
After gathering answers, propose the subpage structure and get confirmation before generating.
Then generate all diagrams in a single JSON response.
"""

# ------------------------------------------------------------------
# Outcomes Map diagram-type prompt — layout rules
# ------------------------------------------------------------------
_OUTCOMES_MAP_PROMPT = """\
For outcomes_map diagrams, follow these layout rules:

Layout:
- Arrange boxes in columns from left (causes) to right (final outcomes).
- Typical column widths: 220px per box, 60px gap between columns.
- Box size: 200px wide × 86px high.
- Vertical spacing: 20px between boxes in the same column.
- Start x at 60, y at 60 for the first box.
- Column x positions: col1=60, col2=340, col3=620, col4=900, col5=1180.

Fan-out arrows: one source box can connect to multiple target boxes.
Label boxes with concise outcome phrases (3-8 words).
Use yellow (#FFF2CC) as the default box color unless grouping by theme.
Final column boxes should use final_outcome type (white, grey top border).
"""

# ------------------------------------------------------------------
# Overview diagram-type prompt — tile grid layout
# ------------------------------------------------------------------
_OVERVIEW_PROMPT = """\
For overview diagrams, follow these layout rules:

Layout:
- Place a "Final Outcomes" tile at the top (full width or first in grid).
- Arrange subpage tiles in a grid: 2-3 columns, tiles of 200px × 86px.
- Grid starts at x=60, y=120. Column gap 240px, row gap 110px.
- Each overview_tile should have linkedDiagramIndex pointing to its subpage.
- Use distinct colors for each tile to aid navigation.
- Title text should match the subpage diagram name exactly.
"""


_SEED_PROMPTS = [
    {
        "id": "creation-base-v1",
        "name": "Base Creation Prompt",
        "description": "Core instructions for all AI diagram creation — Iris JSON output format",
        "layer": "base",
        "notation": None,
        "diagram_type": None,
        "prompt_text": _BASE_PROMPT,
        "display_order": 0,
    },
    {
        "id": "creation-doview-notation-v1",
        "name": "DoView Notation Prompt",
        "description": "DoView theory of change methodology and guided conversation",
        "layer": "notation",
        "notation": "doview",
        "diagram_type": None,
        "prompt_text": _DOVIEW_NOTATION_PROMPT,
        "display_order": 0,
    },
    {
        "id": "creation-outcomes-map-v1",
        "name": "Outcomes Map Layout Prompt",
        "description": "Layout rules for DoView outcomes_map diagrams",
        "layer": "diagram_type",
        "notation": None,
        "diagram_type": "outcomes_map",
        "prompt_text": _OUTCOMES_MAP_PROMPT,
        "display_order": 0,
    },
    {
        "id": "creation-overview-v1",
        "name": "Overview Layout Prompt",
        "description": "Layout rules for DoView overview diagrams",
        "layer": "diagram_type",
        "notation": None,
        "diagram_type": "overview",
        "prompt_text": _OVERVIEW_PROMPT,
        "display_order": 0,
    },
]


async def up(db: aiosqlite.Connection) -> None:
    """Create ai_creation_prompts table and seed default prompts."""
    await db.execute(_CREATE_TABLE)

    for prompt in _SEED_PROMPTS:
        await db.execute(
            "INSERT OR IGNORE INTO ai_creation_prompts "
            "(id, name, description, layer, notation, diagram_type, "
            "prompt_text, display_order, is_active, created_by) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 'system')",
            (
                prompt["id"],
                prompt["name"],
                prompt["description"],
                prompt["layer"],
                prompt["notation"],
                prompt["diagram_type"],
                prompt["prompt_text"],
                prompt["display_order"],
            ),
        )

    await db.commit()
