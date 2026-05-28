# ADR-219: Native Sparx EA XMI 2.1 Import

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-219 |
| **Initiative** | Make Sparx EA's native XML (XMI 2.1) export a first-class import in iris |
| **Proposed By** | Engineering |
| **Date** | 2026-05-28 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** users wanting to bring Sparx Enterprise Architect
models into iris when all they have is the **native XML export**
("Export Package to XMI 2.1 / Native XML") rather than the binary
project file — a common situation because the XML export is text,
diff-able, emailable, and produced without admin access to the `.qea`
database,

**facing** that iris already imports Sparx EA *databases* (`.qea`/`.eap`
via `app/import_sparx/`, ADR-059/ADR-084) and ArchiMate Open Exchange
XML (`app/import_archimate/`, ADR-148), but has **no reader for EA's
native XMI** — which is a third, distinct format: UML 2.1 XMI with an
`<xmi:Extension extender="Enterprise Architect">` block carrying the
EA-specific elements, connectors, tagged values and diagram geometry,
and Sparx profile namespaces (`sparxsystems.com/profiles/...`). It is
**not** ArchiMate OEX (different namespace, no Open Group schema) and
**not** the `.qea`/`.eap` binary databases,

**we decided to**:
1. Add a new backend module `app/import_sparx_xml/` (reader + service +
   router) that parses EA native XMI 2.1 using the stdlib
   `xml.etree.ElementTree` (no new dependency, exactly as
   `app/import_archimate/` does).
2. **Reuse the entire `.qea` import pipeline.** The native XML is the
   same EA model as a `.qea`, just serialised as XML. So the new reader
   emits the *same* intermediate dataclasses the `.qea` reader produces
   (`QeaPackage`, `QeaElement`, `QeaConnector`, `QeaDiagram`,
   `QeaDiagramObject`, `QeaDiagramLink`, `QeaTaggedValue`), and the
   orchestration in `import_sparx/service.py` is refactored into a
   surface-agnostic `import_sparx_model(...)` that both the `.qea` path
   and the new XMI path call. Type mapping
   (`ARCHIMATE_STEREOTYPE_MAP`, `map_object_type`, `map_connector_type`,
   `map_diagram_type`), geometry conversion (`ea_rect_to_position`),
   icon matching, and GUID-based idempotency (ADR-073) are reused
   **untouched** (DRY, protocol §13). The only genuinely new parsing
   code is the XMI reader.
3. Normalise EA's GUID cross-references (`xmi:id`/`xmi:idref`, e.g.
   `EAID_…`/`EAPK_…`) to the integer IDs the dataclasses key on, using
   the `ea_localid`/`localID` integers EA emits in the extension block,
   so the existing integer-keyed orchestration works unchanged.
4. Expose the import as `POST /api/import/sparx-xml`, mirroring the
   `/api/import/archimate` router (content-sniff, `set_id` validation,
   temp-file handling), with idempotent re-import via `ea_guid`.
5. Disambiguate the shared `.xml` extension on the frontend by
   **content sniffing** the first ~4 KiB before upload: an EA native
   XMI file (`xmi:XMI` + `Enterprise Architect`/`sparxsystems.com`)
   routes to `/api/import/sparx-xml`; an ArchiMate OEX file (Open Group
   namespace) routes to `/api/import/archimate`.

**to achieve** a low-friction native-XML import for Sparx EA users that
reuses iris's mature `.qea` plumbing — net new code is essentially one
XML reader — while keeping the three Sparx-adjacent formats (OEX,
`.qea`/`.eap`, native XMI) cleanly separated and individually testable.

**accepting** that:
- This release is **import only** and **website only** (the import
  UI). A unified `POST /api/import` dispatcher, an `import_model` MCP
  tool, and an `iris import` CLI command are deferred to a follow-up
  (captured as ADR-220 when that work starts) so this release stays
  focused on the core path.
- The native XMI export does not include element images/alternate
  images, so those are not imported (the `.qea` path doesn't either).
- We accept the broad `.xml` extension (shared with ArchiMate OEX and
  with the Archi tool's export); the content sniff guards against
  importing the wrong kind of XML, and the backend re-sniffs and
  returns 400 on mismatch.
- The native XMI geometry uses a screen-down convention
  (`Top` < `Bottom`, positive); the reader normalises it to the
  EA-database convention the existing `ea_rect_to_position` expects so
  no geometry math is duplicated.

---

## Rejected alternatives

- **A separate, parallel orchestrator for XMI.** Would duplicate the
  ~700-line `.qea` orchestration (package topo-sort, stereotype
  mapping, geometry, idempotency, NavigationCell post-processing).
  Direct DRY violation (§13). Instead we extract `import_sparx_model`
  and share it.
- **Map XMI onto the ArchiMate OEX dataclasses and reuse
  `import_archimate`.** The EA extension (diagram geometry, EA tagged
  values, EA stereotypes, UML connectors) is far closer to the `.qea`
  model than to OEX; OEX has no representation for most of it.
- **Add `lxml` for schema-validated parsing.** Unnecessary — the
  permissive stdlib `ElementTree` already handles real EA exports, and
  adding a C-build dependency on Render is the same trade-off rejected
  in ADR-148.
- **A new `.xmi` file extension.** Real EA native exports are `.xml`.
  Content sniffing is the only reliable signal, so a new extension
  would add friction without solving disambiguation.
- **Defer the `import_sparx/service.py` refactor (call the existing
  `import_sparx_file` after writing a temp SQLite).** Would require
  re-serialising the parsed XML into a SQLite database just to re-read
  it — absurd round-trip. Sharing the in-memory orchestrator is far
  cleaner.

---

## Dependencies

- Reuses the `.qea` orchestration, mappers, converter and icon matcher
  in [backend/app/import_sparx/](../../backend/app/import_sparx/)
  (ADR-059, ADR-084) — refactored into a shared `import_sparx_model`.
- Reuses `ARCHIMATE_STEREOTYPE_MAP`
  ([backend/app/import_sparx/mapper.py](../../backend/app/import_sparx/mapper.py)).
- Reuses GUID-based idempotency (ADR-073) via `metadata.ea_guid`.
- Mirrors the router/sniff pattern of ADR-148
  ([backend/app/import_archimate/](../../backend/app/import_archimate/)).
- No database migration — persistence is via the existing
  element/relationship/diagram/package services, which already work on
  both SQLite and Supabase (protocol §15).

## Related specs

- [SPEC-219-A: Native Sparx EA XMI Import](specs/SPEC-219-A-Native-Sparx-EA-XMI-Import.md)
