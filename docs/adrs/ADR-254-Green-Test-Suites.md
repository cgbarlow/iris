# ADR-254: Bring the Test Suites Back to Green

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-254 |
| **Initiative** | Fix the test failures already on `main` (issue #307) |
| **Proposed By** | Engineering (request from the product owner, 2026-09-24) |
| **Date** | 2026-09-24 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** four test suites that had failures already on `main`
(frontend 7, MCP 2, backend 15, and 8 backend tests that were never
collected), which nobody noticed because CI runs only the parity, genericness
and extensions checks,

**facing** the product owner's request to log the failures and fix them, and
the finding that almost all of them were tests pinning behaviour a later
release had changed on purpose,

**we decided to**
(1) update each stale test to assert the current, intended behaviour and name
the release or ADR that changed it, without touching product code;
(2) add `run_sqlite_main_migrations(conn)` in `app/startup.py`, the ordered
list of main-database migrations that startup already ran, and make tests that
build their own database call it instead of a hand-picked subset, so a test
schema can't fall behind again;
(3) fix the one real bug: `convert_eap_to_sqlite` checks the JET4 header
before checking for `mdbtools`, so a bad `.eap` upload is a 400 on every host;
(4) move `tests/test_startup.py` into the `tests/test_startup/` package
(`test_initialize_databases.py`) so its 8 tests are collected;
(5) set pytest's `tmp_path_retention_policy = "failed"` for the backend, since
each full run leaves about 1.4 GB of SQLite files and three retained runs fill
a tmpfs `/tmp`,

**and neglected** (a) deleting or skipping the stale tests. Rejected: each
still guards a real behaviour once realigned; (b) adding the missing
migrations to each hand-picked list. Rejected: that is what drifted in the
first place; (c) adding these suites to CI in this change. Deferred: it is a
larger piece of work (service containers, runtime budget) and deserves its own
decision,

**to achieve** suites where a failure means something again,

**accepting that** tests using the full migration chain run slightly slower
than with a subset (the search and mnemos tests take about 11 s together).

---

## Consequences

- No API, MCP or CLI change; surface parity is unaffected.
- The svelte-check type errors (~167, mostly in test files) are not addressed.

## Dependencies

- ADR-089 / ADR-234 (node sizing), ADR-191 / ADR-211 (element templates),
  ADR-204 (tab defaults), ADR-111 (MNEMOS gating).

## References

- Issue: [#307](https://github.com/cgbarlow/iris/issues/307)
- Implementation spec: [SPEC-254-A](./specs/SPEC-254-A-Green-Test-Suites.md)
