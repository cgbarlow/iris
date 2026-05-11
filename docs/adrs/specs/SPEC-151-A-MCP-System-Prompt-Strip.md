# SPEC-151-A: MCP `system_prompt` strip

ADR: [ADR-151](../ADR-151-MCP-Boundary-Strips-Scope-System-Prompts.md)

## What to strip

A module-level tuple in `mcp/src/iris_mcp/links.py`:

```python
_STRIPPED_KEYS: tuple[str, ...] = ("system_prompt",)
```

v5.8.2 ships with one key. Future additions extend the tuple. No
per-handler strip logic.

## Where the strip runs

Inside three existing serialisation helpers in `links.py`:

| Helper | Strip target |
|---|---|
| `with_web_url(payload, kind)` | the top-level dict |
| `with_web_urls_list(payload, kind)` | each dict in the parsed list |
| `with_web_urls_search(payload)` | each dict in `data["results"]` |

The strip runs **unconditionally** — independent of whether
`IRIS_WEB_URL` is set. (Prior to v5.8.2 the helpers were full no-ops
when `IRIS_WEB_URL` was unset; the strip half of the helper now
always runs, the web-URL decoration half still skips.)

Two private helpers are added:

```python
def _strip_sensitive_keys(item: Any) -> None: ...
def _strip_sensitive_keys_list(items: Any) -> None: ...
```

The first mutates a single dict in place; the second mutates each
element of a list in place. Non-dict inputs are silently ignored.

## Coverage

All four Set/Collection-returning MCP tools already route through
the affected helpers — no handler changes needed:

| Handler | Helper called |
|---|---|
| `_get_set` | `with_web_url(..., "set")` |
| `_list_sets` | `with_web_urls_list(..., "set")` |
| `_get_collection` | `with_web_url(..., "collection")` |
| `_list_collections` | `with_web_urls_list(..., "collection")` |

`with_web_urls_search` is included in the strip for defence in depth
— the FTS index does not currently surface `system_prompt`, but
keeping the boundary consistent across all three helpers means a
future change to search wouldn't accidentally reintroduce the leak.

## Tests

`mcp/tests/test_links_strip_system_prompt.py` — pins the new
behaviour. Nine cases:

| Helper | Case | Assertion |
|---|---|---|
| `with_web_url` | set payload | `system_prompt` absent; other fields + `web_url` preserved |
| `with_web_url` | collection payload | same |
| `with_web_url` | env unset | `system_prompt` still absent |
| `with_web_url` | field absent | no-op for that key; other fields intact |
| `with_web_url` | bad JSON | passthrough |
| `with_web_urls_list` | each set item | `system_prompt` absent from every item |
| `with_web_urls_list` | each collection item | same |
| `with_web_urls_list` | env unset | still strips |
| `with_web_urls_search` | each result | `system_prompt` absent |

Existing 22 tests in `tests/test_links.py` continue to pass — the
strip is additive and doesn't change any prior assertions.

## Out of scope (deferred)

- Stripping additional fields — none currently identified. The
  `_STRIPPED_KEYS` tuple is the extension point.
- Stripping nested fields (e.g., `set.collection.system_prompt`) —
  none currently exist; the top-level strip covers all known leak
  shapes.
- Logging / metrics on every strip — adds noise without value. If
  Iris ever wants to audit the boundary, the existing MCP request
  log is the right place.
