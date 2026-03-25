"""Shared types for import modules (SparxEA, DoView PPTX, etc.)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ImportWarning:
    category: str
    message: str
