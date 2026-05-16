# SPEC-177-A: AskUserQuestion as MCP-wide user-question convention

ADR: [ADR-177](../ADR-177-AskUserQuestion-MCP-Convention.md)

## Summary

Insert a new top-level **ASKING QUESTIONS** section into the `mcp-server-instructions-v1` singleton body, positioned between ORIENT-FIRST PROTOCOL and DISCOVERY TOOLS. Migration patches existing deploys; seed function re-applies the canonical body on every startup (new behaviour for this row, matching the existing cascade-prompt pattern). Update `iris-mcp`'s `_FALLBACK_INSTRUCTIONS` so day-one fallback matches the seeded body.

## Body to insert

Lifted from [`docs/prompts/mcp-server-instructions.md`](../../prompts/mcp-server-instructions.md):

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

Insertion point: after the `ORIENT-FIRST PROTOCOL.` block (ends with the line "Do not paraphrase, do not silently drop options.") and before the `DISCOVERY TOOLS.` block.

## Migration (SQLite)

`backend/app/migrations/m059_mcp_user_question_rule.py` (id verified next free at drafting time, follows m058 from SPEC-176-A):

- Defensive table-exists check (matches m053, m057 patterns).
- Use `INSERT` of the new section via `REPLACE(prompt_text, ORIENT_END_MARKER, ORIENT_END_MARKER || ASKING_QUESTIONS_SECTION)` where `ORIENT_END_MARKER` is the exact closing line of ORIENT-FIRST PROTOCOL. This is surgical — does not touch other parts of the body, preserves admin customisations.
- Idempotent — REPLACE is a no-op when the substring isn't found (i.e. on subsequent runs after the section is already present, the marker no longer ends immediately before DISCOVERY TOOLS because the new section sits in between — but the seed `UPDATE` on every startup will keep the body canonical regardless).

Register in `backend/app/startup.py:_initialize_sqlite` right after `m058_up(main)`.

## Migration (Supabase)

`backend/app/migrations/supabase/m063_mcp_user_question_rule.sql` mirrors the SQLite migration with the same REPLACE-based insert.

## Seed update

`backend/app/seed/creation_prompts.py`:

- Add a `MCP_SERVER_INSTRUCTIONS_BODY` module-level constant lifted verbatim from the "Content" fenced block of `docs/prompts/mcp-server-instructions.md`.
- Inside `seed_creation_prompts`, add:
  ```python
  await db.execute(
      "UPDATE ai_creation_prompts SET prompt_text = ? "
      "WHERE id = 'mcp-server-instructions-v1'",
      (MCP_SERVER_INSTRUCTIONS_BODY,),
  )
  ```
- This makes the singleton body canonical on every backend startup. Future copy edits ship without a new migration — change the constant + the source doc, redeploy.

## Iris-mcp fallback update

`mcp/src/iris_mcp/server_instructions.py:_FALLBACK_INSTRUCTIONS`:

- Update to match the new canonical body byte-for-byte. The fallback is used when iris-mcp cannot reach `GET /api/ai/server-instructions` at startup. Day-one behaviour must match server-fetched behaviour.

## docs/prompts/mcp-server-instructions.md update

The doc's "Content (paste this into the row's `prompt_text` field)" fenced block is updated to include the new ASKING QUESTIONS section. The revision history at the foot gains a `v6.1.0` entry referencing this ADR.

## Tests

### `backend/tests/migrations/test_m059_mcp_user_question_rule.py` (new)

Three test functions:

1. `test_migration_inserts_asking_questions_section` — apply m053 (seed) then m059 (this migration) to a fresh SQLite. Query the singleton row's `prompt_text`. Assert it contains `"ASKING QUESTIONS."` and the cascade-specific bullet `"every Stage-0 setup question in a creation cascade"`.

2. `test_migration_preserves_orient_and_discovery_sections` — same setup. Assert `ORIENT-FIRST PROTOCOL.` still present, `DISCOVERY TOOLS.` still present, `AUTH RECOVERY.` still present. None of the existing sections were eaten by the insert.

3. `test_seed_overwrites_with_canonical_body` — apply migration, then call `seed_creation_prompts(db)`. Assert the row's `prompt_text` exactly equals `MCP_SERVER_INSTRUCTIONS_BODY`. Even if an admin edited the body before the seed ran (simulated by an extra UPDATE between the migration and the seed call), the seed restores canonical content.

### `mcp/tests/` updates

If `mcp/tests/test_server_instructions.py` exists and asserts on the `_FALLBACK_INSTRUCTIONS` body content, update its expected strings to include the new ASKING QUESTIONS section.

## Versioning

Shared with SPEC-176-A — both ship in v6.1.0 (this Phase 1 release bundles ADR-176 and ADR-177).

## CHANGELOG

`[6.1.0]` Changed: "MCP server-instructions body now includes an ASKING QUESTIONS section (ADR-177)." Reference both this SPEC and SPEC-176-A.

## Acceptance criteria

- [ ] Migration applies cleanly to a fresh SQLite database (after m053 seeds the singleton).
- [ ] Migration applies cleanly to a database already at m057 (existing v6.0.x deploys).
- [ ] Singleton body after migration contains ORIENT-FIRST + ASKING QUESTIONS + DISCOVERY TOOLS + WORKFLOW GUIDANCE + AUTH RECOVERY in that order.
- [ ] `seed_creation_prompts` overwrites the body with the canonical content from `MCP_SERVER_INSTRUCTIONS_BODY` on every startup.
- [ ] Iris-mcp `_FALLBACK_INSTRUCTIONS` matches the seeded body byte-for-byte.
- [ ] `pytest backend/tests/migrations/test_m059_mcp_user_question_rule.py` green.
- [ ] `pytest mcp/tests/` green.
- [ ] Post-deploy smoke: connect a fresh Claude Desktop / Claude Code session, fetch instructions, confirm the new section is present.
