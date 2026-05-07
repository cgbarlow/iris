"""ArchiMate Open Exchange File Format (OEX) reader.

Parses the XML serialisation defined by The Open Group at
http://www.opengroup.org/xsd/archimate/ and produces dataclasses that the
import service can walk. We use stdlib ``xml.etree.ElementTree`` to avoid a
new dependency.

Supports the 3.0 / 3.1 / 3.2 family — the namespace URI is checked by
prefix so future minor revisions don't break the parser.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

# Open Group namespaces published for OEX. The 3.0 URI is shared by 3.1 and
# 3.2 in practice (Archi tool emits the 3.0 URI for all of them).
_NS_PREFIX_RE = re.compile(r"^http://www\.opengroup\.org/xsd/archimate/3\.\d+/?$")
_NS_3_0 = "http://www.opengroup.org/xsd/archimate/3.0/"
_XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
_XSI_TYPE = "{http://www.w3.org/2001/XMLSchema-instance}type"


@dataclass
class OexElement:
    identifier: str
    xsi_type: str
    name: str
    documentation: str | None = None


@dataclass
class OexRelationship:
    identifier: str
    source: str
    target: str
    xsi_type: str
    name: str | None = None


@dataclass
class OexNode:
    identifier: str
    element_ref: str | None
    x: int
    y: int
    w: int
    h: int
    children: list["OexNode"] = field(default_factory=list)


@dataclass
class OexConnection:
    identifier: str
    relationship_ref: str | None
    source: str
    target: str


@dataclass
class OexView:
    identifier: str
    name: str
    nodes: list[OexNode] = field(default_factory=list)
    connections: list[OexConnection] = field(default_factory=list)


@dataclass
class OexModel:
    name: str
    documentation: str | None
    elements: list[OexElement] = field(default_factory=list)
    relationships: list[OexRelationship] = field(default_factory=list)
    views: list[OexView] = field(default_factory=list)


def _ns(tree_root: ET.Element) -> str:
    """Extract and validate the OEX namespace from the root element tag."""
    tag = tree_root.tag
    if not (tag.startswith("{") and "}" in tag):
        raise ValueError("not an ArchiMate Open Exchange file (no namespace)")
    ns = tag[1 : tag.index("}")]
    if not _NS_PREFIX_RE.match(ns):
        raise ValueError(f"unsupported ArchiMate OEX namespace: {ns}")
    if not tag.endswith("}model"):
        raise ValueError("not an ArchiMate Open Exchange file (root is not <model>)")
    return ns


def _q(ns: str, name: str) -> str:
    return f"{{{ns}}}{name}"


def _localised_text(parent: ET.Element, ns: str, tag: str) -> str | None:
    """Return text from a child <name>/<documentation>; prefer xml:lang='en'."""
    candidates = parent.findall(_q(ns, tag))
    if not candidates:
        return None
    en = next((c for c in candidates if c.get(_XML_LANG) == "en"), None)
    chosen = en if en is not None else candidates[0]
    return (chosen.text or "").strip() or None


def _int_attr(node: ET.Element, name: str, default: int = 0) -> int:
    raw = node.get(name)
    if raw is None:
        return default
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return default


def _parse_nodes(parent: ET.Element, ns: str) -> list[OexNode]:
    out: list[OexNode] = []
    for n in parent.findall(_q(ns, "node")):
        node = OexNode(
            identifier=n.get("identifier") or "",
            element_ref=n.get("elementRef"),
            x=_int_attr(n, "x"),
            y=_int_attr(n, "y"),
            w=_int_attr(n, "w", default=120),
            h=_int_attr(n, "h", default=60),
            children=_parse_nodes(n, ns),
        )
        out.append(node)
    return out


def parse_oex(path: str) -> OexModel:
    """Parse an OEX file and return an OexModel.

    Raises ``ValueError`` if the file is not a valid ArchiMate OEX document.
    """
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        raise ValueError(f"file is not valid XML: {exc}") from exc
    root = tree.getroot()
    ns = _ns(root)

    name = _localised_text(root, ns, "name") or "ArchiMate Model"
    documentation = _localised_text(root, ns, "documentation")

    elements: list[OexElement] = []
    elements_parent = root.find(_q(ns, "elements"))
    if elements_parent is not None:
        for el in elements_parent.findall(_q(ns, "element")):
            elements.append(
                OexElement(
                    identifier=el.get("identifier") or "",
                    xsi_type=(el.get(_XSI_TYPE) or "").strip(),
                    name=_localised_text(el, ns, "name") or "",
                    documentation=_localised_text(el, ns, "documentation"),
                )
            )

    relationships: list[OexRelationship] = []
    rels_parent = root.find(_q(ns, "relationships"))
    if rels_parent is not None:
        for rel in rels_parent.findall(_q(ns, "relationship")):
            relationships.append(
                OexRelationship(
                    identifier=rel.get("identifier") or "",
                    source=rel.get("source") or "",
                    target=rel.get("target") or "",
                    xsi_type=(rel.get(_XSI_TYPE) or "").strip(),
                    name=_localised_text(rel, ns, "name"),
                )
            )

    views: list[OexView] = []
    views_parent = root.find(_q(ns, "views"))
    if views_parent is not None:
        # ArchiMate 3.x wraps views inside <diagrams>; older drafts wrote
        # <view> directly under <views>. Accept both.
        diagrams_parent = views_parent.find(_q(ns, "diagrams"))
        if diagrams_parent is None:
            diagrams_parent = views_parent
        for v in diagrams_parent.findall(_q(ns, "view")):
            connections: list[OexConnection] = []
            for c in v.findall(_q(ns, "connection")):
                connections.append(
                    OexConnection(
                        identifier=c.get("identifier") or "",
                        relationship_ref=c.get("relationshipRef"),
                        source=c.get("source") or "",
                        target=c.get("target") or "",
                    )
                )
            views.append(
                OexView(
                    identifier=v.get("identifier") or "",
                    name=_localised_text(v, ns, "name") or "View",
                    nodes=_parse_nodes(v, ns),
                    connections=connections,
                )
            )

    return OexModel(
        name=name,
        documentation=documentation,
        elements=elements,
        relationships=relationships,
        views=views,
    )


def is_oex_file(path: str) -> bool:
    """Cheap content sniff used by the router to reject non-OEX uploads."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(4096)
    except OSError:
        return False
    return _NS_3_0.encode("utf-8") in head or b"http://www.opengroup.org/xsd/archimate/3." in head


__all__ = [
    "OexConnection",
    "OexElement",
    "OexModel",
    "OexNode",
    "OexRelationship",
    "OexView",
    "is_oex_file",
    "parse_oex",
]
