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

    3. Generate a new DoView outcomes-theory analysis on a topic the user describes,
       grounded in this handbook, with an option to save it back into this set.
       Path: iris_get_response_prompt(notation='markdown', diagram_type='doview_analysis')
       → compose locally → optionally iris_save_doview_analysis. NOT mcp__iris__ask.

    4. Browse a particular chapter's diagrams in detail
       (iris_package_hierarchy filtered to a chapter, then mcp__iris__get_diagram on each).

If the user's opening request explicitly asks for one option, briefly acknowledge it and present the menu of the other three so they can redirect.

PATH DETAILS

A. ANALYSIS (option 3 above) — written outcomes-theory analysis with embedded mermaid:
   - Fetch rules: iris_get_response_prompt(notation='markdown', diagram_type='doview_analysis')
   - Compose using mcp__iris__search + mcp__iris__get_diagram against this set
   - After producing, offer BOTH save paths:
       (i) iris_save_doview_analysis(set_id, name, content, parent_package_id?) —
           auth required (IRIS_TOKEN). Suggest a parent_package_id by topic:
           AI → J series; evaluation → G; introduction/adoption → I; alignment → C;
           indicators → D; contracting → E; reporting → H; fundamentals → A;
           drawing/strategy → B; performance improvement → F.
       (ii) Leave the markdown in chat for copy/paste — it IS the markdown.

B. NEW VISUAL DOVIEW DIAGRAM (a notation=doview outcomes_map):
   The guided creation flow (Stages 0-3, 13 drafting steps, balance checks) is best done in Iris's web UI:
     https://iris-uat.chrisbarlow.nz/sets/33032180-d77a-4ce4-88cf-b49cd643e093
   Open the set → New diagram → notation=DoView → diagram_type=outcomes_map. Recommend the web UI for this case.

DISCOVERABILITY

  list_response_format_types — what formats are available
  iris_package_hierarchy(set_id=<this-set>) — chapter tree, single call
```

## Why this works

- **Orient lands on first turn whether Claude calls `search` or `get_set`** — v5.14.0 (ADR-159) extended search results for Set / Collection hits to include `mcp_system_context`. Claude's natural "search → return link" flow now also surfaces this content.
- **The four options are mandatory and verbatim** — paraphrasing got Claude down to 2 options in v5.13.x. Explicit "all four, every time" + verbatim wording fixes that.
- **AskUserQuestion is conditional** — Claude Code has it; Claude Desktop / claude.ai / generic MCP clients don't (yet). Numbered list is the fallback.
- **Routing for "generate analysis" is explicit** — `iris_get_response_prompt`, NOT `mcp__iris__ask`. v5.13.x left this implicit and Claude defaulted to the wrong path.

## Revision history

- **v5.14.0 (this revision).** Trimmed from ~140 lines to ~50 (target was ~60). Same orient-first-with-four-option-menu intent, far less text. Surfaced through search results too (ADR-159) so the orient lands on first turn regardless of whether Claude calls `get_set` or just `search`.
- **v5.13.3.** Made the four-option menu mandatory and verbatim. Honest note about AskUserQuestion availability.
- **v5.13.2.** Restored orient-first / offer-menu pattern; explicit analysis-vs-diagram routing; "DO NOT use mcp__iris__ask for analysis flow".
- **v5.13.0.** Mention `iris_package_hierarchy` (ADR-158) as the preferred chapter-list call.
- **v5.12.0.** Save-options offer added (Iris save + markdown artefact).

The "offer both save paths" + "orient first" behaviours arguably belong in the `response-format-doview-analysis-v1` row's body so they apply universally, not just on this Set. Until that row is amended via `/admin/settings/ai`, this scope-specific doc is the single source of guidance.

## See also

- [ADR-156](../adrs/ADR-156-MCP-System-Context-Data-Passthrough.md) — what `mcp_system_context` is for (per-scope context, data passthrough on `get_set` / `get_collection`).
- [ADR-157](../adrs/ADR-157-Response-Format-Prompts-and-DoView-Analysis-Artefact.md) — where the response_format rules live (universal layered prompts, admin-editable).
- [ADR-159](../adrs/ADR-159-Scope-Context-In-Search-Results.md) — search results carry `mcp_system_context` so orient lands on first turn.
- [SPEC-157-A](../adrs/specs/SPEC-157-A-Response-Format-Prompts.md) — schema for the response_format mechanism.
- [`doview-book-prompt-c-iris.md`](./doview-book-prompt-c-iris.md) — the source content from which the seeded response_format prompts were derived.
