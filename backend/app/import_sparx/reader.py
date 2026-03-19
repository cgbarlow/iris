"""Read SparxEA .qea (SQLite) files into dataclasses."""

from __future__ import annotations

from dataclasses import dataclass

import aiosqlite


@dataclass
class QeaPackage:
    Package_ID: int
    Name: str | None
    Parent_ID: int
    ea_guid: str | None
    Notes: str | None = None


@dataclass
class QeaElement:
    Object_ID: int
    Object_Type: str | None
    Name: str | None
    Package_ID: int
    Note: str | None
    ea_guid: str | None
    Status: str | None = None
    Stereotype: str | None = None
    Version: str | None = None
    Scope: str | None = None
    Abstract: str | None = None
    Persistence: str | None = None
    Author: str | None = None
    Complexity: str | None = None
    Phase: str | None = None
    CreatedDate: str | None = None
    ModifiedDate: str | None = None
    GenType: str | None = None
    Backcolor: int | None = None
    Fontcolor: int | None = None
    Bordercolor: int | None = None
    BorderWidth: int | None = None
    Alias: str | None = None
    PDATA1: str | None = None
    StyleEx: str | None = None


@dataclass
class QeaConnector:
    Connector_ID: int
    Connector_Type: str | None
    Name: str | None
    Start_Object_ID: int
    End_Object_ID: int
    ea_guid: str | None
    Notes: str | None = None
    Direction: str | None = None
    SourceCard: str | None = None
    DestCard: str | None = None
    SourceRole: str | None = None
    DestRole: str | None = None
    SourceAccess: str | None = None
    DestAccess: str | None = None
    Stereotype: str | None = None
    RouteStyle: int | None = None
    SourceIsNavigable: str | None = None
    DestIsNavigable: str | None = None
    SourceIsAggregate: int | None = None
    DestIsAggregate: int | None = None
    LineColor: int | None = None
    IsBold: int | None = None
    LineStyle: int | None = None
    Start_Edge: int | None = None
    End_Edge: int | None = None
    PtStartX: int | None = None
    PtStartY: int | None = None
    PtEndX: int | None = None
    PtEndY: int | None = None


@dataclass
class QeaDiagramLink:
    DiagramID: int
    ConnectorID: int
    Geometry: str | None = None
    Style: str | None = None
    Hidden: int = 0
    Path: str | None = None


@dataclass
class QeaDiagram:
    Diagram_ID: int
    Name: str | None
    Diagram_Type: str | None
    Package_ID: int
    ea_guid: str | None
    Notes: str | None = None
    cx: int | None = None
    cy: int | None = None


@dataclass
class QeaDiagramObject:
    Diagram_ID: int
    Object_ID: int
    RectTop: int
    RectBottom: int
    RectLeft: int
    RectRight: int
    ObjectStyle: str | None = None


@dataclass
class QeaTaggedValue:
    Object_ID: int
    Property: str | None
    Value: str | None


@dataclass
class QeaAttribute:
    Object_ID: int
    Name: str | None
    Type: str | None
    Notes: str | None = None
    Default: str | None = None
    LowerBound: str | None = None
    UpperBound: str | None = None
    Stereotype: str | None = None
    Scope: str | None = None


async def read_packages(db_path: str) -> list[QeaPackage]:
    """Read all packages from a .qea file."""
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT Package_ID, Name, Parent_ID, ea_guid, Notes FROM t_package"
        )
        rows = await cursor.fetchall()
        return [
            QeaPackage(
                Package_ID=row[0],
                Name=row[1],
                Parent_ID=row[2] or 0,
                ea_guid=row[3],
                Notes=row[4],
            )
            for row in rows
        ]


async def read_elements(db_path: str) -> list[QeaElement]:
    """Read all elements from a .qea file."""
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT Object_ID, Object_Type, Name, Package_ID, Note, ea_guid, "
            "Status, Stereotype, Version, Scope, Abstract, Persistence, "
            "Author, Complexity, Phase, CreatedDate, ModifiedDate, GenType, "
            "Backcolor, Fontcolor, Bordercolor, BorderWidth, Alias, PDATA1, StyleEx "
            "FROM t_object"
        )
        rows = await cursor.fetchall()
        return [
            QeaElement(
                Object_ID=row[0],
                Object_Type=row[1],
                Name=row[2],
                Package_ID=row[3] or 0,
                Note=row[4],
                ea_guid=row[5],
                Status=row[6],
                Stereotype=row[7],
                Version=row[8],
                Scope=row[9],
                Abstract=row[10],
                Persistence=row[11],
                Author=row[12],
                Complexity=row[13],
                Phase=row[14],
                CreatedDate=row[15],
                ModifiedDate=row[16],
                GenType=row[17],
                Backcolor=row[18],
                Fontcolor=row[19],
                Bordercolor=row[20],
                BorderWidth=row[21],
                Alias=row[22],
                PDATA1=row[23],
                StyleEx=row[24],
            )
            for row in rows
        ]


async def read_connectors(db_path: str) -> list[QeaConnector]:
    """Read all connectors from a .qea file."""
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT Connector_ID, Connector_Type, Name, "
            "Start_Object_ID, End_Object_ID, ea_guid, Notes, "
            "Direction, SourceCard, DestCard, SourceRole, DestRole, "
            "SourceAccess, DestAccess, "
            "Stereotype, RouteStyle, SourceIsNavigable, DestIsNavigable, "
            "SourceIsAggregate, DestIsAggregate, "
            "LineColor, IsBold, LineStyle, "
            "Start_Edge, End_Edge, PtStartX, PtStartY, PtEndX, PtEndY "
            "FROM t_connector"
        )
        rows = await cursor.fetchall()
        return [
            QeaConnector(
                Connector_ID=row[0],
                Connector_Type=row[1],
                Name=row[2],
                Start_Object_ID=row[3] or 0,
                End_Object_ID=row[4] or 0,
                ea_guid=row[5],
                Notes=row[6],
                Direction=row[7],
                SourceCard=row[8],
                DestCard=row[9],
                SourceRole=row[10],
                DestRole=row[11],
                SourceAccess=row[12],
                DestAccess=row[13],
                Stereotype=row[14],
                RouteStyle=row[15],
                SourceIsNavigable=str(row[16]) if row[16] is not None else None,
                DestIsNavigable=str(row[17]) if row[17] is not None else None,
                SourceIsAggregate=row[18],
                DestIsAggregate=row[19],
                LineColor=row[20],
                IsBold=row[21],
                LineStyle=row[22],
                Start_Edge=row[23],
                End_Edge=row[24],
                PtStartX=row[25],
                PtStartY=row[26],
                PtEndX=row[27],
                PtEndY=row[28],
            )
            for row in rows
        ]


async def read_diagrams(db_path: str) -> list[QeaDiagram]:
    """Read all diagrams from a .qea file."""
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT Diagram_ID, Name, Diagram_Type, Package_ID, ea_guid, Notes, cx, cy "
            "FROM t_diagram"
        )
        rows = await cursor.fetchall()
        return [
            QeaDiagram(
                Diagram_ID=row[0],
                Name=row[1],
                Diagram_Type=row[2],
                Package_ID=row[3] or 0,
                ea_guid=row[4],
                Notes=row[5],
                cx=row[6],
                cy=row[7],
            )
            for row in rows
        ]


async def read_diagram_links(db_path: str) -> list[QeaDiagramLink]:
    """Read all diagram link placements from a .qea/.eap file."""
    async with aiosqlite.connect(db_path) as db:
        try:
            cursor = await db.execute(
                "SELECT DiagramID, ConnectorID, Geometry, Style, Hidden, Path "
                "FROM t_diagramlinks"
            )
        except Exception:
            # Table may not exist in older .eap files
            return []
        rows = await cursor.fetchall()
        return [
            QeaDiagramLink(
                DiagramID=row[0] or 0,
                ConnectorID=row[1] or 0,
                Geometry=row[2],
                Style=row[3],
                Hidden=row[4] or 0,
                Path=row[5],
            )
            for row in rows
        ]


async def read_diagram_objects(db_path: str) -> list[QeaDiagramObject]:
    """Read all diagram object placements from a .qea file."""
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT Diagram_ID, Object_ID, RectTop, RectBottom, "
            "RectLeft, RectRight, ObjectStyle FROM t_diagramobjects"
        )
        rows = await cursor.fetchall()
        return [
            QeaDiagramObject(
                Diagram_ID=row[0] or 0,
                Object_ID=row[1] or 0,
                RectTop=row[2] or 0,
                RectBottom=row[3] or 0,
                RectLeft=row[4] or 0,
                RectRight=row[5] or 0,
                ObjectStyle=row[6],
            )
            for row in rows
        ]


async def read_attributes(db_path: str) -> list[QeaAttribute]:
    """Read all element attributes from a .qea file."""
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            'SELECT Object_ID, Name, Type, Notes, "Default", '
            "LowerBound, UpperBound, Stereotype, Scope "
            "FROM t_attribute ORDER BY Pos"
        )
        rows = await cursor.fetchall()
        return [
            QeaAttribute(
                Object_ID=row[0] or 0,
                Name=row[1],
                Type=row[2],
                Notes=row[3],
                Default=row[4],
                LowerBound=row[5],
                UpperBound=row[6],
                Stereotype=row[7],
                Scope=row[8],
            )
            for row in rows
        ]


async def read_tagged_values(db_path: str) -> list[QeaTaggedValue]:
    """Read all tagged values from a .qea file."""
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT Object_ID, Property, Value FROM t_objectproperties"
        )
        rows = await cursor.fetchall()
        return [
            QeaTaggedValue(
                Object_ID=row[0] or 0,
                Property=row[1],
                Value=row[2],
            )
            for row in rows
        ]
