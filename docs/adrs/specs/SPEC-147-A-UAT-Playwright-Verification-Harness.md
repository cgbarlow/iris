# SPEC-147-A: UAT Playwright Verification Harness

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-147-A |
| **Implements** | ADR-147 |
| **Date** | 2026-05-06 |
| **Status** | Implemented in v5.5.0 |

## How to run

```
cd frontend
npm run test:uat
```

This sets `PLAYWRIGHT_UAT=1` so the local `webServer` block in
`playwright.config.ts` is skipped (UAT is remote, no localhost
servers needed). It then runs the `uat-setup` project (signs in,
persists storageState) followed by the `uat` project (12 + 3
verification specs). Screenshots land in
`frontend/tests/e2e/uat/screenshots/`; storage state in
`frontend/tests/e2e/uat/.auth/tester.json`. Both directories are
gitignored.

## Project layout

```
frontend/
  playwright.config.ts          # adds `uat-setup` + `uat` projects
  tests/e2e/
    fixtures.ts                 # adds TESTER_USERNAME / PASSWORD / loginAsTester
    uat/
      auth.setup.ts             # one-shot sign-in
      issue-46-verification.spec.ts  # 12 specs
      issue-37-verification.spec.ts  # 3 specs
      screenshots/              # gitignored output
      .auth/                    # gitignored storageState
```

## Test list (issue #46 — UAT verification of v5.4.0/v5.4.1 fixes)

| # | Item | Assertion | Screenshot |
|---|---|---|---|
| 1 | /views toolbar | HierarchyControls's bbox.x < Select's bbox.x | `01-views-toolbar-order.png` |
| 2 | Show dropdown Views label | label visible above Diagrams checkbox | `02-show-dropdown-views-label.png` |
| 3 | +New: Package above View, indented | Package y < View y; View x > Package x | `03-newdropdown-package-above-view.png` |
| 4 | Markdown image paste | textarea value gains `![pasted-image](...)` after a synthetic `paste` event | `04-markdown-paste-image.png` |
| 5/12 | Trio dedup + Add Element hidden on BPMN | exactly 1 Link Element + 1 Add Diagram; 0 Add Element | `05-12-bpmn-trio-dedup-add-element-hidden.png` |
| 6/7 | Problems panel layout | `.bpmn-shell__problems` height ≤ 220; body scroll ≤ viewport+20 | `06-07-problems-panel-height.png` |
| 8 | ContextPad Append Task | node count grows by 1 after click | `08-contextpad-append-task.png` |
| 9 | Drag-to-connect | edge count grows; sequence_flow edge visible | `09-drag-to-connect-sequence-flow.png` |
| 10 | /elements/<id> Used in Diagrams + Relationships | both panels render | `10-element-used-in-diagrams-relationships.png` |
| 11 | EventTriggerFlyout | `.bpmn-event-flyout` visible; legal trigger count in [5,8] | `11-event-trigger-flyout.png` |

## Test list (issue #37 — BPMN canvas + API)

| Item | Assertion |
|---|---|
| BPMN canvas mounts | navigating to a BPMN view + clicking Start Building does not throw `useStore outside <SvelteFlowProvider />` (or any other pageerror) |
| `/api/bookmarks` ≤ 499 | observed via `page.on('response', ...)` during dashboard load |
| `/api/graph/settings` ≤ 499 | observed during dashboard load when fetched |

## Screenshot policy

- Each spec writes one or more PNGs labelled
  `<item-number>-<short-slug>.png`.
- `screenshot: 'only-on-failure'` is set in the project config so
  Playwright also auto-snaps on assertion failure.
- The output dir is gitignored; operators inspect locally per run.

## Skipping non-applicable specs

Tests that require pre-existing UAT data (e.g. an existing BPMN view
to drive ContextPad) call `test.skip(<predicate>, '<reason>')` so
they don't mutate the UAT environment when the seed data is absent.
This keeps the suite safe to run repeatedly.

## How to extend

When a new bug surfaces in UAT, add a spec to `tests/e2e/uat/`:

```ts
import { test, expect } from '@playwright/test';

test('issue #N: short description', async ({ page }) => {
    await page.goto('/some-route');
    // ... drive the bug ...
    await page.screenshot({ path: `tests/e2e/uat/screenshots/N-slug.png` });
    expect(...).toBe(...);
});
```

The `uat` project picks it up automatically (no manifest to update).

## Operator notes

- The tester account must already exist on the UAT site. The setup
  spec only signs in — it does NOT create the account. If the
  account is rotated, update `TESTER_USERNAME` / `TESTER_PASSWORD`
  in `frontend/tests/e2e/fixtures.ts` accordingly.
- Override the target URL via the `IRIS_UAT_URL` env var if needed
  (e.g. for staging variants).
- The runner needs Chromium installed locally. On a fresh checkout:
  `npx playwright install chromium`. On WSL2 / minimal Linux,
  `npx playwright install-deps` may need `sudo`.
