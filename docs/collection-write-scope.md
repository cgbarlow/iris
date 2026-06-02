# Collection Write-Scope — Operator Runbook

How to confine a user's **write/edit** permissions to a specific list of
collections. Background and rationale: [ADR-237](adrs/ADR-237-Per-User-Collection-Write-Scope.md)
and [ADR-238](adrs/ADR-238-Write-Scope-Consistency-And-Completeness.md),
spec: [SPEC-237-A](adrs/specs/SPEC-237-A-Per-User-Collection-Write-Scope.md).

## What it does

A user keeps their **global role** (e.g. `architect`) but, once they have any
rows in the `user_collection_scope` table, their **writes are confined to those
collections** — everywhere else they are read-only.

- **Role decides *what*** they can do (architect = create/edit/delete; viewer =
  read only). **Scope decides *where*** that applies.
- **No scope rows ⇒ unrestricted** — the role applies everywhere (the default,
  pre-ADR-237 behaviour).
- **Admins always bypass** scope.
- A scoped user **cannot create or delete collections**, nor edit global element
  templates, *even inside their scope* — they work within assigned collections,
  not on the containers.
- **Reads are never restricted** — a scoped user can still view everything; only
  writes are gated (API returns `403`, and the web UI hides Edit/Save/Delete and
  the comments box outside their scope).
- **Edits happen inside a set/collection context** (ADR-238): a scoped user works
  within their collections via the in-collection hierarchy/canvas. Root-level
  "New Set/View/Element" buttons are hidden for scoped users, and an out-of-scope
  view opens read-only (no canvas Edit). Creating content under a package files it
  in that package's set — so it stays in the right collection.

> A scope on a **viewer** has no effect — viewers can't write anywhere anyway.
> To give someone "architect on these collections only", set their role to
> `architect` **and** add the scope rows.

## Where scope is managed

Assignment is **data**, managed **directly in Supabase** (SQL editor or
dashboard) — there is no Iris API/MCP/CLI for it by design. Iris only reads and
enforces the rows.

## Assigning scope (Supabase / PostgreSQL)

All queries key the user by **email via `auth.users`** — Supabase stores email
there, while `profiles.username` may be a display name rather than the email.

### 1. Find the user and confirm their role

```sql
select p.id, p.username, p.role, u.email
from profiles p
join auth.users u on u.id = p.id
where u.email = 'person@example.com';
```

You want exactly one row. If `role` is not the write-capable role you intend
(e.g. it's `viewer`), set it — scope on a viewer does nothing:

```sql
update profiles set role = 'architect'
where id = (select id from auth.users where email = 'person@example.com');
```

### 2. Confirm the target collection names

```sql
select id, name, is_deleted from collections
where name in ('Collection A', 'Collection B');
```

Expect one row per collection, `is_deleted = false`. If you get fewer, the names
differ (check spacing/casing) — adjust the strings to what this returns.

### 3. Add the scope rows

```sql
insert into user_collection_scope (user_id, collection_id)
select p.id, c.id
from profiles p
join auth.users u on u.id = p.id
cross join collections c
where u.email = 'person@example.com'
  and c.name in ('Collection A', 'Collection B')
  and c.is_deleted = false
on conflict (user_id, collection_id) do nothing;
```

Idempotent — safe to re-run. (Don't add a `p.role = '…'` filter here: if the
role doesn't match it silently inserts nothing.)

### 4. Verify

```sql
select c.name
from user_collection_scope ucs
join profiles p   on p.id = ucs.user_id
join auth.users u on u.id = p.id
join collections c on c.id = ucs.collection_id
where u.email = 'person@example.com'
order by c.name;
```

Should list exactly the collections you assigned.

## Changing or removing scope

- **Add another collection:** re-run step 3 with the new name.
- **Remove one collection** (keep the rest scoped):

  ```sql
  delete from user_collection_scope
  where user_id = (select id from auth.users where email = 'person@example.com')
    and collection_id = (select id from collections where name = 'Collection B');
  ```

- **Make them a full (unrestricted) member again** — delete *all* their rows:

  ```sql
  delete from user_collection_scope
  where user_id = (select id from auth.users where email = 'person@example.com');
  ```

## Release note (§15)

The `user_collection_scope` table ships in Supabase migration
`m088_user_collection_scope.sql` (mirrors SQLite `m082`). Apply it with
`scripts/supabase-migrate.sh` **before** rolling out the code that reads it
(`/api/auth/me` and the write guards), so there's no missing-table window.

## SQLite / self-hosted mode

Same table and semantics, but the user store is the `users` table (not Supabase
`auth.users`/`profiles`). Resolve the user directly:

```sql
insert into user_collection_scope (user_id, collection_id)
select u.id, c.id
from users u
cross join collections c
where u.username = 'person'
  and c.name in ('Collection A', 'Collection B')
  and c.is_deleted = 0
on conflict (user_id, collection_id) do nothing;
```
