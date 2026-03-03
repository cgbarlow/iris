# ADR-069: Note and Boundary Import Label Derivation

## Proposal: Derive meaningful labels for Note/Boundary elements during SparxEA import

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-069 |
| **Initiative** | SparxEA Import Fidelity |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-03 |
| **Status** | Approved |
| **Dependencies** | ADR-066 (Import All Skipped Items) |

---

## ADR (WH(Y) Statement format)

**In the context of** SparxEA Note elements having `Name=NULL` in `t_object`, causing import to fall back to generic "Element N" names and canvas nodes to get `label: "Unknown"` with no `description`, while the actual content is stored in the `Note` HTML column,

**facing** uninformative Note labels on imported diagrams, missing descriptions on canvas nodes, and Boundary elements similarly lacking meaningful names,

**we decided for** adding a `derive_note_label()` utility that strips HTML tags from Note content, takes the first line, and truncates to 60 characters for use as the entity name; and always populating the `description` field on canvas nodes from the element's `Note` content during import,

**and neglected** using the full HTML content as the name (too long, contains formatting), and leaving notes unnamed (current behaviour, unusable),

**to achieve** meaningful labels on imported Note and Boundary elements, populated descriptions on all canvas nodes, and accurate representation of SparxEA diagram annotations,

**accepting that** HTML stripping may lose some formatting nuance in the label (full content preserved in entity description).

---

## Decisions

1. **derive_note_label utility**: Strip HTML tags, take first line, truncate to 60 chars, provide fallback
2. **Note entity name derivation**: For Note/Boundary elements with NULL Name, derive label from `Note` HTML content
3. **Canvas node description**: Always populate `description` field from element's `Note` content during canvas node construction

---

## Specification

See [SPEC-069-A](specs/SPEC-069-A-Note-Boundary-Import-Fix.md).
