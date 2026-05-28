# SPEC-219-A: Native Sparx EA XMI 2.1 Import

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-219-A |
| **Implements** | [ADR-219](../ADR-219-Native-Sparx-EA-XMI-Import.md) |
| **Status** | Implemented (v6.32.0) |
| **Date** | 2026-05-28 |

---

## Scope

Backend reader + service + router for Sparx Enterprise Architect's native
XML export (UML 2.1 XMI with an EA `<xmi:Extension>` block); a refactor of
`import_sparx/service.py` to share its orchestration; frontend `.xml`
content-sniff dispatch; backend tests.

Out of scope (deferred — see ADR-219 "accepting"): XMI export; the unified
`POST /api/import` dispatcher; the `import_model` MCP tool and `iris import`
CLI command (future ADR-220).

---

## File format reference

EA "Export Package to XMI 2.1 / Native XML" output (`windows-1252`):

```xml
<xmi:XMI xmi:version="2.1"
         xmlns:xmi="http://schema.omg.org/spec/XMI/2.1"
         xmlns:uml="http://schema.omg.org/spec/UML/2.1"
         xmlns:Archimate="http://www.sparxsystems.com/profiles/Archimate/1.0"
         xmlns:ArchiMate3="http://www.sparxsystems.com/profiles/ArchiMate3/1.0">
  <xmi:Documentation exporter="Enterprise Architect" exporterVersion="6.5"/>
  <uml:Model xmi:type="uml:Model" name="EA_Model">
    <packagedElement xmi:type="uml:Package" xmi:id="EAPK_…" name="…">
      <packagedElement xmi:type="uml:Class" xmi:id="EAID_…" name="…"/>
      <packagedElement xmi:type="uml:Association" xmi:id="EAID_…">…</packagedElement>
    </packagedElement>
  </uml:Model>
  <xmi:Extension extender="Enterprise Architect" extenderID="6.5">
    <elements>
      <element xmi:idref="EAID_…" xmi:type="uml:Class" name="…" scope="public">
        <model package="EAPK_…" ea_localid="24497" ea_eleType="element"/>
        <properties documentation="…" sType="Class" alias="CBC.00a"
                    stereotype="ArchiMate_Capability" isAbstract="false"/>
        <project author="…" version="1.0" phase="1.0"
                 created="…" modified="…" complexity="1" status="Proposed"/>
        <style appearance="BackColor=-1;BorderColor=-1;BorderWidth=1;FontColor=-1;…"/>
        <tags><tag name="Current Maturity Level" value="…" modelElement="EAID_…"/></tags>
      </element>
    </elements>
    <connectors>
      <connector xmi:idref="EAID_…">
        <source xmi:idref="EAID_…"><model ea_localid="24497" type="Class" name="…"/>
          <type aggregation="none"/></source>
        <target xmi:idref="EAID_…"><model ea_localid="27010" type="Class" name="…"/>
          <type aggregation="none"/></target>
        <model ea_localid="18621"/>
        <properties ea_type="Association" stereotype="ArchiMate_Association" direction="Unspecified"/>
        <appearance linemode="3" linecolor="-1" linewidth="0" lineStyle="0"/>
      </connector>
    </connectors>
    <diagrams>
      <diagram xmi:id="EAID_…">
        <model package="EAPK_…" localID="2051" owner="EAPK_…"/>
        <properties name="…" type="Logical" documentation="…"/>
        <style1 value="…;DocSize.cx=1138;DocSize.cy=795;…"/>
        <elements>
          <element geometry="Left=771;Top=116;Right=1134;Bottom=215;"
                   subject="EAID_…" seqno="1" style="…;BCol=…;LCol=…;LWth=3;"/>
          <element geometry="EDGE;…SX=0;SY=0;EX=0;EY=0;Path=…;" subject="EAID_<connector>"/>
        </elements>
      </diagram>
    </diagrams>
  </xmi:Extension>
</xmi:XMI>
```

Detection (`is_sparx_xmi_file`, content sniff of the first 4 KiB):
the bytes must contain `xmi:XMI` **and** (`Enterprise Architect`
**or** `sparxsystems.com`). This distinguishes EA native XMI from
ArchiMate OEX (Open Group namespace) and from arbitrary XML.

---

## Shared-orchestrator refactor

`import_sparx/service.py` is split so the orchestration is surface-agnostic:

- **New** `import_sparx_model(db, *, packages, elements, connectors, diagrams, diagram_objects, diagram_links, attributes, tagged_values, imported_by, set_id=None, source_label="SparxEA") -> ImportSummary` — the entire current body of `import_sparx_file` after the file read (package topo-sort, element/connector creation, ArchiMate-stereotype override, diagram canvas building, NavigationCell post-processing, GUID idempotency). The four `"Imported from SparxEA …"` `change_summary` strings become `f"Imported from {source_label} …"` (every value still begins `"Imported from SparxEA"`).
- `import_sparx_file(db, qea_path, imported_by, set_id=None)` keeps its signature; it now reads the eight lists via the `read_*` functions and delegates to `import_sparx_model(..., source_label="SparxEA")`.

`import_sparx_xml_file` reuses `import_sparx_model` with `source_label="SparxEA XMI"`. All mapping/geometry/idempotency code is shared, not duplicated.

---

## Reader (`backend/app/import_sparx_xml/reader.py`)

Stdlib `xml.etree.ElementTree`. `parse_sparx_xmi(path) -> SparxXmiModel`
emits the dataclasses from `app.import_sparx.reader`.

**GUID → integer-ID index.** EA cross-references by GUID
(`xmi:id`/`xmi:idref`, `subject`, `<model package=…>`, connector
source/target). A single pass over `<xmi:Extension>` builds
`guid_to_int: dict[str, int]` from the `ea_localid` (elements,
connectors) / `localID` (diagrams) integers EA emits. Where an
`ea_localid` is missing a synthetic counter is used. Every dataclass
integer field (`Object_ID`, `Package_ID`, `Connector_ID`, `Diagram_ID`,
`Start/End_Object_ID`, `Parent_ID`) is resolved through this index;
`ea_guid` is preserved verbatim for idempotency (ADR-073).

**Packages** (`QeaPackage`): `<element sType="Package">` (and the
`<uml:Package>` tree for the root). `Package_ID`=ea_localid;
`Parent_ID`=index[`<model package=…>` GUID]; `ea_guid`=idref;
`Name`=name; `Notes`=`properties/@documentation`.

**Elements** (`QeaElement`): each `<element>` whose `sType` ≠ Package.
`Object_Type`=`properties/@sType` (feeds `map_object_type`);
`Stereotype`, `Alias`, `Abstract` (`isAbstract` → "1"/None),
`Status`/`Author`/`Version`/`Phase`/`Complexity`/`CreatedDate`/`ModifiedDate`
from `properties`/`project`; `Note`=`properties/@documentation`;
`Package_ID`=index[`<model package=…>`]. `<style appearance="BackColor=…;
BorderColor=…;BorderWidth=…;FontColor=…">` is parsed into
`Backcolor`/`Bordercolor`/`BorderWidth`/`Fontcolor` ints. `PDATA1`/`StyleEx`
populated when present (NavigationCell support).

**Connectors** (`QeaConnector`): each `<connector>`. `Connector_ID`=own
`<model ea_localid>`; `Connector_Type`=`properties/@ea_type`;
`Stereotype`/`Direction` from `properties`; `Start_Object_ID`/`End_Object_ID`
from `source`/`target` `<model ea_localid>`;
`SourceIsAggregate`/`DestIsAggregate` from `source`/`target`
`type/@aggregation` (none→0, shared→1, composite→2 — drives the
association→aggregation/composition promotion in the orchestrator);
`LineColor`/`IsBold`/`LineStyle` from `<appearance>`; `Name`/`Notes` from
`<documentation>`/labels.

**Diagrams** (`QeaDiagram`): each `<diagram>`. `Diagram_ID`=localID;
`Diagram_Type`=`properties/@type`; `Name`/`Notes` from `properties`;
`Package_ID`=index[`<model package=…>`]; `cx`/`cy` parsed from
`style1/@value` `DocSize.cx`/`DocSize.cy`.

**DiagramObjects** (`QeaDiagramObject`): each diagram `<element>` whose
`geometry` is a plain rect. Parse `geometry="Left=…;Top=…;Right=…;
Bottom=…;"`. **Geometry normalisation:** the native XMI uses a
screen-down convention (`Top` < `Bottom`, positive) whereas the existing
`ea_rect_to_position(Left, Right, Top, Bottom)` expects the
EA-database convention (negative Y, `Top` > `Bottom`). The reader emits
`RectTop`/`RectBottom` negated so the existing converter math is reused
**unchanged**. `Object_ID`=index[`subject`]; `ObjectStyle`=`@style`
(carries `BCol`/`LCol`/`LWth`, consumed by `build_node_visual`).

**DiagramLinks** (`QeaDiagramLink`): each diagram `<element>` whose
`geometry` begins `EDGE` (edge waypoints). `DiagramID`=diagram localID;
`ConnectorID`=index[`subject`]; `Geometry`/`Path` passed verbatim to the
existing `parse_diagram_link_geometry`/`parse_diagram_link_path`.

**TaggedValues** (`QeaTaggedValue`): each `<element>/<tags>/<tag>`.
`Object_ID`=index[parent idref]; `Property`=`@name`; `Value`=`@value`.

**Attributes** (`QeaAttribute`): from UML `<packagedElement>/<ownedAttribute>`
when present; `[]` when absent (the GEANZ sample has none — graceful).

`is_sparx_xmi_file(path) -> bool`: OSError-safe first-4 KiB sniff (above).

---

## Service (`backend/app/import_sparx_xml/service.py`)

`import_sparx_xml_file(db, path, *, imported_by, set_id=None) -> ImportSummary`:
`model = parse_sparx_xmi(path)`, then
`return await import_sparx_model(db, packages=model.packages, …, source_label="SparxEA XMI")`.

---

## API — `POST /api/import/sparx-xml`

| Field | Value |
|---|---|
| Auth | Required (Bearer JWT) |
| Body | `multipart/form-data` |
| Form fields | `file` (the `.xml`), `set_id` (optional) |

Behaviour (mirrors `/api/import/archimate`):
- 400 if filename does not end `.xml`.
- 400 if `is_sparx_xmi_file` is false (content sniff).
- 400 if `set_id` is supplied but does not reference an existing set.
- On success returns the SparxEA `ImportSummary` JSON
  (`packages_created`, `packages_skipped`, `elements_created`,
  `elements_skipped`, `relationships_created`, `diagrams_created`,
  `diagrams_updated`, `diagrams_skipped`, `connectors_skipped`,
  `package_relationships_created`, `warnings`).
- Wrapped in the `SupabaseAdapter.hold_connection()` context; temp file
  always unlinked. Registered in `backend/app/main.py`.

---

## Frontend

`frontend/src/routes/import/+page.svelte`: for `.xml`/`.archimate`/`.oex`
single-file uploads, read the first ~4 KiB client-side
(`await file.slice(0, 4096).text()`) and route — `sparxsystems.com` /
`Enterprise Architect` → `/api/import/sparx-xml`;
`opengroup.org/xsd/archimate` → `/api/import/archimate`. `.qea`/`.eap` →
`/api/import/sparx`; `.pptx` → `/api/import/pptx`. Help text names
"Sparx EA native XML (XMI)".

---

## Test fixtures

`backend/tests/test_import_sparx_xml/sample_ea_xmi.xml` — small,
hand-authored: 1 package, ~3 `uml:Class` (one with
`stereotype="ArchiMate_Capability"`, colours, tagged values), 1
`uml:Association`, 1 diagram with two node `<element geometry>` and one
edge `<element geometry="EDGE…">`. Exercises reader, GUID resolution,
geometry normalisation, stereotype mapping, and tags. The 3.6 MB
`GEANZ …model.xml` at repo root is used for manual UAT only, never as a
unit fixture.

---

## Verification

```bash
cd backend && .venv/bin/python -m pytest tests/test_import_sparx_xml tests/test_import_sparx -q
python3 scripts/check_surface_parity.py        # expect "✅ Parity clean"
cd frontend && npm run test:unit -- importPageSparxXml importPageAcceptsArchimate
```

Manual smoke (local dev):
1. `./scripts/dev.sh start`.
2. Drag `GEANZ Common Business Capabilities Sparx EA model.xml` onto `/import`, pick a set, Import.
3. Expect packages/elements/relationships/diagrams created; diagram nodes positioned from geometry; `ArchiMate_Capability` classes typed as `capability`.
4. Re-import → `packages_skipped`/`elements_skipped` > 0 (idempotency).
5. Import an ArchiMate `.xml`/`.oex` → still routes to `/api/import/archimate` (no regression).
