# ADR-112: DocRef Legislation Integration

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-112 |
| **Initiative** | DocRef Legislation Data Source |
| **Proposed By** | Engineering |
| **Date** | 2026-03-29 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** enhancing the Ask AI feature with legislative reference data from New Zealand legislation,

**facing** the need for users to include relevant legislation as context when asking AI questions about their architecture models, with the DocRef project providing chunked CSV exports of NZ legislation at legislation.docref.nz,

**we decided for** creating a new Iris extension ("docref") following the existing extensions pattern (ADR-103), with dedicated database tables for document metadata and content chunks, a background scheduler for hourly index refresh, and a frontend dropdown on the Ask AI page that lets users import and select legislation documents as additional AI context,

**and neglected** embedding legislation as Iris elements/sets (would pollute the architecture model with unrelated reference material), relying on real-time external API calls during AI queries (would add latency and external dependency at query time), and building a generic external data source framework (premature abstraction for a single known data source),

**to achieve** seamless integration of NZ legislation as AI context alongside sets and collections, fast document browsing via cached index with hourly refresh, one-click document import with progress tracking, and clean separation between architecture data and reference material,

**accepting that** the extension depends on the external legislation.docref.nz service for index refresh and CSV downloads, HTML scraping of the index page is fragile to layout changes, and imported legislation chunks consume additional database storage.

---

## Summary

| Capability | Description | Specification |
|------------|-------------|---------------|
| DocRef Extension | Extension registry entry with install/uninstall/enable/disable lifecycle | [SPEC-112-A](./specs/SPEC-112-A-DocRef-Integration.md) |
| Document Index | Cached list of available legislation from legislation.docref.nz with hourly refresh | [SPEC-112-A](./specs/SPEC-112-A-DocRef-Integration.md) |
| CSV Import | Download and parse chunked CSV files into docref_chunks table | [SPEC-112-A](./specs/SPEC-112-A-DocRef-Integration.md) |
| AI Context | Legislation chunks formatted as structured text for LLM system prompts | [SPEC-112-A](./specs/SPEC-112-A-DocRef-Integration.md) |
| Frontend Selector | DocRef dropdown on Ask AI page with import/status indicators | [SPEC-112-A](./specs/SPEC-112-A-DocRef-Integration.md) |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Extends | ADR-103 | Extensions Framework | DocRef is registered as an extension |
| Extends | ADR-093 | AI Model Management | Adds DocRef as AI context source |
| Relates To | ADR-102 | Collections | DocRef dropdown sits alongside collection selector |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-112-A | DocRef Integration | Technical Specification | [specs/SPEC-112-A-DocRef-Integration.md](./specs/SPEC-112-A-DocRef-Integration.md) |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Engineering | 2026-03-29 |
| Approved | Engineering | 2026-03-29 |
