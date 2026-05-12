# DoView / Outcomes-Theory Set — `mcp_system_context` content

Canonical paste-ready content for the **MCP system context** field on the Outcomes Theory Set (`/sets/33032180-d77a-4ce4-88cf-b49cd643e093`, previously named "DoView Book"). The same content flows through both `get_set` and (since v5.14.0 / ADR-159) `search` results, so an MCP client model sees the orient guidance the moment the set is matched — no follow-up `get_set` call required.

## Content (paste this into the field on UAT)

```text
This set is the visual companion to Dr Paul Duignan's outcomes-theory body of work and DoView outcomes-mapping methodology.

ORIENT FIRST. On the first turn, before doing any other tool action:
  1. Briefly describe the set (one sentence).
  2. Call iris_package_hierarchy(set_id=<this-set>) — NOT list_packages — and list the chapters (Part A through Part J) with one-line descriptions.
  3. Offer ALL FOUR options below. Use a structured multi-choice UI if your client has one (Claude Code: AskUserQuestion). Otherwise present as a numbered list (1./2./3./4.), one option per line.

  THE FOUR OPTIONS — verbatim, all four, every time:

    1. Pull up a specific chapter or diagram from the handbook
       (e.g. J06 — Mathematization of Outcomes Theory).

    2. Ask a cross-package question via Iris AI
       (e.g. "What are the recurring causal-link conventions?" — uses mcp__iris__ask).

    3. Generate a new DoView outcomes-theory analysis OR a new visual
       DoView outcomes_map on a topic the user describes. → call
       iris_create_diagram. The tool's own description carries the
       full workflow (discover via list_notations / list_diagram_types,
       fetch the creation prompt cascade via iris_get_response_prompt
       with purpose='creation_format', run the guided conversation,
       confirm destination using create_collection / create_set /
       create_package as needed, save). Do not duplicate that
       workflow here.

    4. Browse a particular chapter's diagrams in detail
       (iris_package_hierarchy filtered to a chapter, then mcp__iris__get_diagram on each).

If the user's opening request explicitly asks for one option, briefly acknowledge it and present the menu of the other three so they can redirect.

DISCOVERABILITY

  list_response_format_types(purpose='response_format'|'creation_format') — what response formats / creation types are available
  iris_package_hierarchy(set_id=<this-set>) — chapter tree, single call
```

## Why this works

- **Orient lands on first turn whether Claude calls `search` or `get_set`** — v5.14.0 (ADR-159) extended search results for Set / Collection hits to include `mcp_system_context`. Claude's natural "search → return link" flow now also surfaces this content.
- **The four options are mandatory and verbatim** — paraphrasing got Claude down to 2 options in v5.13.x. Explicit "all four, every time" + verbatim wording fixes that.
- **AskUserQuestion is conditional** — Claude Code has it; Claude Desktop / claude.ai / generic MCP clients don't (yet). Numbered list is the fallback.
- **Workflow logic lives in the `create_diagram` tool description, not here.** v5.17.0 (ADR-162) moved the full creation flow (discover → fetch creation prompt → guided conversation → confirm destination → save) into the tool's description so it travels universally across every MCP client and every scope, not just this set. The scope context just points at the tool.

## Revision history

- **v5.17.0 (this revision).** Stripped the diagram-creation workflow entirely (paths A and B in v5.16.x) — that lives in `create_diagram`'s tool description now (ADR-162). The web-UI-handoff guidance for visual DoView creation is gone; the generic `create_diagram` flow covers both markdown DoView analyses and visual DoView outcomes_maps. ~30 lines shorter.
- **v5.14.0.** Trimmed from ~140 lines to ~50 (target was ~60). Same orient-first-with-four-option-menu intent, far less text. Surfaced through search results too (ADR-159) so the orient lands on first turn regardless of whether Claude calls `get_set` or just `search`.
- **v5.13.3.** Made the four-option menu mandatory and verbatim. Honest note about AskUserQuestion availability.
- **v5.13.2.** Restored orient-first / offer-menu pattern; explicit analysis-vs-diagram routing; "DO NOT use mcp__iris__ask for analysis flow".
- **v5.13.0.** Mention `iris_package_hierarchy` (ADR-158) as the preferred chapter-list call.
- **v5.12.0.** Save-options offer added (Iris save + markdown artefact).

## See also

- [ADR-156](../adrs/ADR-156-MCP-System-Context-Data-Passthrough.md) — what `mcp_system_context` is for (per-scope context, data passthrough on `get_set` / `get_collection`).
- [ADR-157](../adrs/ADR-157-Response-Format-Prompts-and-DoView-Analysis-Artefact.md) — where the response_format rules live (universal layered prompts, admin-editable).
- [ADR-159](../adrs/ADR-159-Scope-Context-In-Search-Results.md) — search results carry `mcp_system_context` so orient lands on first turn.
- [ADR-162](../adrs/ADR-162-Generic-MCP-Diagram-Creation-Workflow.md) — generic `create_diagram` tool + workflow-in-tool-descriptions pattern.
- [SPEC-157-A](../adrs/specs/SPEC-157-A-Response-Format-Prompts.md) — schema for the response_format mechanism.
- [`doview-book-prompt-c-iris.md`](./doview-book-prompt-c-iris.md) — the source content from which the seeded response_format prompts were derived.
