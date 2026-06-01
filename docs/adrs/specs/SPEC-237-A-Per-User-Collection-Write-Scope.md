# SPEC-237-A: Per-User Collection Write-Scope

Implements **[ADR-237](../ADR-237-Per-User-Collection-Write-Scope.md)**.

## 1. Data model

Table `user_collection_scope` (SQLite `m082`, Supabase mirror `m088`):

| column | SQLite | Supabase | notes |
|--------|--------|----------|-------|
| `user_id` | `TEXT REFERENCES users(id)` | `UUID REFERENCES profiles(id) ON DELETE CASCADE` | the scoped user |
| `collection_id` | `TEXT REFERENCES collections(id)` | `TEXT REFERENCES public.collections(id)` | a writable collection |
| `created_at` | `TEXT DEFAULT (datetime('now'))` | `TIMESTAMPTZ DEFAULT NOW()` | |

`PRIMARY KEY (user_id, collection_id)`, index `idx_ucs_user`. Supabase enables
RLS (per the post-m030 posture; the backend connects out-of-band). Both halves
idempotent. **Assignment is performed directly in Supabase** — Iris exposes no
write surface for it.

**Semantics.** No rows for a user ⇒ *unscoped* ⇒ writes everywhere (pre-ADR-237
behaviour). Rows present ⇒ writes only in those collections. Admins always
bypass.

## 2. Enforcement (`backend/app/authz/`)

- `load_scope(db, user_id) -> set[str]` — the user's writable collection ids
  (empty = unscoped). Positional row access.
- `collection_resolver.collection_of_{set,package,diagram,element,template}` and
  `collection_of_entity(entity_type, id)` — resolve a write target's owning
  collection id (lightweight FK lookups, `is_deleted`-agnostic). `None` ⇒ no
  owning collection (global template, un-grouped/default set).
- `enforce.assert_write_allowed(db, user, collection_id)` — `403 "Outside your
  collection write-scope"` unless admin, unscoped, or `collection_id ∈ scope`.
  `collection_id is None` ⇒ denied for scoped users.
- `enforce.assert_unscoped_or_admin(db, user)` — `403` for any scoped non-admin.

## 3. Gated write endpoints

`assert_write_allowed` (resolve owning collection) on:
collections `PUT`/thumbnail; sets `POST`(body collection)/`PUT`(both source +
destination on move)/`DELETE`/thumbnail; packages `POST`/`PUT`/`DELETE`/`PUT
…/parent`; diagrams `POST`/`PUT`/`DELETE`/`PUT …/parent`/`rollback`/`reorder`/
tags; elements `POST`/`PUT`/`DELETE`/`rollback`/tags; element_templates
`PUT`/`DELETE`; comments create/update/delete (via target element/diagram);
entity-image attach/detach (`collection_of_entity`); diagram-link delete (via
source diagram).

`assert_unscoped_or_admin` on: collection `POST`(create) and `DELETE`;
element_template `POST` when `is_global` and `PUT` that sets `is_global`.

## 4. Client surface

- `GET /api/auth/me` → adds `write_scope: string[] | null` (null = unrestricted;
  admins and unscoped users → null; scoped → sorted collection ids).
- Element & diagram read responses add `collection_id`.
- Frontend auth store: `isScoped()`, `canWrite(collectionId)`. Affordances gated:
  New/Edit/Delete collection (hidden when `isScoped()`); collection/set Save +
  image editors and element/set/diagram edit + delete (`canWrite(collection_id)`);
  `CommentsPanel` hidden entirely when `!canWrite(collectionId)`.

## 5. Acceptance tests (`backend/tests/test_authz/`)

Scoped user writes inside scope (201/200) / 403 outside; element update gated by
collection; unscoped user unaffected; admin bypasses even with scope rows;
cannot create or delete a collection; cannot create a global template; set move
across the boundary denied; comment create gated; reads unaffected;
`/api/auth/me.write_scope` for scoped/unscoped/admin. Plus the migration
schema-mirror test. `check_surface_parity` stays green.
