# ADR-148: ArchiMate Open Exchange XML Import

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-148 |
| **Initiative** | Issue #52 — make ArchiMate OEX a first-class import in iris |
| **Proposed By** | Engineering |
| **Date** | 2026-05-07 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** users wanting to bring ArchiMate models authored
in other tools (Archi, Sparx EA, Visual Paradigm, BiZZdesign) into iris
as first-class diagrams, alongside the existing `.qea`/`.eap` (SparxEA)
and `.pptx` (DoView) import paths,

**facing** that The Open Group's ArchiMate® Model Exchange File Format
(OEX) is the de-facto interoperability standard for ArchiMate 3.x and
that iris already has rich ArchiMate plumbing (40+ entity types, the
`ARCHIMATE_STEREOTYPE_MAP` in `import_sparx/mapper.py`, automatic
notation detection) but no XML reader to feed it,

**we decided to**:
1. Add a new backend module `app/import_archimate/` (reader + mapper +
   service + router) that parses OEX 3.0 / 3.1 / 3.2 files using the
   stdlib `xml.etree.ElementTree` (no new dependency) and produces
   iris elements, relationships, and diagrams.
2. Reuse `ARCHIMATE_STEREOTYPE_MAP` as the single source of truth for
   element-type mapping — the OEX mapper prefixes the unprefixed
   `xsi:type` (e.g. `BusinessActor`) with `ArchiMate_` and delegates
   (DRY, protocol #13).
3. Define a small new `RELATIONSHIP_TYPE_MAP` for the 12 ArchiMate
   relationship types (Composition, Aggregation, Assignment,
   Realization, Serving, Triggering, Flow, Specialization, Access,
   Influence, Association, plus the legacy `Used`/`UsedBy` aliases).
4. **Auto-generate a single Overview diagram** when the source OEX file
   has no embedded views (model-only). Layout: type-grouped grid
   (`ceil(sqrt(n))` columns × 220×140 cell spacing). Without this,
   model-only imports — which are common in real-world OEX — would
   land 100s of orphaned elements with nothing to render.
5. Extend the existing `/import` page dropzone to accept `.xml`,
   `.archimate`, and `.oex` extensions with content sniffing on upload
   (the OEX namespace must appear in the first 4 KiB or the request
   is rejected with 400).
6. Cover the path with a real-world UAT Playwright spec that imports
   the user-supplied
   [MSD Business Architecture model](https://github.com/1punchtan/msd-business-architecture/blob/main/workspace/msd-map.xml)
   — 127 elements, 977 relationships, 0 views — and asserts the
   resulting Overview diagram renders ≥100 nodes without throwing.

**to achieve** a polished, low-friction import for ArchiMate users
that puts iris on equal footing with established ArchiMate tools while
keeping the implementation minimal: net new lines are the parser,
12-row relationship map, and grid-layout helper.

**accepting** that:
- This release is **import only**. OEX export (writing iris diagrams
  back to OEX) is deferred until users ask for round-trip — the
  use-cases we've heard so far are one-way (migrate into iris, then
  iterate in iris).
- The grid layout is simple and dense for 100+ nodes. Users will
  rearrange manually for any non-trivial model. A future ADR may add
  a force-directed layout if friction emerges.
- Nested `<node>` containment (compound nodes) is **flattened** to
  absolute coordinates on import — iris diagrams don't model parent-
  child node nesting today.
- We accept the broader `.xml` extension (not just `.archimate` /
  `.oex`) because Archi tool's official export uses `.xml`; we sniff
  for the OEX namespace before importing to avoid accidentally
  ingesting a non-OEX XML.

---

## Rejected alternatives

- **Add `lxml` for XML schema validation.** Overkill — OEX files in
  the wild are often slightly out-of-spec (missing `xml:lang` on
  `<name>`, mixing 3.0/3.1 namespaces). Permissive parsing via stdlib
  is a better fit, and avoids a C-build dependency on Render.
- **Define a separate ArchiMate-specific data model.** Iris elements,
  relationships, and diagrams already represent ArchiMate concepts
  (notation auto-detection tags `archimate` when the data shows it).
  No table changes needed.
- **Duplicate `ARCHIMATE_STEREOTYPE_MAP`** in the new module.
  Violates DRY (#13). The existing 40-row map already covers every
  type the OEX format defines.
- **Skip auto-layout when no views exist.** Tested with the MSD
  fixture — 127 silent elements with no diagram is a poor outcome;
  the user wouldn't see anything on `/views` and would have to build
  the visualisation manually. Auto-layout is the higher-value default.
- **Open up batch upload like `.pptx`.** OEX files tend to be a
  single canonical model per repo. Single-file flow keeps the UX
  simple and matches the SparxEA pattern.

---

## Dependencies

- Depends on the existing `ARCHIMATE_STEREOTYPE_MAP`
  ([backend/app/import_sparx/mapper.py:47-97](../../backend/app/import_sparx/mapper.py#L47-L97)).
- Depends on the existing element / relationship / diagram services
  for persistence.
- Depends on the existing notation auto-detection
  ([backend/app/diagrams/notation_detection.py](../../backend/app/diagrams/notation_detection.py))
  to tag the imported diagram as `notation: "archimate"`.
- Depends on ADR-147 (UAT Playwright harness) for the e2e
  verification project.

## Related specs

- [SPEC-148-A: ArchiMate OEX Import](specs/SPEC-148-A-ArchiMate-OEX-Import.md)
