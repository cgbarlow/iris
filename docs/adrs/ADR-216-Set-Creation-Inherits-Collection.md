# ADR-216: Set creation inherits the active collection filter

Status: Accepted (2026-05-22)

Builds on: [ADR-126 / sets-collections] (existing collection scoping).

## Context

The sets list page (`/sets`) supports a `?collection_id=<id>` URL filter and an in-memory active-collection store (the chip at the top of many pages). When a user is viewing sets filtered by a collection and clicks "Create new set", the new set is currently created with `collection_id = NULL`, dropping it out of the filter view. The user then has to navigate to the new set and re-attach it via the set's edit page. Friction reported on the [2026-05-22 issue #211 comment](https://github.com/cgbarlow/iris/issues/211).

## Decision

When the user is viewing the sets list with an active collection filter (URL query param `collection_id` or active-collection-store value), the "Create new set" action passes that collection id through to the backend in the `POST /api/sets` body.

Backend behaviour is unchanged — `SetCreate` already accepts `collection_id: str | None = None`. This is a one-line frontend change.

### Scope

- Active collection filter on `/sets` → carried through.
- Sets created from the unfiltered list (`/sets` with no collection filter) → still collection-less (current behaviour preserved).
- `/collections/{id}` page doesn't currently have a create-set affordance — out of scope. If one is added later, it should follow the same pattern.

## Consequences

**Positive:** Closes the reported UX gap. The user's mental model — "I'm working in this collection; new sets live here" — is honoured.

**Negative / accepted trade-offs:** A user with a stale collection filter on `/sets` who didn't realise it was active might create a set "in" that collection unintentionally. The active filter chip is visible at the top of the page, so the surface is honest about scope; we accept this small risk.

## References

- [SPEC-216-a — code change, edge cases, test](./specs/SPEC-216-a-Set-Creation-Inherits-Collection.md)
- [`docs/plans/issue-211-comment-followups.md`](../plans/issue-211-comment-followups.md) §4
