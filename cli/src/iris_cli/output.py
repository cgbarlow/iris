"""Output helpers — rich tables for humans, JSON for machines."""

from __future__ import annotations

import json
import sys
from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel
from rich.console import Console
from rich.table import Table

_err = Console(stderr=True)
_out = Console()


def print_table(
    rows: Iterable[dict[str, Any]] | Iterable[BaseModel],
    *,
    columns: list[str],
    title: str | None = None,
) -> None:
    """Render a list of dicts/models as a Rich table."""
    table = Table(title=title, show_header=True, header_style="bold")
    for col in columns:
        table.add_column(col)
    for row in rows:
        data = row.model_dump() if isinstance(row, BaseModel) else row
        table.add_row(*[_cell(data.get(c)) for c in columns])
    _out.print(table)


def print_json(payload: Any) -> None:
    sys.stdout.write(json.dumps(_jsonable(payload), indent=2, default=str))
    sys.stdout.write("\n")


def print_error(message: str) -> None:
    _err.print(f"[red]Error:[/red] {message}")


def _cell(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value)
    return str(value)


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    return value
