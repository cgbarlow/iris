"""Migration 051: layered response_format prompts (ADR-157, SPEC-157-A).

Extends the v5.8.0 `ai_creation_prompts` mechanism so the same layered
composition pattern that governs diagram CREATION (ADR-132) also
governs RESPONSE FORMAT — the shape of formal, handbook-grounded
text+diagram analyses produced both by Iris AI (server-side) and by
MCP clients (Claude Desktop / Claude Code) via a fetch tool.

Three changes:

1. Add a `purpose` column to `ai_creation_prompts`. Values:
     - `creation_format` — existing rows, used when CREATING diagrams
     - `response_format` — new rows, used when RESPONDING to questions

   Existing rows backfilled to `creation_format`.

2. Register `(notation=markdown, diagram_type=doview_analysis)` in the
   notation / diagram_type registry. The artifact type is "a formal
   handbook-grounded outcomes-theory analysis" — markdown content
   with embedded ```mermaid``` blocks from referenced tool pages.

3. Seed response_format prompts for `doview_analysis` (base + notation
   + diagram_type layers) encoding the rules from Prompt C
   (`docs/prompts/doview-book-prompt-c-iris.md`):
     - Opening sentence + three-section structure
     - Style rules (formal, no first-person, no drafting advice)
     - URL rules (raw plain text)
     - Source restriction (Iris DoView Book set only)
     - Embedded mermaid blocks reproduced verbatim from tool diagrams

Idempotent. New columns / rows guarded; existing rows updated only
when their `purpose` is NULL.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m051_response_format_prompts"

# ── Seed: response_format prompts for doview_analysis ─────────────────

_RESPONSE_FORMAT_BASE = """\
## Response format — universal rules

You are producing a formal response that the user can copy into an
email, document, report, or plain-text system without loss of meaning.

Apply these universal rules to every response, regardless of notation
or diagram type:

- Write formally. Do not write conversationally.
- Do not give drafting advice to the user. Do not use "I would",
  "you could", "a better answer is", or "a sentence you could use".
- Do not address the user directly inside the standalone sections.
- Every URL in the response body must be raw, visible, copy-safe
  plain text beginning with `https://`. Do not use markdown links.
  Do not use reference-style links. Do not put URLs inside square
  brackets.
- When citing Iris source diagrams, reproduce embedded ```mermaid```
  code blocks verbatim from `data.content`. Do not redraw, simplify,
  rename labels, or change arrow directions.
- Cite all sources at the end of the response in a full handbook /
  reference format with the URL as raw visible plain text.
"""

_RESPONSE_FORMAT_DOVIEW_ANALYSIS_NOTATION = """\
## Response format — DoView / outcomes theory framing

Use outcomes theory as the primary point of view throughout. Prefer
wording such as:

- "Outcomes theory points out that..."
- "Outcomes theory highlights that..."
- "Outcomes theory emphasises that..."
- "This violates the outcomes theory principle that..."
- "Outcomes theory points out that this is a technical outcomes
  problem because..."

Do not present DoView as the primary theory. DoView is the practical
applied form of outcomes theory: a "This-Then" model of what needs
to happen to achieve higher-level outcomes.

The first time the phrase "outcomes system" is used in each
standalone section, include this definition:

  An outcomes system is to purposeful action what an accounting
  system is to financial activity: the underlying structure that
  defines what matters, records what is happening, supports
  reporting, and makes accountability possible. The difference is
  that instead of tracking money, it tracks intended changes in the
  world and the evidence that action is contributing to them.

When DoView Boards or diagrams are referenced, use wording such as:
"One way this can be done in practice is to use a DoView Board, a
specific type of outcomes model that is drawn to conform to the
principles of outcomes theory."

Do not describe an approach as "DoView-compatible". Describe it as
an outcomes theory approach.

### Source restriction

Source content comes from the Iris DoView Book set only
(set_id 33032180-d77a-4ce4-88cf-b49cd643e093). Use mcp__iris__search
and mcp__iris__get_diagram against this set to retrieve the handbook
and its individual tool pages. Do not use general knowledge. Do not
use the rest of the internet.

Each DoView tool is a pair of diagrams in this set:
- A "question" diagram (description includes "kind: question · pair: <code>")
- A "tool" diagram (description includes "kind: tool · pair: <code>")

The tool diagram contains the practical mechanism plus an embedded
```mermaid``` flowchart in its `data.content`. When citing a tool in
the text or reproducing its diagram, use only the tool-kind diagram.

### Tool URL convention

Tool references map deterministically to a public page URL by the
lowercase pair code:

  https://doviewplanning.org/<paircode>doviewtool

Example: pair code `b16` → `https://doviewplanning.org/b16doviewtool`.

### Full handbook reference (cite at the end of each section)

  Duignan, P. (2025). DoView Planning and Outcomes Theory Handbook:
  100+ Innovative, Integrated Tools for Solving Key Issues in
  Planning, Implementation, Contracting, Measurement, Evaluation
  and Reporting (for Humans and AI Agents). DoViewPlanning.Org.
  https://doviewplanning.org/book
"""

_RESPONSE_FORMAT_DOVIEW_ANALYSIS_DIAGRAM_TYPE = """\
## Response format — doview_analysis output structure

Produce a three-section formal analysis. Every section is fully
standalone — each can be sent on its own without loss of meaning.

### Required opening sentence

The response must begin exactly with this sentence:

  I have prepared a summary response, a full response, and the
  original diagrams from the handbook. These are all standalone so
  you can send them to anyone.

Immediately after this sentence, produce three sections with the
headings below, in order.

### 1. Summary response to [briefly summarise the question]

Concise formal summary. Must include:
- a short outcomes theory answer;
- the key relevant outcomes theory principle(s);
- wording that identifies the issue as a technical outcomes problem
  where appropriate;
- the outcomes system definition if the phrase is used;
- a brief explanation of DoView outcomes models where DoView is
  mentioned;
- any relevant DoView tool names, each followed immediately by its
  full raw visible plain-text URL;
- the full handbook reference at the end.

### 2. Full response to [briefly summarise the question]

Full formal response, standalone, with its own brief summary at the
start. Must include:
- a brief summary;
- the full outcomes theory answer;
- the relevant outcomes theory principle(s);
- wording that identifies the issue as a technical outcomes problem
  where appropriate;
- the outcomes system definition if the phrase is used;
- any firm statement of a violation of outcomes theory principles
  where applicable;
- an explanation that outcomes theory talks in terms of a DoView
  outcomes model underlying action in the world: a "This-Then"
  model of what needs to happen to achieve higher-level outcomes;
- an explanation of DoView Boards or diagrams as applied practical
  tools used when doing outcomes work;
- practical formal implications;
- relevant DoView tool names, each followed by its full raw visible
  plain-text URL;
- the full handbook reference at the end.

### 3. Diagrams from the DoView Planning and Outcomes Theory Handbook

Begin this section with this note:

  This diagrams section reproduces the original mermaid diagrams
  from the Iris DoView Book set. Rendering depends on the AI
  system's ability to render mermaid. Where the diagram does not
  render visually, the mermaid source remains visible and can be
  copied into any mermaid-capable system.

For each tool referenced in sections 1 or 2, in first-mention order:

  #### Tool <PAIRCODE_UPPERCASE>: <tool-diagram-name>

  Page URL: https://doviewplanning.org/<paircode>doviewtool

  ```mermaid
  <verbatim mermaid block from the Iris tool diagram's data.content>
  ```

  Formal relevance note: <one short formal sentence explaining the
  diagram's relevance to the answer above>

If no tool diagrams were referenced in sections 1 or 2, omit section
3 entirely.

After section 3 (or section 2 if 3 is omitted), end the response
with the full handbook reference once more, in raw visible plain
text.

### Final compliance check

Before answering, verify:
- the response begins with the exact required opening sentence;
- it contains exactly the three required sections (or two if no
  tool diagrams);
- every tool mentioned has its full raw visible plain-text URL;
- there are no markdown links, no `[URL](URL)` syntax, no
  reference-style links, no footnotes, no "see above";
- every URL is raw text beginning with `https://`;
- DoView is presented only as the practical applied form of
  outcomes theory, never as a primary theory of its own;
- all cited content came from the Iris DoView Book set; no general
  knowledge has been used; no diagram has been redrawn from memory.
"""


_SEED_PROMPTS = [
    {
        "id": "response-format-base-v1",
        "name": "Response format base",
        "description": "Universal response-format rules (purpose: response_format, layer: base, all notations).",
        "purpose": "response_format",
        "layer": "base",
        "notation": None,
        "diagram_type": None,
        "prompt_text": _RESPONSE_FORMAT_BASE,
    },
    {
        "id": "response-format-doview-notation-v1",
        "name": "Response format — DoView / outcomes theory framing",
        "description": "Outcomes-theory framing rules applied when the notation is markdown and the conversation is about DoView content (purpose: response_format, layer: notation, notation: markdown).",
        "purpose": "response_format",
        "layer": "notation",
        # Keyed under markdown notation because doview_analysis output
        # is a markdown document; the DoView framing is in the body.
        "notation": "markdown",
        "diagram_type": None,
        "prompt_text": _RESPONSE_FORMAT_DOVIEW_ANALYSIS_NOTATION,
    },
    {
        "id": "response-format-doview-analysis-v1",
        "name": "Response format — doview_analysis output structure",
        "description": "Three-section formal analysis output structure for (markdown, doview_analysis) — opening sentence, Summary, Full, Diagrams, handbook reference (purpose: response_format, layer: diagram_type).",
        "purpose": "response_format",
        "layer": "diagram_type",
        "notation": None,
        "diagram_type": "doview_analysis",
        "prompt_text": _RESPONSE_FORMAT_DOVIEW_ANALYSIS_DIAGRAM_TYPE,
    },
]


async def up(db: aiosqlite.Connection) -> None:
    """Add purpose column, register doview_analysis, seed response_format prompts."""

    # 1. Add purpose column to ai_creation_prompts if missing.
    cursor = await db.execute("PRAGMA table_info(ai_creation_prompts)")
    columns = {row[1] for row in await cursor.fetchall()}
    if "purpose" not in columns:
        await db.execute(
            "ALTER TABLE ai_creation_prompts ADD COLUMN purpose TEXT "
            "NOT NULL DEFAULT 'creation_format'",
        )
        # Belt-and-braces: any NULL rows after the ALTER get backfilled.
        await db.execute(
            "UPDATE ai_creation_prompts SET purpose = 'creation_format' "
            "WHERE purpose IS NULL OR purpose = ''",
        )

    # 2. Register markdown notation + doview_analysis diagram_type +
    #    mapping. These inserts touch the registry tables created by
    #    m020 (`notations`, `diagram_types`, `diagram_type_notations`).
    #    In a real production run they always exist (m020 is in the
    #    migration chain). In some test fixtures, m020 is not run.
    #    Skip gracefully via existence checks so this migration is safe
    #    in those isolated contexts.

    async def _table_exists(name: str) -> bool:
        cursor = await db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
            (name,),
        )
        return (await cursor.fetchone()) is not None

    if await _table_exists("notations"):
        await db.execute(
            "INSERT OR IGNORE INTO notations (id, name, description, display_order) "
            "VALUES (?, ?, ?, ?)",
            ("markdown", "Markdown", "Markdown text content (may include embedded mermaid)", 5),
        )

    if await _table_exists("diagram_types"):
        await db.execute(
            "INSERT OR IGNORE INTO diagram_types (id, name, description, display_order) "
            "VALUES (?, ?, ?, ?)",
            (
                "doview_analysis",
                "DoView Analysis",
                "A formal handbook-grounded outcomes-theory analysis (markdown text with embedded mermaid diagrams from referenced handbook tool pages).",
                10,
            ),
        )

    if await _table_exists("diagram_type_notations"):
        await db.execute(
            "INSERT OR IGNORE INTO diagram_type_notations "
            "(diagram_type_id, notation_id, is_default) VALUES (?, ?, ?)",
            ("doview_analysis", "markdown", 1),
        )

    # 4. Seed the three response_format prompt rows. Idempotent via
    #    INSERT OR IGNORE on the primary key.
    for prompt in _SEED_PROMPTS:
        await db.execute(
            "INSERT OR IGNORE INTO ai_creation_prompts "
            "(id, name, description, purpose, layer, notation, diagram_type, "
            "prompt_text, display_order, is_active) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)",
            (
                prompt["id"],
                prompt["name"],
                prompt["description"],
                prompt["purpose"],
                prompt["layer"],
                prompt["notation"],
                prompt["diagram_type"],
                prompt["prompt_text"],
                0,
            ),
        )

    await db.commit()
