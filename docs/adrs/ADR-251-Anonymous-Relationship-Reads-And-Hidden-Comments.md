# ADR-251: Anonymous Relationship Reads, and No Comments UI for Anonymous Visitors

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-251 |
| **Initiative** | Make anonymous (signed-out) browsing consistent: relationships readable, comments UI hidden |
| **Proposed By** | Engineering (decision by the product owner, 2026-09-24) |
| **Date** | 2026-09-24 |
| **Status** | Approved |
| **Supersedes** | ADR-249 rejected option (g) |

---

## ADR (WH(Y) Statement format)

**In the context of** anonymous read-only access (ADR-123), under which
signed-out visitors and MCP sessions can read collections, sets, packages,
diagrams and elements, and of two gaps in that experience:
(1) `GET /api/relationships` and `GET /api/relationships/{id}` still required
sign-in, so ADR-249 had to carve `list_relationships` / `get_relationship` out
of the MCP server instructions' "reads work without sign-in" promise;
(2) comments need sign-in to read *and* write, but the comments UI (panel,
Comments buttons and counts) was still shown to anonymous visitors on diagram
and element pages, so every anonymous visit ended in a
"Failed to load comments" panel from the 401, plus a wasted comments request
per page load,

**facing** the product owner's decisions of 2026-09-24 that "listing
relationships should not need signing in" and that the anonymous comments
error should be hidden,

**we decided to** (1) switch the two relationship read routes from
`get_current_user` to `get_optional_user`, exactly like element reads. Writes
(`POST`/`PUT`/`DELETE`, batch create) still need sign-in, and a
present-but-invalid token is still rejected with 401 (ADR-123 semantics). The
ADR-249 carve-outs are removed from the MCP server instructions (seed and
fallback), the two tool descriptions, `mcp/README.md` and `docs/api.md`.
(2) Hide the comments UI for anonymous visitors: `CommentsPanel` renders only
when signed in (`!isAnonymous() && canWrite(collectionId)`) and does not fetch
when anonymous. The diagram page derives `commentsAvailable = !isAnonymous()`,
gates all four Comments toggles on it, and skips the comment-count request
when anonymous. Comments themselves stay sign-in-only,

**and neglected** (a) making comments anonymously readable too. Rejected:
comments are collaboration content, often internal discussion, and nobody
asked to publish them; the owner asked only for the error to be hidden;
(b) keeping the panel but swapping the error for a "Sign in to see comments"
prompt. Rejected for now: the owner asked to hide it, and it would keep
spending an anonymous-bucket request per page view just to learn the answer
is 401. It can come back as a deliberate call-to-action later;
(c) keeping relationship reads signed-in and improving the error instead.
Rejected by the owner's decision: relationships are model structure like
elements, and hiding them from anonymous readers made public models
incomplete (e.g. an anonymous agent could see a family tree's people but not
how they connect),

**to achieve** a consistent anonymous experience: everything structural is
readable without sign-in, and anonymous visitors never see UI that can only
fail for them,

**accepting that** relationship metadata (labels, roles, `data`) becomes
public wherever the connected elements already are, which is the same
exposure as element data under ADR-123.

---

## Consequences

- No schema or MCP tool / CLI change; the surface-parity check covers writes
  only, and writes are unchanged.
- Anonymous relationship reads count against the `anon` rate-limit bucket like
  any other anonymous read.
- Anonymous diagram views make one fewer request (no comments count).

## Dependencies

- ADR-123 (anonymous read-only bypass), ADR-237 (comments hidden in read-only
  collections, which this extends to anonymous visitors), ADR-249
  (relationship tools; this supersedes its rejected option (g)).

## References

- Implementation spec: [SPEC-251-A](./specs/SPEC-251-A-Anonymous-Relationship-Reads-And-Hidden-Comments.md)
