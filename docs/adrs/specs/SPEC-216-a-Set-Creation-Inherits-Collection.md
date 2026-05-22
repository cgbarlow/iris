# SPEC-216-a: Set creation inherits the active collection filter

Implements: [ADR-216](../ADR-216-Set-Creation-Inherits-Collection.md).

## 1. Change

In `frontend/src/routes/sets/+page.svelte::handleCreate`:

```diff
-async function handleCreate(name: string, description: string | null) {
-    try {
-        await apiFetch<IrisSet>('/api/sets', {
-            method: 'POST',
-            body: JSON.stringify({ name, description }),
-        });
+async function handleCreate(name: string, description: string | null) {
+    const body: Record<string, unknown> = { name, description };
+    if (collectionId) {
+        body.collection_id = collectionId;
+    }
+    try {
+        await apiFetch<IrisSet>('/api/sets', {
+            method: 'POST',
+            body: JSON.stringify(body),
+        });
```

`collectionId` is already derived on the page (line 29):

```ts
let collectionId = $derived(
  page.url.searchParams.get('collection_id')
  || getActiveCollectionId()
  || ''
);
```

So a truthy value means the user has an active filter — either from the URL query param or the in-memory active-collection store. Empty string means no filter; the create payload omits `collection_id` entirely (preserving the current "collection-less set" outcome).

## 2. Backend

Unchanged. `backend/app/sets/models.py::SetCreate.collection_id` is already `str | None = None`. `POST /api/sets` already routes it through `create_set(... collection_id=...)`.

## 3. Tests

`frontend/tests/unit/setCreateInheritsCollection.test.ts`:

- Body shape when `collectionId` is non-empty → `{name, description, collection_id}` present.
- Body shape when `collectionId` is empty → no `collection_id` key in the body (omitted, not null).

These are data-shape tests aligned with the repo's existing frontend testing posture.

## 4. Out of scope

- A create-set button on `/collections/{id}` if one is added later — follow the same pattern.
- Allowing the user to *override* the inherited collection at create time. Today they can't change it; they'd have to edit the set after creation. Could be a future enhancement.
