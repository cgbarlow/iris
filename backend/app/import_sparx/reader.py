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


@dataclass
class QeaElement:
    Object_ID: int
    Object_Type: str | None
    Name: str | None
    Package_ID: int
    Note: str | None
    ea_guid: str | None


@dataclass
class QeaConnector:
    Connector_ID: int
    Connector_Type: str | None
    Name: str | None
    Start_Object_ID: int
    End_Object_ID: int
    ea_guid: str | None


@dataclass
class QeaDiagram:
    Diagram_ID: int
    Name: str | None
    Diagram_Type: str | None
    Package_ID: int
    ea_guid: str | None


@dataclass
class QeaDiagramObject:
    Diagram_ID: int
    Object_ID: int
    RectTop: int
    RectBottom: int
    RectLeft: int
    RectRight: int


@dataclass
class QeaAttribute:
    Object_ID: int
    Name: str | None
    Type: str | None


async def read_packages(db_path: str) -> list[QeaPackage]:
    """Read all packages from a .qea file."""
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT Package_ID, Name, Parent_ID, ea_guid FROM t_package"
        )
        rows = await cursor.fetchall()
        return [
            QeaPackage(
                Package_ID=row[0],
                Name=row[1],
                Parent_ID=row[2] or 0,
                ea_guid=row[3],
            )
            for row in rows
        ]


async def read_elements(db_path: str) -> list[QeaElement]:
    """Read all elements from a .qea file."""
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT Object_ID, Object_Type, Name, Package_ID, Note, ea_guid "
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
            )
            for row in rows
        ]


async def read_connectors(db_path: str) -> list[QeaConnector]:
    """Read all connectors from a .qea file."""
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT Connector_ID, Connector_Type, Name, "
            "Start_Object_ID, End_Object_ID, ea_guid "
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
            )
            for row in rows
        ]


async def read_diagrams(db_path: str) -> list[QeaDiagram]:
    """Read all diagrams from a .qea file."""
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT Diagram_ID, Name, Diagram_Type, Package_ID, ea_guid "
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
            )
            for row in rows
        ]


async def read_diagram_objects(db_path: str) -> list[QeaDiagramObject]:
    """Read all diagram object placements from a .qea file."""
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT Diagram_ID, Object_ID, RectTop, RectBottom, "
            "RectLeft, RectRight FROM t_diagramobjects"
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
            )
            for row in rows
        ]


async def read_attributes(db_path: str) -> list[QeaAttribute]:
    """Read all element attributes from a .qea file."""
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT Object_ID, Name, Type FROM t_attribute ORDER BY Pos"
        )
        rows = await cursor.fetchall()
        return [
            QeaAttribute(
                Object_ID=row[0] or 0,
                Name=row[1],
                Type=row[2],
            )
            for row in rows
        ]
