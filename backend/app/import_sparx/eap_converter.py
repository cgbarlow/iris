"""Convert Sparx EA .eap (JET4/MDB) files to SQLite for import."""

from __future__ import annotations

import asyncio
import logging
import shutil
import tempfile

import aiosqlite

logger = logging.getLogger(__name__)

REQUIRED_TABLES = [
    "t_package",
    "t_object",
    "t_connector",
    "t_diagram",
    "t_diagramobjects",
    "t_attribute",
    "t_objectproperties",
]

# JET 4.0 magic bytes at offset 0: \x00\x01\x00\x00Standard Jet DB
_JET4_SIGNATURE = b"\x00\x01\x00\x00Standard Jet DB"


def is_jet4_file(path: str) -> bool:
    """Check if a file is a JET 4.0 (MDB) database by reading the header."""
    try:
        with open(path, "rb") as f:
            header = f.read(20)
        return header[:19] == _JET4_SIGNATURE
    except (OSError, ValueError):
        return False


async def _run_mdbtools_command(cmd: list[str]) -> str:
    """Run an mdbtools command and return stdout."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(
            f"mdbtools command failed: {' '.join(cmd)}\n{stderr.decode().strip()}"
        )
    return stdout.decode()


async def convert_eap_to_sqlite(eap_path: str) -> str:
    """Convert a .eap (MDB/JET4) file to a temporary SQLite database.

    Uses mdbtools CLI to extract schema and data from the MDB file,
    then loads them into a new SQLite database.

    Returns the path to the temporary SQLite file. Caller must clean up.

    Raises:
        RuntimeError: If mdbtools is not installed.
        ValueError: If the file is not a JET4 (MDB) file.
    """
    if not shutil.which("mdb-tables"):
        raise RuntimeError(
            "mdbtools is not installed. Install with: sudo apt install mdbtools"
        )

    if not is_jet4_file(eap_path):
        raise ValueError("File is not a JET4 (MDB) file")

    tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
    sqlite_path = tmp.name
    tmp.close()

    async with aiosqlite.connect(sqlite_path) as db:
        for table in REQUIRED_TABLES:
            try:
                ddl = await _run_mdbtools_command(
                    ["mdb-schema", "-T", table, eap_path, "sqlite"]
                )
            except RuntimeError:
                logger.warning("Table %s not found in EAP file, skipping", table)
                continue

            if not ddl.strip():
                logger.warning("Empty schema for table %s, skipping", table)
                continue

            # Execute CREATE TABLE
            await db.executescript(ddl)

            # Export INSERT statements
            try:
                inserts = await _run_mdbtools_command(
                    ["mdb-export", "-I", "sqlite", eap_path, table]
                )
            except RuntimeError:
                logger.warning("Failed to export data for table %s, skipping", table)
                continue

            if inserts.strip():
                await db.executescript(inserts)

        await db.commit()

    return sqlite_path
