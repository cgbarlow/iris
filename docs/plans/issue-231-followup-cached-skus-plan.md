# Plan — woolies-shopper v0.2.0 (phased pipeline) + Iris aggregate provenance

## Context

The woolies-shopper v0.1.0 skill (just shipped, `cgbarlow/skills#12`) replaced the slow Chrome-extension cart-building step with `woolies-nz-cli` — a 10–100× per-item speedup over driving the browser. The next efficiency win comes from realising that **most weekly shops are dominated by repeat purchases.** If the resolved Woolworths SKU is cached on each grocery item from the first shop onward, every subsequent shop can skip the search+pick+ambiguity-prompt loop and go straight to `woolies cart add`. The LinkedIn post for cgbarlow/iris#211 promised "each time we go shopping it refines the information, learns, and gets better" — this is the mechanism that delivers that.

The architectural insight from the riff: most of phase 2 doesn't need an LLM at all. A bash orchestrator can bulk-add cached SKUs deterministically, and only invoke Claude (via the woolies-shopper skill, now re-scoped) when there are exceptions to resolve. Steady-state shops with high cache-hit rates burn zero LLM tokens on the bulk-add phase.

Data-model fit: each Ingredient element has multiple **Product** attributes (one per real-world buyable variant; preferred-ordering by array position; v6.30.1 made the per-attribute `notes` field UI-editable). The SKU lives in each Product attribute's notes, using a parseable `woolies:NNN | confirmed:YYYY-MM-DD` convention. The skill walks the Product attributes in preferred order, trying each cached SKU until one succeeds.

The user runs the whole thing from a regular terminal — no inside-Claude-Code-mobile question to answer.

## Scope: three deliverables across two repos

| # | Repo | Deliverable | Depends on |
|---|---|---|---|
| 1 | `cgbarlow/iris` | Aggregate output provenance flag — `OutputConfig.include_provenance: bool` opt-in that appends `<!-- iris:element=<uuid> -->` to each rendered line | — |
| 2 | `cgbarlow/skills` | `shop.sh` master orchestrator + `phase2_bulk_add.sh` (pure bash, uses `iris` CLI + `woolies` CLI) | (1) for cache-hit path; degrades gracefully without it |
| 3 | `cgbarlow/skills` | Skill v0.2.0 re-scope: tighten `description` so it only triggers as an exception resolver, not a "do the whole shop" entry point | — (but ships with #2) |

## Deliverable 1 — Iris aggregate provenance (`cgbarlow/iris`)

### What changes

**Single small enhancement, opt-in per aggregation profile.** A new `include_provenance: bool = False` flag on `OutputConfig` causes `_render_line` (`backend/app/aggregation/engine.py:441-455`) to append an HTML comment to each emitted line carrying the element_id. The element_id is already in the rendering context (`r.token_id`, passed at engine.py:520) — this is just plumbing it into the output template.

Final shape:

```markdown
## Produce

- Carrots: 3 <!-- iris:element=8f3c4d2e-… -->

## Meat & Poultry

- Pork mince: 500 g <!-- iris:element=2a91b0d5-… -->
```

The HTML comment renders invisibly in markdown; the bash phase-2 orchestrator regexes it out. No retailer-specific code in Iris core (ADR-214 stays clean) — Iris only knows about element provenance; the SKU lookup happens skill-side from each Product attribute's notes.

### Critical files

- `backend/app/aggregation/models.py` — add `include_provenance: bool = False` to `OutputConfig` (line 57-64). Mirrors the existing `show_per_source_breakdown` flag pattern.
- `backend/app/aggregation/engine.py:441-455` — `_render_line` reads `output.include_provenance`; when true, appends ` <!-- iris:element={element_id} -->`. `_format_output` (line 472-529) passes the `output` config in already.
- `backend/tests/test_aggregation/test_engine.py` — TDD: new test cases for the flag's on/off behaviour. Use the existing `test_group_by_package_name` (line 365-415) as the fixture template.

### Out of scope for the Iris PR

- **Updating any seeded aggregation profile to set the flag.** Users opt-in per profile via the existing `update_aggregation_profile` MCP/CLI surface; no paired migration needed in this PR. (A future PR can flip the seeded shopping-list profile if you want the default to change — that one IS a paired migration.)
- **Surfacing cached SKU notes directly in the markdown.** Phase 2 fetches the element's Product notes via `iris elements get`. Embedding the SKU in the aggregate output would put retailer-shaped data in Iris's response — drift toward ADR-214 risk. Element_id only.

### Protocol mapping for the Iris PR

| § | Protocol | Application |
|---|---|---|
| 1 | ADR | New: `ADR-NNN-Aggregate-Output-Provenance.md`. Captures the opt-in flag decision and the explicit rejection of "embed retailer SKU in output" alternative. |
| 2 | Spec | New: `SPEC-NNN-A-Aggregate-Output-Provenance.md` referencing the ADR. Defines the HTML-comment format and the OutputConfig flag. |
| 3 | TDD | ✅ tests in `test_aggregation/test_engine.py` first (red → green → refactor). |
| 4 | Feature branch | `feature/aggregate-provenance` in iris. |
| 5 | Changelog | `[Unreleased] Added: aggregate output provenance flag (ADR-NNN)`. |
| 6 | Release | Version bump per the four-version-bump discipline ([[feedback_iris_version_bump_discipline]]). Frontend + backend + mcp + iris-client. Likely v6.31.0 (minor — new feature, additive). |
| 7 | `{@html}` | N/A — no frontend change. |
| 8 | Context7 MCP | Not needed; engine code is well-understood. |
| 9 | Production-ready | ✅ no stubs. |
| 10 | Agent teams | ✅ Phase 1 exploration used 2 parallel Explore agents. |
| 11 | Latest stable deps | N/A — no new deps. |
| 12 | README accuracy | Update `docs/mcp.md` and `docs/cli.md` aggregate sections to mention the flag. |
| 13 | DRY | ✅ Both MCP `aggregate` tool and `iris aggregate` CLI hit the same `_engine.run()` → same `_format_output()`. No duplication. |
| 14 | Surface parity | ✅ no new write endpoints. The flag is a config field on an existing profile that's already mutable via `update_aggregation_profile` (MCP + CLI both exist). Parity check passes without exception. |
| 15 | SQLite/Supabase parity | ✅ no migration in this PR. (If a future PR flips a seeded profile, that one needs paired m{NNN}*.py + m{NNN}*.sql.) |

## Deliverable 2 — `shop.sh` orchestrator (`cgbarlow/skills`)

### What changes

New entry point at `skills/woolies-shopper/scripts/shop.sh`. Three-phase pipeline, fresh `claude` session per phase, state hands off through files in `${SHOP_STATE_DIR:-/tmp/shop-$(date +%Y-%m-%d-%H%M)}/`:

```
shop.sh
├── phase 1 — interactive `claude` session
│     Prompt: "I'm starting the weekly Woolies shop. Please ask me to
│     upload a photo of this week's meal plan; OCR it; create the meal
│     plan diagram in Iris; run `iris aggregate` against the shopping-
│     list profile against the new diagram; print the resulting diagram
│     id on a line beginning with `DIAGRAM_ID=`."
│     The session uses the existing Iris MCP. User exits when done.
│   Master script greps `DIAGRAM_ID=…` from the transcript → manifest.
│
├── phase 2 — pure bash, no LLM
│     `phase2_bulk_add.sh <diagram_id> <state_dir>`
│       a. `iris export diagram <diagram_id>` → markdown body
│       b. Parse each line. Regex the HTML-comment element_id (when
│          present). Lines without an element_id are pushed straight
│          to exceptions (phase 1 produced no provenance — graceful
│          degradation; user just gets a phase-3 prompt for those).
│       c. For each line with element_id:
│            `iris elements get <element_id>` → JSON
│            walk `data.attributes[]` in order, picking each row whose
│            name is "Product" — preferred is index 0.
│            for each Product row in order:
│              parse `notes` for `woolies:NNN`; if absent, skip row.
│              `woolies cart add <sku> <qty> --unit <Each|Kilogram>`
│              on success → update `confirmed:YYYY-MM-DD` on this row
│                            via get-merge-put through `iris update
│                            element`; record the line as added; break.
│              on stock-out / 404 → try next Product row.
│            if all Product rows fail → push to exceptions.json with
│              the line + element_id.
│       d. Emit `cart-result.json` (added/skipped/substituted tally)
│          and `exceptions.json` (lines requiring phase 3).
│
└── phase 3 — conditional `claude` session
      Triggered only if `exceptions.json` is non-empty.
      `claude -p "Resolve these woolies shopping exceptions: $(cat
      $STATE_DIR/exceptions.json). Use the woolies-shopper skill. For
      each line: search woolies, pick / ask user / handle OOS as the
      skill defines, cart add, write any new SKU back to the relevant
      Product attribute's notes via `iris update element`."
      The woolies-shopper skill (v0.2.0, see Deliverable 3) handles
      this end-to-end.
```

### Critical files (new)

- `skills/woolies-shopper/scripts/shop.sh` — master orchestrator (~60 lines bash).
- `skills/woolies-shopper/scripts/phase2_bulk_add.sh` — pure bash bulk-add (~120 lines, uses `jq` for JSON manipulation per the iris CLI dance the Explore agent flagged).
- `skills/woolies-shopper/scripts/lib/iris_attr_update.sh` — helper for the get-merge-put attribute-notes-update pattern (reused between phase 2 and the skill in phase 3 — §13 DRY).
- `skills/woolies-shopper/tests/test_phase2.sh` — TDD: fixture-driven bash tests. Use `bats` if available; otherwise stdlib `set -e` + `diff` against expected output.
- `skills/woolies-shopper/tests/fixtures/aggregate-output.md` — realistic aggregate output (with HTML comments).
- `skills/woolies-shopper/tests/fixtures/element-chilli-beans.json` — sample element with multiple Product attribute rows + cached SKUs in notes.

### Existing code reused

- `scripts/install.sh` and `scripts/doctor.sh` — unchanged; `shop.sh` calls `doctor.sh` at top.
- `scripts/pick.py` — unchanged; only the skill (phase 3) uses it.
- `tests/test_pick.py` + fixtures — unchanged.

### Out of scope

- **Cron / `/schedule` integration.** User invokes manually from terminal. Scheduling can be wrapped around it later (just a cron line invoking `shop.sh`) — no orchestrator change required.
- **Phase 1 automation of the photo step.** User uploads via Claude conversation in the phase-1 session. No file-watcher / Dropbox integration.
- **Multi-retailer support.** Convention is `woolies:NNN`; future-proofed but only Woolies is implemented.

## Deliverable 3 — Skill v0.2.0 re-scope (`cgbarlow/skills`)

### What changes

The skill's role narrows: it's no longer the entry point for "do the shopping" — that's `shop.sh`. It's the exception resolver invoked by phase 3.

- **SKILL.md frontmatter `description`** — re-pitch so Claude triggers it for "resolve these shopping exceptions" / "deal with this OOS item / unknown SKU" prompts, not for "do my shopping." The hostile case to avoid: a user types "do my shopping" into a bare Claude session (no `shop.sh`), the skill triggers, and ignores the orchestrator + cache. v0.2.0 description steers Claude to recommend running `shop.sh` from the terminal instead.
- **SKILL.md body** — drop the "Locate the shopping list" and "Parse the aggregated list" sections (phase 2 does this). Keep: preflight, search+pick, cart-add for the exception line, **NEW** writeback of newly-discovered SKUs to the relevant Product attribute's `notes` via `iris update element`, summary.
- **scripts/pick.py and tests** — no functional change.
- **CHANGELOG.md** — `## [0.2.0] — YYYY-MM-DD — Re-scope as exception resolver; add `shop.sh` orchestrator; SKU writeback via Product attribute notes.`
- **marketplace.json** — bump cgbarlow-skills version (e.g. 2.4.0 → 2.5.0).
- **README.md** — explain the new entry-point (`shop.sh` from terminal) + the skill's narrower role.

### Skill writeback authentication

Phase 3 is the first write the skill performs against Iris. Today's skill is read-only against the MCP. The writeback uses the `iris` CLI (not MCP) per the agreed split — phase 3 shells out to `iris update element`. That requires the user's local `iris` CLI to be authenticated (`iris login` once, PAT cached). Add to install.sh: a `iris doctor` style check that surfaces if the iris CLI isn't logged in.

## Protocol mapping for the skill PR

Same approach as v0.1.0 — the cgbarlow/skills repo doesn't have an `adrs/` tree, so several Iris protocols are partial-application or N/A. Mapping:

| § | Applies? | How honoured |
|---|---|---|
| 1 ADR | Partial — design captured in this plan + the Iris-side ADR-NNN. No skill-repo ADR tree exists. |
| 2 Spec | Partial — SKILL.md is the spec. |
| 3 TDD | ✅ `tests/test_phase2.sh` first, fixture-driven. Skill prompt itself isn't unit-testable — eval cases in `evals/evals.json` updated for the new scope. |
| 4 Feature branch | `feature/woolies-shopper-v0.2.0` in cgbarlow/skills. |
| 5 Changelog | ✅ per-skill `CHANGELOG.md` + marketplace version bump. |
| 6 Release | ✅ `v0.2.0` recorded in skill CHANGELOG; marketplace `2.4.0 → 2.5.0`. Tag if existing convention. |
| 8 Context7 | Not needed. |
| 9 Production-ready | ✅ no stubs in shop.sh or phase2_bulk_add.sh. |
| 11 Latest stable deps | ✅ confirm `woolies-nz-cli==0.1.1` is still PyPI latest at build time. |
| 12 README accuracy | ✅ skill README updated to reflect `shop.sh` entry-point + new scope. |
| 13 DRY | ✅ `scripts/lib/iris_attr_update.sh` reused between phase 2 and phase 3 skill writeback. |
| 14 Surface parity | N/A — Iris-specific. |
| 15 SQLite/Supabase parity | N/A — no DB. |

## Build flow (when execution begins)

Two PRs, parallelisable. Iris ships first if possible (unblocks the cache-hit code path); skill ships in parallel and degrades gracefully without it.

### Iris PR (`feature/aggregate-provenance` in `cgbarlow/iris`)

1. Branch off main. Open issue first: "ADR-NNN: Aggregate output provenance flag for downstream orchestrators."
2. Write ADR + SPEC.
3. TDD `OutputConfig.include_provenance`: add tests in `test_aggregation/test_engine.py` for flag-off (no change) and flag-on (HTML comment appended). Red.
4. Implement: 1-line addition to `OutputConfig`, ~5-line addition to `_render_line`. Green.
5. Update `docs/mcp.md` + `docs/cli.md` aggregate sections.
6. Run `scripts/check_surface_parity.py` (should pass without exception).
7. Bump all four versions per [[feedback_iris_version_bump_discipline]]. CHANGELOG `[Unreleased]` → `[v6.31.0]`.
8. PR; merge to main after CI green. Deploy to UAT (auto via Render). Per [[feedback_iris_merge_and_migration_authority]] no migration here so no `supabase-migrate.sh` step.
9. **User-side step**: in the Iris UI (or via `iris aggregation-profile update`), flip `include_provenance: true` on the shopping-list profile. (Or skip if you want to wait for the future seed-update PR.)

### Skill PR (`feature/woolies-shopper-v0.2.0` in `cgbarlow/skills`)

1. Branch off main. Open issue: "woolies-shopper v0.2.0: phased bash orchestrator + exception-resolution scope."
2. TDD `phase2_bulk_add.sh` against the fixture aggregate-output.md + fixture element JSON. Red → green.
3. Write `shop.sh` (master). Smoke-test phases 1 + 2 against UAT Iris with a small known meal plan.
4. Update SKILL.md: re-scope description + body, add writeback step.
5. Update README.md + CHANGELOG.md (v0.2.0).
6. Bump marketplace.json (2.4.0 → 2.5.0).
7. PR. Once iris PR is on UAT, end-to-end test on a real shop. Merge per the same self-PR + merge pattern as v0.1.0.

## Verification (end-to-end)

1. **Iris-side unit**: `pytest backend/tests/test_aggregation/test_engine.py -k provenance` → green.
2. **Iris-side smoke**: `iris aggregate --profile <shopping-list-id> --source <meal-plan-id>` against a UAT meal plan with the profile's `include_provenance: true` → markdown body contains `<!-- iris:element=... -->` per line.
3. **Skill-side unit**: `cd skills/woolies-shopper && bash tests/test_phase2.sh` → green.
4. **Skill-side existing tests**: `python3 -m unittest discover -s tests` → still 10/10 green (v0.1.0 picker tests unchanged).
5. **End-to-end on a real shop**:
   - First-run: empty Product notes everywhere. Phase 2 should push everything to phase 3 (no cached SKUs). Phase 3 resolves all items; each successful pick writes back a SKU to the relevant Product attribute's notes.
   - Second-run a few days later, same meal plan: phase 2 should hit ~100 % cache hit rate, run in ~30s of pure HTTPS, exceptions.json should be empty, no phase 3 needed.
   - Force an exception: temporarily edit a Product's notes to point at a known-OOS SKU, run again. Phase 2 detects the failure, walks to next Product (or pushes to exceptions if none), phase 3 resolves.
6. **Cache writeback check**: after a successful first-run, open the affected Ingredient elements in the Iris UI — Product attribute notes should show `woolies:NNN | confirmed:2026-05-24` for each Product the skill picked.
7. **Graceful degradation check**: skill PR works against the OLD aggregate output (no HTML comment). Phase 2 detects no element_id per line, routes everything to phase 3 exceptions. Whole workflow still completes, just without the cache-hit fast path. This is the deploy-ordering safety net (skill can ship before / without the Iris PR).

## Open items the user resolves during build (not pre-decision)

- **iris CLI auth in `install.sh`** — add an `iris doctor`-style check; if not logged in, prompt user to run `iris login`. Discovered while writing phase 3 writeback; no impact on overall design.
- **`jq` dependency** — phase 2's get-merge-put attribute-update dance needs `jq`. Add to install.sh dependency check.
- **shop.sh slash-command convenience** — if the user wants `/shop` to invoke `shop.sh` in any Claude Code session, that's a separate Claude Code custom command, not a skill change. Defer.
- **Cron scheduling** — `0 8 * * 6 /path/to/shop.sh` in user's crontab. Out of scope; documented in README only.

## Critical files (consolidated)

**Iris repo (`feature/aggregate-provenance`):**
- `backend/app/aggregation/models.py` (edit)
- `backend/app/aggregation/engine.py:441-455` (edit)
- `backend/tests/test_aggregation/test_engine.py` (edit)
- `docs/adrs/ADR-NNN-Aggregate-Output-Provenance.md` (new)
- `docs/adrs/specs/SPEC-NNN-A-Aggregate-Output-Provenance.md` (new)
- `docs/mcp.md`, `docs/cli.md` (edit — aggregate section)
- `CHANGELOG.md` (edit)
- `frontend/package.json` + `backend/pyproject.toml` + `mcp/pyproject.toml` + `iris-client/pyproject.toml` (version bumps)

**Skill repo (`feature/woolies-shopper-v0.2.0`):**
- `skills/woolies-shopper/scripts/shop.sh` (new)
- `skills/woolies-shopper/scripts/phase2_bulk_add.sh` (new)
- `skills/woolies-shopper/scripts/lib/iris_attr_update.sh` (new — DRY helper)
- `skills/woolies-shopper/scripts/install.sh` (edit — add iris CLI + jq checks)
- `skills/woolies-shopper/tests/test_phase2.sh` (new)
- `skills/woolies-shopper/tests/fixtures/aggregate-output.md` (new)
- `skills/woolies-shopper/tests/fixtures/element-*.json` (new — Product-attribute fixtures)
- `skills/woolies-shopper/SKILL.md` (edit — re-scope)
- `skills/woolies-shopper/README.md` (edit)
- `skills/woolies-shopper/CHANGELOG.md` (edit — v0.2.0)
- `skills/woolies-shopper/evals/evals.json` (edit — exception-resolution scope)
- `.claude-plugin/marketplace.json` (edit — 2.4.0 → 2.5.0)
