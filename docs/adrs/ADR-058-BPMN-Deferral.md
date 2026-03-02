# ADR-058: BPMN Support Deferral

## Proposal: Defer BPMN Implementation to Future Phase

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-058 |
| **Initiative** | SparxEA Integration & Modeling Standard Support |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-02 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** expanding Iris node type support to cover additional modeling standards beyond ArchiMate and UML, particularly BPMN (Business Process Model and Notation), which is used in enterprise architecture for process modeling,

**facing** the scope analysis that full BPMN support would require: swimlane/pool canvas architecture changes (major refactor of current FullViewCanvas layout system), ~30+ new node types (start/end/intermediate events, exclusive/parallel/inclusive/event-based gateways, various activities, data objects), ~10+ new edge types (sequence flow, message flow, association), and complex gateway/event execution semantics that differs fundamentally from current node rendering patterns. This scope is larger than all other SparxEA integration work packages combined. Additionally, the SparxEA AIXM sample file used for validation contains zero BPMN diagrams, making this a non-critical path item for the current integration goal.

**we decided for** deferring BPMN support to a future phase and focusing current effort on ArchiMate and UML expansion, which directly support the SparxEA import use case and proven modeling patterns.

**and neglected** attempting partial BPMN support (would create incomplete feature that misleads users about capability), and attempting full BPMN implementation in current phase (would delay achievement of SparxEA integration goal and inflate development timeline).

**to achieve** bounded scope for SparxEA integration delivery, proven ArchiMate and UML patterns before tackling architectural complexity of swimlane/pool support, and cleaner separation of concerns for future BPMN work.

**accepting that** SparxEA import will skip any BPMN diagrams encountered (logged as warnings in import log), swimlane/pool canvas architecture will need independent design work when BPMN support is planned, and enterprises with BPMN-heavy models will not be able to import those diagrams until future phase.

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Relates To | ADR-045 | Example Iris Architecture Models | Seed data and model type support |
| Relates To | ADR-046 | SparxEA Import Strategy | Import flow and diagram handling |
| Relates To | ADR-011 | Canvas Integration and Testing Strategy | Canvas architecture constraints |

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Architecture Team | 2026-03-02 | Accepted | Planning | 12 months | 2027-03-02 |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Accepted | Architecture Team | 2026-03-02 |
