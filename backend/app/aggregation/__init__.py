"""Generic aggregation engine + profile library (ADR-212, v6.20.0).

Walks one or two levels of smart_markdown diagrams, collects structured
per-use values from tokens, aggregates by configurable rules in a
named profile, and emits grouped/summed markdown. The engine is
parameterised by data (profiles) and reusable across domains —
shopping-list, sprint-points, time-tracking, expense-report, reading-
log, etc. — without code changes.

Surfaces:
  - REST: /api/aggregation/profiles (CRUD), /api/aggregation/run.
  - MCP: aggregate, list/get/create/update/delete_aggregation_profile.
  - CLI: iris aggregate, iris aggregation-profile <subcmd>.

The ``aggregation_list`` diagram type (ADR-213) is one consumer of the
engine — it calls ``engine.run`` at synth-on-read time. Agents (Claude
Desktop) call ``engine.run`` directly via MCP.
"""
