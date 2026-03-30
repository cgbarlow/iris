# ADR-113: Ask AI Tabbed Layout

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-113 |
| **Initiative** | Ask AI UX Improvement |
| **Proposed By** | Engineering |
| **Date** | 2026-03-29 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** the Ask AI page where context selectors (collection, sets, legislation) and the chat dialogue share a single vertically-stacked layout,

**facing** the problem that selectors consume significant vertical space, leaving the chat dialogue cramped and reducing the usable area for conversation, particularly when the DocRef extension adds another selector row,

**we decided for** splitting the Ask AI page into two local tabs — "Context" (selectors) and "Request" (chat) — using the same tab styling pattern as Admin/Settings, with `display:none` toggling to preserve chat state across tab switches and a one-line context summary on the Request tab,

**and neglected** URL-routed tabs via SvelteKit layout (would require lifting shared state into a store or context, adding complexity for no routing benefit), a collapsible sidebar for selectors (would still consume horizontal space and require responsive breakpoints), and keeping the current stacked layout with a collapsible section (half-measure that still competes for vertical space),

**to achieve** maximum vertical space for the chat dialogue, clean separation of concerns between context selection and conversation, a consistent tab UX matching the existing Settings pattern, and a summary line that keeps users informed of their selected context without switching tabs,

**accepting that** users must switch tabs to change context (mitigated by the summary line showing current selections), and the `display:none` approach keeps the hidden panel's DOM alive (negligible memory cost for the benefit of preserved chat state).

---

## Summary

| Capability | Description | Specification |
|------------|-------------|---------------|
| Tab Bar | Local tab bar with Context and Request tabs matching Settings styling | [SPEC-113-A](./specs/SPEC-113-A-Ask-AI-Tabs.md) |
| Context Tab | Collection dropdown, MultiSetSelector, DocRefSelector (if enabled) | [SPEC-113-A](./specs/SPEC-113-A-Ask-AI-Tabs.md) |
| Request Tab | Context summary line + expanded SetQA chat area | [SPEC-113-A](./specs/SPEC-113-A-Ask-AI-Tabs.md) |
| Context Summary | Comma-separated list of selected set and document names | [SPEC-113-A](./specs/SPEC-113-A-Ask-AI-Tabs.md) |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Extends | ADR-093 | AI Model Management | Ask AI is the primary AI interaction surface |
| Relates To | ADR-112 | DocRef Legislation Integration | DocRef selector moves into the Context tab |
| Relates To | ADR-109 | Package-Level AI Context | Package selector within MultiSetSelector on Context tab |
