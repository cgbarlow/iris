# Issue #231 — Research: replacing Claude-in-Chrome with `woolies-nz-cli` for the ordering step

**Status:** research / design — no implementation in this branch
**Scope:** the *ordering* step only. The upstream chain (photo → meal plan → `iris aggregate` → shopping list) is treated as a given; its output is the input to whatever we build here.
**Related:** issue #211 (closed, the workflow that worked but was slow), issue #231 (this), ADR-182 (Surface Parity), ADR-134 (standalone iris-mcp service).

---

## 1. Why we're looking at this

The v6.30.x meal-plan → shopping-order workflow proved end-to-end on UAT. Everything up to and including `iris aggregate` is fast and deterministic. The bottleneck is the **last mile**: handing the aggregated shopping list to Claude in the Chrome extension and asking it to drive `woolworths.co.nz` like a human. That step is:

- **Slow** — every product search is a page load + DOM scrape + LLM-mediated decision per item. ~178 grocery elements in the catalogue today; a typical weekly cart touches 25–40 of them, each costing ~5–15s of browser-driven work.
- **Fragile** — the agent has to disambiguate from a visual list, deal with banner ads, "see similar," and out-of-stock pivots. Failure modes are unbounded.
- **Expensive in tokens** — every page-load returns a large DOM that the model has to read.

[`mcinteerj/woolies-nz-cli`](https://github.com/mcinteerj/woolies-nz-cli) is an unofficial Woolworths NZ CLI that talks to the same internal `/api/v1/*` endpoints the web app uses, with a Camoufox-driven login bootstrap and cached cookies thereafter. If we can use it as the ordering rail instead, the per-item cost drops from "drive a browser" to "one HTTPS call."

---

## 2. What `woolies-nz-cli` actually gives us

Inspected at commit `0.1.1` (2026-04-25), MIT, ~7 stars, single-author hobby project. Python 3.11+, `pipx`/`uv` install, `woolies` entry point.

### Commands (from `README.md` + `pyproject.toml`)

| Command | What it does | Output |
|---|---|---|
| `woolies login` | Interactive Camoufox browser flow; persists cookies + creds | one-time, ~25s + ~300MB browser DL first run |
| `woolies logout` | Wipe creds + cookies | — |
| `woolies doctor` | Diagnose creds, paths, browser, DNS | human text |
| `woolies search "<q>" [--limit N] [--size X] [--json]` | Search products, grouped variants, dual-priced loose produce flagged | `--json` for structured |
| `woolies cart list [--json]` | Show current cart | `--json` |
| `woolies cart add <sku> <qty> [--unit Each\|Kilogram]` | Add to cart | confirmation line |
| `woolies cart update <sku> <qty>` | Set qty | confirmation |
| `woolies cart remove <sku>` | Remove item | confirmation |
| `woolies cart clear --force` | Empty cart | confirmation |
| `woolies inspect` | Visible browser w/ active session for debugging | interactive |

`--json` flag is universal on the data-bearing commands, so all output is machine-readable.

### Auth model

- Three credential sources, in resolution order:
  1. `WOOLWORTHS_USERNAME` / `WOOLWORTHS_PASSWORD` env vars (for CI / unattended).
  2. `~/.config/woolies-nz-cli/config.toml` (populated by `woolies login`, mode 0600).
  3. `password_command` in `config.toml` for 1Password / `pass` / Bitwarden integration.
- Cookies cached at `~/.local/state/woolies-nz-cli/cookies.json`. Session survives "typically a few weeks."
- Steady-state per-command latency is ~1s (httpx against the cookie-authenticated API). Camoufox only re-runs on cookie invalidation.

### What it does **not** do

- **No checkout / order submit.** It manages the trolley; the human still places the order in the browser. That's the right boundary for our use case — we want a human "check + submit" at the end anyway (per issue #211 vision: *"Claude tells me when online order ready for review. Check order, submit."*).
- **No "boosts" / loyalty-specials redemption** — the v0.1.0 release notes don't mention it. The Chrome extension demo did pick these up; if they matter, expect a gap (worth confirming once we run the CLI for real).
- **No delivery-slot booking, no payment, no address.**

### Stability disclaimer (verbatim from README, paraphrased)

> Selectors against the login page can break with no warning. Internal API payload shapes can change. Akamai fingerprinting can update. No SLA. PRs welcome.

This is significant for our architecture choice — see §4.

---

## 3. The two architecture options

The user's brief: **evaluate a Claude skill vs. extending the Iris MCP framework with a wrapper around the woolies CLI**. Both options assume the input is the aggregated shopping list already produced by `iris aggregate` (markdown, with summed quantities and resolved product names).

### Option A — Claude skill (`woolies-shop`)

A self-contained skill under `~/.claude/skills/woolies-shop/` (or vendored in this repo under e.g. `skills/woolies-shop/`). The skill is invoked by the user in any Claude Code / Claude Desktop session that already has access to the Iris MCP. It:

1. Reads the most recent aggregated shopping list from Iris (via existing `iris-mcp` tools — `list_diagrams`, `get_diagram`, or the artefact returned by `aggregate`).
2. For each line item, runs `woolies search "<name>" --json --limit 5` via Bash.
3. Picks the best match (or asks the user when ambiguous) using a small set of rules in the skill prompt: prefer exact size match, prefer in-stock, prefer non-loose where the recipe says "1 onion" etc.
4. Calls `woolies cart add <sku> <qty> [--unit ...]`.
5. Surfaces the final `woolies cart list --json` to the user with a "review and submit in browser" instruction.

```
┌──────────────────────────┐         ┌─────────────────────┐
│  Claude (skill prompt)   │         │   iris-mcp (HTTPS)  │
│  - knows the workflow    │ ──MCP──▶│   get aggregated    │
│  - reads shopping list   │         │   shopping list     │
│  - picks SKUs            │         └─────────────────────┘
│  - drives the CLI        │
│                          │         ┌─────────────────────┐
│                          │ ──bash─▶│  woolies-nz-cli     │
│                          │         │  (local install)    │
└──────────────────────────┘         └─────────────────────┘
```

**Pros**
- **Lives outside Iris.** No new Iris release, no new tests, no genericness-invariant question (ADR-214). The CI-enforced rule that Iris core contains no grocery terminology stays intact.
- **User-local secrets.** Woolies creds never leave the user's machine and never touch Iris infrastructure. The hosted iris-mcp on Render never needs them.
- **CLI churn is contained.** When `woolies-nz-cli` breaks (and per its own README, it will), the fix is `pipx upgrade` or a skill-prompt tweak. No Iris deploy.
- **Fastest to build.** A skill is a markdown file with a description and a handful of bash invocations. Days of work, not weeks.
- **Easy to retire.** If Woolworths ever ships a real API or an MCP server, the skill is deleted with no impact on Iris.

**Cons**
- **One client only at a time.** The skill is only invokable from a Claude session that has the skill installed. Not reusable from a phone, a scheduled job, or another agent without copying it.
- **Bash-coupling.** Skill prompt-engineering has to handle CLI errors (network, selectors broken, session expired). Less structured than a typed MCP tool surface.
- **No "search" reuse.** Other Iris workflows that might want price-checking or substitution suggestions can't share the woolies surface — each Claude session has to re-discover it via the skill.

### Option B — Iris MCP extension (`iris-mcp-woolies` or new tools inside `iris-mcp`)

Add tools to the iris-mcp surface that wrap `woolies-nz-cli`. Two sub-shapes worth distinguishing:

- **B1 — same process, new tools.** Add `woolies_search`, `woolies_cart_add`, etc. to `mcp/src/iris_mcp/tools.py` next to the existing 19 Iris tools. Iris core stays free of grocery terms (ADR-214) because these tools talk to *Woolworths*, not to Iris's own data — they're a third-party adapter that happens to live in the same MCP server.
- **B2 — separate MCP server, separate Render service.** Spin up `iris-mcp-woolies` as its own remote MCP. Claude Desktop adds it as a second connector. Iris-mcp doesn't change.

```
┌──────────────────────────┐         ┌─────────────────────┐
│  Claude (any client)     │ ──MCP──▶│   iris-mcp          │
│                          │         │   (Iris data tools) │
│                          │         └─────────────────────┘
│                          │
│                          │         ┌─────────────────────┐
│                          │ ──MCP──▶│ iris-mcp-woolies    │
│                          │         │   wraps woolies CLI │
└──────────────────────────┘         │   or its httpx core │
                                     └─────────────────────┘
```

**Pros**
- **Reusable surface.** Any MCP-capable client (Claude.ai, Cursor, custom agents) gets the same tools. The phone path becomes possible.
- **Typed contract.** Tool schemas force argument shapes. The model doesn't have to parse CLI output text — handlers return JSON dicts.
- **Composable with Iris tools in one session.** A model can chain `aggregate` → `woolies_search` → `woolies_cart_add` without leaving the MCP boundary.
- **OAuth piggyback (B1 only).** If the user is already authed against Iris, the same connector session covers both.

**Cons**
- **Secrets problem.** Woolies creds need to live somewhere the MCP server can reach them. For the hosted iris-mcp on Render, that means storing personal Woolworths credentials on Iris infrastructure (or making each user paste them through a tool prompt, which is its own UX disaster). The README is explicit: *credentials and cookies stay on your machine*. We'd be deliberately breaking that property.
- **Genericness invariant collision (ADR-214).** Iris's CI-enforced rule that core code paths contain no `recipe / meal / ingredient / shopping` terminology was *the* design fight of issue #211. Wrapping the Woolworths CLI in the iris-mcp server reopens that question. Even if we argue "it's an external adapter, not core," there will be terminology in tool names (`woolies_*`), descriptions, and tests that exists in `mcp/`. Not a hard violation (`woolies` isn't on the banned-word list), but it nudges Iris from "generic platform" toward "grocery-shopping product." That's a directional drift worth being explicit about.
- **Surface parity protocol (ADR-182 / §14).** Every MCP write tool must also exist as a CLI subcommand and a backend endpoint. `woolies_cart_add` has no backend behind it — it's a pure external-API adapter. We'd need a *third* documented asymmetry on top of `ask`, `delete_*`, and `move_element`. Possible, but each one weakens the protocol's enforcement value.
- **Iris release cycle inherits Woolworths' fragility.** The README says outright: selector breaks, no SLA, "patched when I can be bothered." That's fine for a personal skill. When it lives in iris-mcp, every Woolworths breakage becomes an Iris bug report. We'd be putting a hobby-grade dependency on a critical path of a project where we care about CI gates, ADRs, and CHANGELOG hygiene.
- **B1 specifically forces a transitive dependency.** `iris-mcp` would have to bundle (or optionally import) `woolies-nz-cli` + Camoufox. That's ~300MB of browser binary in worst case, plus a Python-3.11+ pin. For a backend service, that's a lot of weight.
- **B2 is cleaner but is also "build a whole new MCP service to wrap a CLI."** Effort comparable to the skill but with much more surface area (Dockerfile, Render service, OAuth, tests, deploy pipeline) for the same eventual functionality.

---

## 4. Evaluation matrix

| Axis | Option A (skill) | Option B1 (tools in iris-mcp) | Option B2 (new MCP server) |
|---|---|---|---|
| Time to first working order | days | weeks | weeks |
| Creds stay on user's machine | ✅ | ❌ (server-side or per-call) | ❌ |
| Survives Woolies breakage gracefully | ✅ — local upgrade | ❌ — Iris release | ❌ — service release |
| Reusable from non-Claude-Code clients | ❌ | ✅ | ✅ |
| Protects Iris genericness invariant (ADR-214) | ✅ | ⚠️ — directional drift | ✅ |
| Adds protocol asymmetry (ADR-182) | n/a | ❌ — needs new exemption | ❌ — needs new exemption |
| Cost to delete if it doesn't work out | trivial | non-trivial | non-trivial |
| Plays nicely if Woolworths ships an MCP | trivial swap | requires Iris release | trivial — swap the server |

---

## 5. Recommendation

**Build Option A (a Claude skill) first.** Specifically:

- **Where:** `skills/woolies-shop/` in this repo (vendored, so the workflow is reproducible by anyone cloning iris). Skill markdown + a small helper Bash script for "search top-N and pick best match" logic that's tedious to express in prompt-only form.
- **Inputs:** the diagram id (or artefact id) returned by `iris aggregate` — fed in by the user when invoking the skill, or auto-discovered as "the most recent aggregation artefact in set X."
- **Output:** an in-browser cart ready to review + submit, plus a textual diff in chat (`added: N items, ambiguous: M, out-of-stock: K`).
- **Failure mode:** when `woolies-nz-cli` breaks, the skill prints the underlying CLI error verbatim and asks the user to run `woolies doctor` or upgrade the CLI. No Iris-side fix needed.

**Reasons this is the right starting point**

1. **The win we're chasing is latency, not platform.** Replacing browser-driven shopping with `httpx` calls is a 10–100× speedup regardless of whether the orchestrator is a skill or an MCP server. Get that win cheaply first.
2. **Credential boundary.** Keeping Woolies creds local is the responsible default. Crossing that boundary should be a deliberate decision after evidence, not a default architectural choice.
3. **The Iris genericness invariant is a real asset.** ADR-214 was hard-won. The right time to put grocery-shopping code inside Iris is "never, unless we get a generic-enough abstraction for it" — same argument as the recipe / meal-plan UI living entirely in user-managed data, not in core code paths.
4. **The fragility of `woolies-nz-cli` belongs in user space.** Hobby-grade upstream, no SLA — putting it behind a versioned Iris MCP makes us responsible for breakage we can't fix.
5. **Reversibility.** If after a few weeks of skill use we discover we want this from a phone or a scheduled job, promoting the skill's logic to Option B2 (separate MCP service) is straightforward. The reverse — peeling grocery code back out of iris-mcp — is much harder.

**When to revisit (i.e. promote to Option B2 specifically, not B1)**

- We have ≥2 non-Claude-Code clients that want the same surface (a phone agent, a scheduled "auto-shop on Friday morning" job).
- The skill has been stable for ≥1 month — i.e. we have evidence the upstream CLI is reliable enough to be worth wrapping in a service.
- We're willing to operate a second Render service with the secrets-management implications.

**Why B1 (tools inside iris-mcp) is not the right promotion target even later.** The credential boundary and genericness-invariant arguments don't get better with time. If we ever want this on a server, give it its own server (B2).

---

## 6. Open questions / risks worth confirming before building

- **Does the CLI work from inside our devcontainer?** Camoufox is Linux-supported, but the ~300MB browser download + login flow has only been smoke-tested on macOS / Linux desktop. Confirm in a dev container with `woolies login` once, before committing to the skill design.
- **Boosts / loyalty-specials.** The v0.1.0 CLI doesn't mention them. If "matching the Chrome demo" requires boosts, that's a gap to flag — either submit a PR to `woolies-nz-cli`, or document the asymmetry.
- **Substitution policy.** When a SKU is out-of-stock, the Chrome agent could ask the user; the skill should do the same. Confirm the search-result JSON exposes enough info (stock status, alternative variants) to suggest replacements without another search round-trip.
- **Quantity translation.** `iris aggregate` outputs human-style quantities ("1kg pork mince", "2"). Some Woolies SKUs are per-pack, some loose with dual `--unit Each | Kilogram`. The skill's pick-best-match logic needs a small ruleset; consider whether to encode this in the `Ingredient` element template (size/unit attribute slot) so the aggregation output is closer to "ready to add to cart" already.
- **Disclaimer surfacing.** The CLI README is explicit that automated use *may* violate Woolworths' ToS. The skill should restate this on first run — the user opts in knowingly, and is encouraged to use a dedicated Woolies account.

---

## 7. Out of scope for this research

- The upstream chain (photo → meal-plan smart-markdown → `iris aggregate`). Already proven in #211.
- Generalising beyond Woolworths (Pak'n'Save, New World, Countdown AU). Each would need its own CLI/adapter; the architectural conclusion of this doc still applies (skill, not Iris-core).
- Building the skill. This branch is research only, per the issue.

---

*Branch: `research/issue-231-woolies-skill`. Author: Chris Barlow. Date: 2026-05-23.*
