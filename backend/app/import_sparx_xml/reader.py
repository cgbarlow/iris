"""Read Sparx EA native XMI 2.1 export (.xml) into the shared Qea* dataclasses.

EA's "Export Package to XMI 2.1 / Native XML" produces UML 2.1 XMI with an
``<xmi:Extension extender="Enterprise Architect">`` block carrying the
EA-specific elements, connectors, tagged values, and diagram geometry. This
reader parses that block into the *same* intermediate dataclasses the ``.qea``
reader produces, so the shared ``import_sparx_model`` orchestrator handles both
(ADR-219, DRY protocol §13). The only genuinely new code is this parser.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from xml.etree import ElementTree as ET

from app.import_sparx.reader import (
    QeaAttribute,
    QeaConnector,
    QeaDiagram,
    QeaDiagramLink,
    QeaDiagramObject,
    QeaElement,
    QeaPackage,
    QeaTaggedValue,
)


@dataclass
class SparxXmiModel:
    """The eight lists the orchestrator consumes (mirror of the .qea reads)."""

    packages: list[QeaPackage] = field(default_factory=list)
    elements: list[QeaElement] = field(default_factory=list)
    connectors: list[QeaConnector] = field(default_factory=list)
    diagrams: list[QeaDiagram] = field(default_factory=list)
    diagram_objects: list[QeaDiagramObject] = field(default_factory=list)
    diagram_links: list[QeaDiagramLink] = field(default_factory=list)
    attributes: list[QeaAttribute] = field(default_factory=list)
    tagged_values: list[QeaTaggedValue] = field(default_factory=list)


# ── namespace-agnostic XML helpers ──────────────────────────────────────
# The extension block tags are unprefixed; xmi:* attributes are namespaced.
# EA's XMI namespace URI varies by version, so we match on local names.


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _attr(elem: ET.Element, local: str) -> str | None:
    """Attribute by local name (handles ``xmi:idref`` etc. regardless of ns)."""
    val = elem.get(local)
    if val is not None:
        return val
    for key, value in elem.attrib.items():
        if _local(key) == local:
            return value
    return None


def _child(parent: ET.Element | None, local: str) -> ET.Element | None:
    if parent is None:
        return None
    for c in parent:
        if _local(c.tag) == local:
            return c
    return None


def _children(parent: ET.Element | None, local: str) -> list[ET.Element]:
    if parent is None:
        return []
    return [c for c in parent if _local(c.tag) == local]


def _cattr(parent: ET.Element | None, child_local: str, attr: str) -> str | None:
    """Attribute ``attr`` of the first ``child_local`` child, or None.

    Uses an explicit ``is not None`` check — an ElementTree element with no
    children is falsy, so ``_child(...) or fallback`` would silently drop a
    self-closing element like ``<model ea_localid=".."/>``.
    """
    c = _child(parent, child_local)
    return c.get(attr) if c is not None else None


def _find_descendant(root: ET.Element, local: str) -> ET.Element | None:
    for el in root.iter():
        if _local(el.tag) == local:
            return el
    return None


# ── geometry / style parsing ────────────────────────────────────────────

_GEOM_RE = re.compile(r"([A-Za-z]+)=(-?\d+)")


def _parse_geometry_rect(geometry: str | None) -> dict[str, int] | None:
    """Parse a node geometry 'Left=771;Top=116;Right=1134;Bottom=215;'.

    Returns None for edge geometries (no Left/Top/Right/Bottom — those carry an
    ``EDGE=`` token and SX/SY/EX/EY offsets instead).
    """
    if not geometry:
        return None
    vals = {k: int(v) for k, v in _GEOM_RE.findall(geometry)}
    if not all(k in vals for k in ("Left", "Top", "Right", "Bottom")):
        return None
    return vals


def _parse_appearance(appearance: str | None) -> dict[str, int]:
    """Parse element ``<style appearance="BackColor=-1;BorderColor=-1;...">``."""
    result: dict[str, int] = {}
    if not appearance:
        return result
    for part in appearance.split(";"):
        if "=" in part:
            key, _, val = part.partition("=")
            try:
                result[key.strip()] = int(val.strip())
            except ValueError:
                pass
    return result


def _int_or_none(val: str | None) -> int | None:
    if val is None:
        return None
    try:
        return int(val)
    except ValueError:
        return None


def _agg_to_int(aggregation: str | None) -> int:
    """EA aggregation: none→0, shared→1 (aggregation), composite→2 (composition)."""
    return {"shared": 1, "composite": 2}.get((aggregation or "").lower(), 0)


# ── detection ───────────────────────────────────────────────────────────


def is_sparx_xmi_file(path: str) -> bool:
    """Content-sniff: is this a Sparx EA native XMI export?

    True iff the first 4 KiB contain ``xmi:XMI`` AND an EA marker
    (``Enterprise Architect`` or ``sparxsystems.com``). This distinguishes EA
    native XMI from ArchiMate Open Exchange XML (Open Group namespace) and
    from arbitrary XML. OSError-safe.
    """
    try:
        with open(path, "rb") as f:
            head = f.read(4096)
    except OSError:
        return False
    return b"xmi:XMI" in head and (
        b"Enterprise Architect" in head or b"sparxsystems.com" in head
    )


# ── main parser ─────────────────────────────────────────────────────────


def parse_sparx_xmi(path: str) -> SparxXmiModel:
    """Parse an EA native XMI 2.1 export into the shared Qea* dataclasses."""
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise ValueError(f"Not a valid XML file: {exc}") from exc

    extension = _find_descendant(root, "Extension")
    if extension is None:
        raise ValueError(
            "Not a Sparx EA native XMI file (no <xmi:Extension> block)."
        )

    model = SparxXmiModel()

    el_list = _children(_child(extension, "elements"), "element")
    conn_list = _children(_child(extension, "connectors"), "connector")
    diag_list = _children(_child(extension, "diagrams"), "diagram")

    # ── Pass 1: GUID → integer-ID index (from ea_localid / localID) ──────
    # EA cross-references by GUID; the dataclasses key on integers. We use the
    # ea_localid/localID integers EA emits, falling back to a synthetic counter.
    guid_to_int: dict[str, int] = {}
    synthetic = -1

    def intern(guid: str | None, localid: str | None) -> int:
        nonlocal synthetic
        if guid and guid in guid_to_int:
            return guid_to_int[guid]
        iid = _int_or_none(localid)
        if iid is None:
            iid = synthetic
            synthetic -= 1
        if guid:
            guid_to_int[guid] = iid
        return iid

    for el in el_list:
        intern(_attr(el, "idref"), _cattr(el, "model", "ea_localid"))
    for cn in conn_list:
        intern(_attr(cn, "idref"), _cattr(cn, "model", "ea_localid"))
    for dg in diag_list:
        intern(_attr(dg, "id"), _cattr(dg, "model", "localID"))

    # ── Pass 2: packages + elements + tagged values ─────────────────────
    for el in el_list:
        idref = _attr(el, "idref")
        m = _child(el, "model")
        props = _child(el, "properties")
        project = _child(el, "project")
        code = _child(el, "code")
        style = _child(el, "style")

        obj_id = guid_to_int.get(idref, -1) if idref else -1
        parent_pkg_guid = m.get("package") if m is not None else None
        pkg_id = guid_to_int.get(parent_pkg_guid, 0) if parent_pkg_guid else 0
        name = _attr(el, "name")
        s_type = props.get("sType") if props is not None else None
        documentation = props.get("documentation") if props is not None else None

        if s_type == "Package":
            model.packages.append(
                QeaPackage(
                    Package_ID=obj_id,
                    Name=name,
                    Parent_ID=pkg_id,
                    ea_guid=idref,
                    Notes=documentation,
                )
            )
            # Packages can carry tagged values too.
            _collect_tags(el, obj_id, model)
            continue

        appearance = _parse_appearance(
            style.get("appearance") if style is not None else None
        )

        is_abstract = props.get("isAbstract") if props is not None else None
        model.elements.append(
            QeaElement(
                Object_ID=obj_id,
                Object_Type=s_type,
                Name=name,
                Package_ID=pkg_id,
                Note=documentation,
                ea_guid=idref,
                Status=project.get("status") if project is not None else None,
                Stereotype=props.get("stereotype") if props is not None else None,
                Version=project.get("version") if project is not None else None,
                Scope=props.get("scope") if props is not None else _attr(el, "scope"),
                Abstract="1" if is_abstract == "true" else None,
                Author=project.get("author") if project is not None else None,
                Complexity=project.get("complexity") if project is not None else None,
                Phase=project.get("phase") if project is not None else None,
                CreatedDate=project.get("created") if project is not None else None,
                ModifiedDate=project.get("modified") if project is not None else None,
                GenType=code.get("gentype") if code is not None else None,
                Backcolor=appearance.get("BackColor"),
                Fontcolor=appearance.get("FontColor"),
                Bordercolor=appearance.get("BorderColor"),
                BorderWidth=appearance.get("BorderWidth"),
                Alias=props.get("alias") if props is not None else None,
            )
        )
        _collect_attributes(el, obj_id, model)
        _collect_tags(el, obj_id, model)

    # ── Pass 3: connectors ──────────────────────────────────────────────
    for cn in conn_list:
        idref = _attr(cn, "idref")
        conn_id = guid_to_int.get(idref, -1) if idref else -1
        src = _child(cn, "source")
        tgt = _child(cn, "target")
        start_id = _connector_endpoint_id(src, guid_to_int)
        end_id = _connector_endpoint_id(tgt, guid_to_int)
        props = _child(cn, "properties")
        appearance = _child(cn, "appearance")
        documentation = _child(cn, "documentation")

        model.connectors.append(
            QeaConnector(
                Connector_ID=conn_id,
                Connector_Type=props.get("ea_type") if props is not None else None,
                Name=_attr(cn, "name"),
                Start_Object_ID=start_id,
                End_Object_ID=end_id,
                ea_guid=idref,
                Notes=documentation.get("value") if documentation is not None else None,
                Direction=props.get("direction") if props is not None else None,
                Stereotype=props.get("stereotype") if props is not None else None,
                SourceIsAggregate=_agg_to_int(_cattr(src, "type", "aggregation")),
                DestIsAggregate=_agg_to_int(_cattr(tgt, "type", "aggregation")),
                LineColor=_int_or_none(
                    appearance.get("linecolor") if appearance is not None else None
                ),
                LineStyle=_int_or_none(
                    appearance.get("lineStyle") if appearance is not None else None
                ),
            )
        )

    # ── Pass 4: diagrams + diagram objects + diagram links ──────────────
    for dg in diag_list:
        dg_guid = _attr(dg, "id")
        diag_id = guid_to_int.get(dg_guid, -1) if dg_guid else -1
        m = _child(dg, "model")
        props = _child(dg, "properties")
        pkg_guid = m.get("package") if m is not None else None
        # ADR-221: a composite (element-owned) diagram carries an `owner`
        # GUID that differs from its containing package. Map it to the
        # owning element's int id so the orchestrator can set that
        # element's detail_diagram_id. A package-owned diagram (owner ==
        # package) is not composite → leave ParentID unset. The
        # orchestrator further filters to element ids, so a stray
        # non-element owner is harmless.
        owner_guid = m.get("owner") if m is not None else None
        parent_id = (
            guid_to_int.get(owner_guid)
            if owner_guid and owner_guid != pkg_guid
            else None
        )

        cx = cy = None
        style1 = _child(dg, "style1")
        if style1 is not None:
            sval = style1.get("value") or ""
            cx_m = re.search(r"DocSize\.cx=(\d+)", sval)
            cy_m = re.search(r"DocSize\.cy=(\d+)", sval)
            cx = int(cx_m.group(1)) if cx_m else None
            cy = int(cy_m.group(1)) if cy_m else None

        model.diagrams.append(
            QeaDiagram(
                Diagram_ID=diag_id,
                Name=props.get("name") if props is not None else None,
                Diagram_Type=props.get("type") if props is not None else None,
                Package_ID=guid_to_int.get(pkg_guid, 0) if pkg_guid else 0,
                ea_guid=dg_guid,
                Notes=props.get("documentation") if props is not None else None,
                cx=cx,
                cy=cy,
                ParentID=parent_id,
            )
        )

        for de in _children(_child(dg, "elements"), "element"):
            subject = _attr(de, "subject")
            subj_id = guid_to_int.get(subject) if subject else None
            if subj_id is None:
                continue
            geom = _attr(de, "geometry")
            rect = _parse_geometry_rect(geom)
            if rect is not None:
                # Normalise to the .qea convention (negative Y, Top > Bottom) so
                # the existing ea_rect_to_position is reused unchanged.
                model.diagram_objects.append(
                    QeaDiagramObject(
                        Diagram_ID=diag_id,
                        Object_ID=subj_id,
                        RectLeft=rect["Left"],
                        RectRight=rect["Right"],
                        RectTop=-rect["Top"],
                        RectBottom=-rect["Bottom"],
                        ObjectStyle=_attr(de, "style"),
                    )
                )
            elif geom and "EDGE=" in geom:
                model.diagram_links.append(
                    QeaDiagramLink(
                        DiagramID=diag_id,
                        ConnectorID=subj_id,
                        Geometry=geom,
                    )
                )

    return model


def _connector_endpoint_id(
    endpoint: ET.Element | None, guid_to_int: dict[str, int]
) -> int:
    """Resolve a connector <source>/<target> to its element integer id."""
    if endpoint is None:
        return -1
    ep_model = _child(endpoint, "model")
    local = ep_model.get("ea_localid") if ep_model is not None else None
    iid = _int_or_none(local)
    if iid is not None:
        return iid
    return guid_to_int.get(_attr(endpoint, "idref") or "", -1)


def _collect_tags(el: ET.Element, obj_id: int, model: SparxXmiModel) -> None:
    tags = _child(el, "tags")
    for tag in _children(tags, "tag"):
        model.tagged_values.append(
            QeaTaggedValue(
                Object_ID=obj_id,
                Property=tag.get("name"),
                Value=tag.get("value"),
            )
        )


def _collect_attributes(el: ET.Element, obj_id: int, model: SparxXmiModel) -> None:
    attrs = _child(el, "attributes")
    for attr in _children(attrs, "attribute"):
        props = _child(attr, "properties")
        bounds = _child(attr, "bounds")
        model.attributes.append(
            QeaAttribute(
                Object_ID=obj_id,
                Name=_attr(attr, "name"),
                Type=props.get("type") if props is not None else None,
                Notes=props.get("documentation") if props is not None else None,
                LowerBound=bounds.get("lower") if bounds is not None else None,
                UpperBound=bounds.get("upper") if bounds is not None else None,
                Stereotype=_cattr(attr, "stereotype", "stereotype"),
                Scope=_attr(attr, "scope"),
            )
        )
