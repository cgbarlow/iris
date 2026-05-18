# ADR-196: Elements page search uses debounced abortable fetch

Status: Accepted (2026-05-18)
Related: dashboard search at `frontend/src/routes/+page.svelte:460-464`

## Context

Issue [#173](https://github.com/cgbarlow/iris/issues/173) item 7 —
on the elements page, typing "grocery" in the search box shows the
matching "Grocery item template source" element briefly, then it
"flashes away" and the user sees nothing. The same search on the
dashboard works perfectly. The user observation: *"learn from the
dashboard view."*

Cause. The elements page wired its search input to
`oninput={() => { page = 1; loadElements(); }}` — synchronous fetch
on every keystroke, no debounce, no `AbortController`. Typing
"grocery" fires 7 requests in rapid succession; the network does
not guarantee they return in order. When a slower earlier request
for `"grocer"` lands *after* the faster `"grocery"` request, the
later response is overwritten by the earlier one and the matching
result vanishes.

The dashboard's search has had a 300ms debounce since at least
v5.x (`onSearchInput` at `frontend/src/routes/+page.svelte:461-464`).
Debounce alone fixes most cases — keystrokes within 300ms of each
other don't fire — but a long tail of slow networks can still
inject a stale response, so we add an `AbortController` and a
request-time query capture as a belt-and-braces guard.

## Decision

`frontend/src/routes/elements/+page.svelte` adopts the pattern:

1. **Debounce** the search input with `onSearchInput`,
   `setTimeout(..., 300)`, mirroring the dashboard's cadence.
2. **AbortController** — `loadElements` aborts the previous
   in-flight request before issuing the next one, passing
   `{ signal }` to `apiFetch` (which already forwards `RequestInit`
   to `fetch`).
3. **Request-time query capture** — capture `searchQuery.trim()`
   into `requestedQuery` at fetch-time, and compare against the
   current `searchQuery` when the response resolves. Drop stale
   results. This catches the case where a response begins
   resolving in the JS event loop before `AbortController` fires.
4. **AbortError silencing** — a deliberately-aborted request must
   not surface as "Failed to load elements".

## Why mirror the dashboard rather than refactor both

DRY tension (Protocol §13). Two ways to spell this:

- **Inline (chosen).** Same pattern in both files. ~15 lines each.
  No new abstraction. Anyone reading either page sees the whole
  story locally.
- **Shared helper.** Extract a `debouncedFetch` / `useDebouncedLoad`
  utility into `frontend/src/lib/utils/`. Two callers today;
  third caller would push us over the DRY threshold.

The shared-helper version costs more than it saves at two callers,
because Svelte 5's `$state` is reactive at the source-file level —
the helper would have to take callbacks to read/write the page's
state, which is more indirection than the duplication. We commit
to revisiting this if a third search input needs the same shape;
the spec calls out the threshold explicitly.

## Why 300ms

Matches the dashboard. Subjectively responsive; long enough to
collapse the keystrokes of "grocery" (typed in <1s on most
keyboards) into one or two requests. Not a number worth
re-deriving.

## Consequences

- `frontend/src/routes/elements/+page.svelte` — module-level
  `searchTimeout` + `loadController`, new `onSearchInput`,
  `loadElements` aborts the previous controller and discards
  stale responses; search input `oninput` wired to
  `onSearchInput`.
- `frontend/tests/unit/elementsSearchRaceCondition.test.ts` —
  new static-parser test (10 assertions) covers debounce, abort,
  signal forwarding, AbortError handling, and the race-guard.
- No backend changes; no MCP / CLI changes.
- CHANGELOG `[6.8.5]`.

## Verification

- `npx vitest run tests/unit/elementsSearchRaceCondition.test.ts`
  — 10 green.
- Browser smoke: dev.sh, navigate to /elements, type "grocery"
  in the search box, confirm the matching element stays rendered.
  Confirm the dashboard search (which already worked) is unchanged.

## See also

- Issue [#173](https://github.com/cgbarlow/iris/issues/173) item 7.
- Dashboard search reference:
  `frontend/src/routes/+page.svelte:400-418,460-464`.
