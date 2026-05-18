# SPEC-196-A: Elements page search debounce + abort

Implements: [ADR-196](../ADR-196-Elements-Search-Debounce-Abort.md)
Resolves: Issue [#173](https://github.com/cgbarlow/iris/issues/173) item 7
Status: Living

## Shape

`frontend/src/routes/elements/+page.svelte`:

```ts
let searchTimeout: ReturnType<typeof setTimeout> | undefined;
let loadController: AbortController | undefined;

function onSearchInput() {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    page = 1;
    loadElements();
  }, 300);
}

async function loadElements() {
  loadController?.abort();
  loadController = new AbortController();
  const controller = loadController;
  const requestedQuery = searchQuery.trim();
  loading = true;
  try {
    // …build params…
    const data = await apiFetch<…>(`/api/elements?${params}`, { signal: controller.signal });
    if (requestedQuery !== searchQuery.trim()) return;  // race guard
    elements = data.items;
    total = data.total;
    loadAvailableTags();
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') return;
    error = 'Failed to load elements';
  } finally {
    if (controller === loadController) loading = false;
  }
}
```

Search input markup:
```svelte
<input id="element-search" bind:value={searchQuery} oninput={onSearchInput} type="search" … />
```

The `loading = false` is guarded by `controller === loadController`
so an aborted older controller doesn't clear the spinner while the
newer request is still in-flight.

## Acceptance criteria

1. Typing a single character that matches an element shows the
   element and it stays rendered.
2. Typing "grocery" character-by-character within ~1s yields the
   final result set rendered exactly once, with no flash of stale
   results.
3. Rapidly toggling between search and filter (notation /
   collection / set) does not leave the spinner stuck on; loading
   reflects the newest request.
4. Network errors on the newest request still surface as "Failed
   to load elements".
5. The dashboard search at `frontend/src/routes/+page.svelte` is
   not modified — its behaviour is reference-only.

## DRY threshold (revisit trigger)

Two callers (dashboard + elements page) use this pattern inline.
**On the third caller**, extract to
`frontend/src/lib/utils/debounced-fetch.ts` with a generic
`createDebouncedLoader<T>(...)` and refactor both existing call
sites in the same PR. The signature should accept (a) a request
builder, (b) a response handler, (c) a debounce ms, (d) an
identity check for the race guard.

## Tests

`frontend/tests/unit/elementsSearchRaceCondition.test.ts` —
10 cases:

1-5. **Debounce.** `searchTimeout` declared, `onSearchInput`
   exists, `setTimeout(..., 300)`, `clearTimeout(searchTimeout)`,
   input wired to `onSearchInput`.
6-9. **Abort.** `loadController` declared, `abort()` called at
   start of `loadElements`, `signal` passed to `apiFetch`,
   `AbortError` handled.
10. **Race guard.** A `requestedQuery` / `searchAtRequest` /
   `capturedQuery` local is compared on response.

## Verification

```
npx vitest run tests/unit/elementsSearchRaceCondition.test.ts
```

Green. Manual smoke per ADR-196 verification section.
