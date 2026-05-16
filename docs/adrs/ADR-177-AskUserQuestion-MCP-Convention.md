# ADR-177: AskUserQuestion as MCP-wide user-question convention

Status: Accepted (2026-05-16)
Extends: [ADR-163](ADR-163-Centralised-MCP-Server-Instructions.md), [ADR-167](ADR-167-Orient-Directive-In-Tool-Response.md)

## Context

The ORIENT-FIRST protocol seeded into the MCP server `instructions` channel (ADR-163, v5.18.0) and reinforced via the tool-response wrapper (ADR-167, v6.0.6) already mentions AskUserQuestion in one place: "Offer the menu of options the orient sheet specifies, IN ORDER, VERBATIM. Use AskUserQuestion when the client supports it; numbered list otherwise." That sentence is correct for the orient menu — but it's wedged inside ORIENT-FIRST PROTOCOL, scoped to first-turn behaviour only.

The issue #133 UAT showed the rule failing in two unrelated places:

1. **Inside creation cascades.** Stage-0 questions (subject, info source, name, subpage size, detail level) were sometimes asked via AskUserQuestion, sometimes embedded as a numbered list inside prose. Turns 1, 3, 6, 7, and 10 of the banana transcript were inconsistent.
2. **At the destination step.** When the cascade reached the (then-absent) save-destination phase, even the limited variation that did surface there was prose, not AskUserQuestion.

The rule is broader than the orient menu. Any time the model is asking the user to pick from a finite set of options, the client's structured question tool (AskUserQuestion in Claude Code / Claude Desktop / Cursor) gives a better UX than embedded prose: the user sees clear option chips, can pick with one click, the model receives an unambiguous answer, and there is no parsing ambiguity from free-text replies.

A choice exists between three scopings:

- Keep the rule inside ORIENT-FIRST only (today's state). Cascades remain inconsistent.
- Add a parallel rule inside every `creation_format` cascade prompt (Phase 1's first draft of the plan). Repeats the rule, splits ownership.
- **Promote the rule to a top-level MCP-wide convention** in the same MCP server `instructions` channel ADR-163 / ADR-166 / ADR-167 already maintain. One rule, one place to drift.

The user (#133 review) chose the third option: one MCP-wide rule, cascades only add nuance (default-name pattern, paste/upload affordance).

## Decision

Add a new top-level **ASKING QUESTIONS** section to the MCP server-instructions singleton body (the row at `purpose='mcp_server_instructions'`, `layer='base'`), positioned between ORIENT-FIRST PROTOCOL and DISCOVERY TOOLS. Body:

```text
ASKING QUESTIONS.
Whenever you need the user to choose from a finite set of options, ask via the MCP client's structured user-question tool (AskUserQuestion in Claude Code / Claude Desktop / Cursor). Do not embed multi-option questions in prose. Do not list multiple questions in a single message — one question per turn, wait for the answer, then ask the next. When the client does not expose a user-question tool, fall back to a numbered list with options IN ORDER, VERBATIM (no paraphrasing).
This applies to:
  - the orient menu (already covered in ORIENT-FIRST above),
  - every Stage-0 setup question in a creation cascade,
  - the save-destination chooser,
  - any other choice the model surfaces to the user.
If you ever feel unsure whether a question warrants the tool: it does.
```

The body of `creation-cascade-shared-v1` (introduced in ADR-176) reinforces this rule for cascade Stage-0 specifically, but it does not duplicate the rule — it points at the ASKING QUESTIONS section as the source of truth and adds cascade-specific patterns (default-name suggestion, paste/upload affordance) that the top-level rule doesn't describe.

This ADR supersedes the **user-question half** of ADR-167 — specifically the sentence "Use AskUserQuestion when the client supports it; numbered list otherwise" — by relocating its intent into the new top-level section and broadening its scope from "orient menu" to "any user-facing choice." The structural-overview half of ADR-167 (the imperative TOC-loading directive in the tool-response wrapper) is unchanged.

The seed migration that ships this section is paired with the cascade base prompts migration so the two land in the same release (v6.1.0). The seed function `seed_creation_prompts` is extended to re-apply the mcp-server-instructions body on every startup, matching the existing pattern for cascade prompts — admin edits to the singleton body are overwritten with canonical content on the next deploy. (Today `m053_mcp_server_instructions_seed` INSERTs once via `INSERT OR IGNORE`; m057 patches in place; this phase adds re-apply-from-seed for ongoing canonical maintenance.)

## Why MCP-wide, not cascade-only

- The defect surfaces outside cascades (orient menu inconsistency, future tool responses that ask the user something). A cascade-only rule would leave the rest of the surface drifting.
- The orient sheet already mentioned AskUserQuestion in passing; promoting the mention to a first-class section unifies the existing partial rule with the new explicit one.
- One rule lives in one place — `mcp-server-instructions-v1`. Future edits to the convention propagate to every MCP client and every cascade through the same TTL refresh mechanism (ADR-166).

## Why not just rely on the orient-sheet sentence

That sentence is buried inside ORIENT-FIRST step 3 and reads as scoped to orient-menu options. Models read it as "use AskUserQuestion for menus on the first turn" not as "use AskUserQuestion for every multi-option question." Promoting it to its own section breaks that scoping ambiguity.

## Why update the seed pattern to re-apply on startup

`m053` shipped the singleton via `INSERT OR IGNORE`. `m057` fixed a defect via targeted `REPLACE`. Both are point-in-time edits and require a new migration each time the canonical body changes. The cascade-prompt pattern (seed function re-applies content on every startup) is strictly better — copy edits ship without a new migration, and admin breakage recovers on the next deploy. Adopting the same pattern for the MCP server-instructions row aligns the two prompt-management surfaces and removes a migration class.

## Consequences

- SQLite migration `m{next}_mcp_user_question_rule.py` and Supabase mirror UPDATE the existing singleton body to insert the new ASKING QUESTIONS section. Targeted text insert, not full body replace — preserves any admin customisation elsewhere.
- `backend/app/seed/creation_prompts.py` extended to also UPDATE `mcp-server-instructions-v1` to the canonical body on every startup. Body lifted from `docs/prompts/mcp-server-instructions.md`. Pattern matches the existing UPDATE-on-startup for cascade prompts.
- `mcp/src/iris_mcp/server_instructions.py:_FALLBACK_INSTRUCTIONS` updated to include the new section, so iris-mcp's day-one fallback body matches the seeded body for clients that connect before the backend has been hit.
- `docs/prompts/mcp-server-instructions.md` updated to show the new canonical body. Section between ORIENT-FIRST PROTOCOL and DISCOVERY TOOLS.
- ADR-167 status remains Accepted; this ADR supersedes only the user-question sentence inside ADR-167's body (orient-step 3). The TOC-loading wrapper is intact.

## Verification

- `pytest backend/tests/migrations/test_m{next}_mcp_user_question_rule.py` green — asserts the seeded singleton body contains the new ASKING QUESTIONS section header and the cascade-specific bullet.
- `pytest mcp/tests/` green — `_FALLBACK_INSTRUCTIONS` body match update reflected in any existing assertion.
- Post-deploy smoke: open claude.ai → Outcomes Theory Book → confirm orient menu still surfaces via AskUserQuestion; then open a fresh BPMN creation cascade → confirm every Stage-0 question surfaces via AskUserQuestion (not prose).

## See also

- [ADR-163](ADR-163-Centralised-MCP-Server-Instructions.md) — original Server.instructions channel.
- [ADR-166](ADR-166-MCP-Server-Instructions-TTL-Refresh.md) — TTL refresh that propagates edits to this body without redeploy.
- [ADR-167](ADR-167-Orient-Directive-In-Tool-Response.md) — partially superseded (user-question half only).
- [ADR-176](ADR-176-Cascade-Shared-Base-Prompts.md) — companion ADR shipping the cascade-specific reinforcement.
- [SPEC-177-A](specs/SPEC-177-A-AskUserQuestion-MCP-Convention.md) — exact body, migration shape, test plan.
- [`docs/prompts/mcp-server-instructions.md`](../prompts/mcp-server-instructions.md) — canonical paste-ready body.
- Issue [#133](https://github.com/cgbarlow/iris/issues/133) — UAT report.
