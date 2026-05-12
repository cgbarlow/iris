# DoView Book Set — `mcp_system_context` content

Canonical paste-ready content for the **MCP system context** field on the DoView Book Set (`/sets/33032180-d77a-4ce4-88cf-b49cd643e093`).

This pointer is what an MCP client model (Claude Desktop / Claude Code) sees when it calls `mcp__iris__get_set` on the DoView Book Set. It is intentionally short — it orients the model to the response-format workflow without trying to encode formatting rules in tool data (those live in the layered response_format prompts seeded by SQLite m051 / Supabase m055, fetched at runtime via `iris_get_response_prompt`).

Per ADR-156 (`mcp_system_context` semantics) and ADR-157 (response_format layered prompts).

## Content

Paste the following into the **MCP system context** textarea on the DoView Book Set edit page:

```text
This set is the visual companion to Dr Paul Duignan's DoView outcomes-
mapping methodology and outcomes-theory body of work (the "Outcomes
Theory" book in Iris; previously named "DoView Book").

ORIENT FIRST — do not jump into a tool action without a menu.

When a user opens or asks about this set, the FIRST response should:
  1. Briefly describe the set's purpose (one or two sentences).
  2. Use iris_package_hierarchy(set_id=<this-set>) — NOT list_packages,
     which paginates and misses older chapters — to list the chapter
     structure (Part A through Part J, with brief one-line descriptions).
  3. Offer a menu of common next steps and wait for the user to choose.
     If your client supports a structured multiple-choice question UI
     (Claude Code's AskUserQuestion, similar affordances in other
     clients), use it; otherwise present the options as a bulleted list
     and let the user reply free-form. The menu:
       - "Pull up a specific chapter or diagram (e.g. J03 - Using AI to
          Speed Up DoView Planning)"
       - "Ask a cross-package question (e.g. 'what are the recurring
          causal-link conventions across the diagrams?')"
       - "Generate a new DoView outcomes-theory analysis on a topic the
          user describes, grounded in this handbook, and optionally save
          it back here"
       - "Browse a particular chapter's diagrams in detail"

DO NOT generate an analysis or fetch a response prompt on the first
turn unless the user has explicitly asked for one. Open with the menu.

────────────────────────────────────────────────────────────────────
Two different "DoView" outputs the user might ask for — different paths
────────────────────────────────────────────────────────────────────

A. WRITTEN OUTCOMES-THEORY ANALYSIS (prose + embedded mermaid diagrams
   from referenced handbook tool pages). This is the doview_analysis
   flow. Use this when the user says "generate a DoView analysis",
   "analyse X from an outcomes-theory perspective", "what does
   outcomes theory say about Y", or similar text-output requests.

   Steps:
     1. Fetch the response format rules:
          iris_get_response_prompt(notation='markdown',
                                   diagram_type='doview_analysis')
     2. Compose the response in-conversation following those rules,
        using mcp__iris__search + mcp__iris__get_diagram against this
        set for handbook source material.
     3. AFTER producing the analysis, offer BOTH save paths (do not
        assume only one is wanted):
          (i) Save into Iris as a doview_analysis diagram:
                iris_save_doview_analysis(set_id, name, content,
                                          parent_package_id?)
              (auth required — if no IRIS_TOKEN, returns an auth
              error; in that case the markdown is already in chat
              for copy/paste.)
              When suggesting a parent_package_id, recommend a
              sensible chapter — AI-related → J series; evaluation
              → G; introduction/adoption → I; alignment → C;
              indicators → D; contracting → E; reporting → H;
              fundamentals → A; drawing/strategy → B; performance
              improvement → F. If unsure, suggest top-level or
              ask. The user may also redirect to a different set.
         (ii) Leave the markdown in chat so the user can copy /
              save it locally. The chat content IS the markdown —
              no additional tool call is needed.

   DO NOT use mcp__iris__ask for this flow. mcp__iris__ask is for
   Iris's own internal Q&A and creation flows; it would route the
   work back through Iris's backend LLM (costly, slower, and not
   what the user asked for here).

B. NEW VISUAL DOVIEW DIAGRAM (a new notation=doview outcomes_map or
   overview-style page that will appear in the set as a real Iris
   diagram). Use this when the user says "create a new DoView
   diagram", "draw an outcomes map for X", "build the theory of
   change as a diagram", etc.

   For this case, the guided creation flow (Stages 0-3, the 13
   drafting steps, balance checks, the "This-Then" methodology)
   is best done through Iris's web UI:
     https://iris-uat.chrisbarlow.nz/sets/<this-set-id>
   Open the set, click "New diagram", pick notation=DoView,
   diagram_type=outcomes_map. The Ask Iris panel will walk through
   the methodology and materialise the result as real diagrams.

   Direct generation through MCP is possible (mcp__iris__ask with
   mode='creation', then apply_diagram_creation) but loses the
   guided-conversation rhythm that the methodology depends on.
   Recommend the web UI for this case unless the user explicitly
   prefers the MCP path.

────────────────────────────────────────────────────────────────────
Discoverability helpers
────────────────────────────────────────────────────────────────────

  list_response_format_types
    What output formats are available (e.g. doview_analysis).

  iris_package_hierarchy(set_id=<this-set>)
    Complete chapter tree, single call. Preferred over list_packages.
```

## Revision history

**Post-v5.13.1 fix (this revision).** Restored the orient-first /
offer-menu pattern that was implicit in pre-v5.12 conversations but
got drowned out when more prescriptive routing was added. Explicit
about which path each user-request shape maps to:
- "analysis" → `iris_get_response_prompt` + compose + optional save
- "diagram" → web UI (guided creation)
- `mcp__iris__ask` is explicitly NOT the path for either (was being
  defaulted to incorrectly).
Also reflects the set rename: "DoView Book" → "Outcomes Theory" in
the prose, while keeping the file name stable.

**v5.13.0 — package_hierarchy hint.** Mentions
`iris_package_hierarchy` (ADR-158) as the preferred single-call
mechanism to get the chapter list; resolves the "only saw E-J"
pagination problem.

**v5.12.0 — save-options offer.** Instructs the client to offer both
save paths after producing a doview_analysis (Iris save + markdown
artefact in chat).

The "offer both save paths" + "orient first" behaviours arguably
belong in the `response-format-doview-analysis-v1` row's body so
they apply universally, not just on this Set. Until that row is
amended via `/admin/settings/ai`, this scope-specific doc is the
single source of guidance.

## Why this content (and not the strict format rules)

- The DoView Book Set is one scope; the response_format rules are universal to any `(notation=markdown, diagram_type=doview_analysis)` conversation regardless of scope. They belong in the layered prompts table (admin-editable, central), not duplicated into per-scope passthrough fields. ADR-157 establishes this split.
- Embedding the strict Prompt-C rules directly in `mcp_system_context` would:
  - Trigger prompt-injection treatment (the client model sees scope tool data as untrusted; long directive content in tool data is treated as informational, not authoritative).
  - Duplicate content that's already in the response_format prompt rows.
  - Make the rules un-editable from a central admin surface.
- The fetch step (`iris_get_response_prompt`) is a deliberate model action — the response_format cascade body arrives as the response to a tool call the model chose to make. That's a stronger trust signal than scope tool data.

## Smoke test after pasting

In a fresh Claude Desktop conversation with Iris MCP connected:

> "Give me an outcomes-theory analysis of siloing program steps in the DoView Book Set."

Expected flow:
1. Claude calls `mcp__iris__get_set` → sees the pointer.
2. Claude calls `mcp__iris__get_response_prompt('markdown', 'doview_analysis')` → fetches the cascade (~300 lines of Prompt C rules).
3. Claude calls `mcp__iris__search` + `mcp__iris__get_diagram` to gather handbook material.
4. Claude composes a three-section formal response (Summary + Full + Diagrams with verbatim mermaid blocks + raw handbook URLs).
5. Claude offers to save via `iris_save_doview_analysis`.

If Claude doesn't reach for `iris_get_response_prompt` reliably, sharpen this content's signal (e.g. lead with "For outcomes-theory questions about this set, **always** call iris_get_response_prompt…"). The current phrasing is intentionally conservative; tighten if real usage shows under-triggering.

## See also

- [ADR-156](../adrs/ADR-156-MCP-System-Context-Data-Passthrough.md) — what `mcp_system_context` is for (per-scope context, data passthrough).
- [ADR-157](../adrs/ADR-157-Response-Format-Prompts-and-DoView-Analysis-Artefact.md) — where the response_format rules live (universal layered prompts, admin-editable).
- [SPEC-157-A](../adrs/specs/SPEC-157-A-Response-Format-Prompts.md) — schema and endpoint shapes for the response_format mechanism.
- [`doview-book-prompt-c-iris.md`](./doview-book-prompt-c-iris.md) — the source content from which the seeded response_format prompts (`response-format-base-v1`, `response-format-doview-notation-v1`, `response-format-doview-analysis-v1`) were derived.
