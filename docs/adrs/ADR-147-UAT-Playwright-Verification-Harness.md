# ADR-147: UAT Playwright Verification Harness

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-147 |
| **Initiative** | E2E verification of released fixes against the live UAT site |
| **Proposed By** | Engineering |
| **Date** | 2026-05-06 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** repeated UAT-feedback releases (v5.4.0 / v5.4.1
in particular) where users reported "at least one of these bugs is
still showing up" against the live deployment despite green unit and
static-parser tests in the merge,

**facing** the gap between "static-parser test asserts the source
code claims to do X" and "live UAT actually does X end-to-end with a
real browser, network, and database",

**we decided to** add a dedicated UAT-targeted Playwright project
that:
- Drives `https://iris-uat.chrisbarlow.nz` directly via the existing
  Playwright runner.
- Signs in once as a dedicated tester account
  (`tester@test.local` / hardcoded fixture credentials, same
  convention as the existing `admin` account in `fixtures.ts`).
- Persists `storageState` so each verification spec reuses the
  authenticated session without re-logging-in.
- Takes labelled screenshots before and after each interaction so
  the operator can visually confirm correct behaviour even if an
  assertion is flaky against the live system.
- Runs **on demand only** (`npm run test:uat`), gated by
  `PLAYWRIGHT_UAT=1` so the local backend + vite preview servers
  aren't started for remote-only runs.

**to achieve** a durable verification layer that catches regressions
the merge tests can't (e.g. a Postgres migration that ships in code
but isn't applied in production, a build cache serving stale chunks,
a CDN edge that hasn't invalidated).

**accepting** that:
- The tester account credentials live in
  `frontend/tests/e2e/fixtures.ts` alongside the admin account
  credentials. Both are sandbox-scoped — the tester account exists
  only on the UAT site and has limited permissions.
- The UAT suite isn't part of CI on every PR. Running it in CI would
  require either keeping UAT permanently warm (the keep-alive
  workflow already does part of this) or accepting flaky cold-start
  failures. We prefer reliability over automation for this use case.
- Tests that need pre-existing data (a BPMN view, an element with
  edges) skip themselves when the UAT data isn't present, rather
  than mutating UAT state. This keeps the suite non-destructive.

## Reference

| Document | Purpose | Type | Link |
|----------|---------|------|------|
| SPEC-147-A | Test list, screenshot policy, run instructions | Technical Specification | [specs/SPEC-147-A-UAT-Playwright-Verification-Harness.md](./specs/SPEC-147-A-UAT-Playwright-Verification-Harness.md) |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Engineering | 2026-05-06 |
| Approved | Engineering | 2026-05-06 |
