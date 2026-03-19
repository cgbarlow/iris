"""Tests for auto-handle computation from node geometry (ADR-088).

Verifies compute_auto_handles() returns correct handle side pairs
based on relative node center positions.
"""

from __future__ import annotations

from app.import_sparx.service import compute_auto_handles


class TestComputeAutoHandles:
    """Verify handle selection based on relative node positions."""

    def test_horizontal_right(self) -> None:
        """Target to the right of source → right/left."""
        result = compute_auto_handles(0, 0, 100, 60, 300, 0, 100, 60)
        assert result == ("right", "left")

    def test_horizontal_left(self) -> None:
        """Target to the left of source → left/right."""
        result = compute_auto_handles(300, 0, 100, 60, 0, 0, 100, 60)
        assert result == ("left", "right")

    def test_vertical_below(self) -> None:
        """Target below source → bottom/top."""
        result = compute_auto_handles(0, 0, 100, 60, 0, 200, 100, 60)
        assert result == ("bottom", "top")

    def test_vertical_above(self) -> None:
        """Target above source → top/bottom."""
        result = compute_auto_handles(0, 200, 100, 60, 0, 0, 100, 60)
        assert result == ("top", "bottom")

    def test_diagonal_predominantly_horizontal(self) -> None:
        """Diagonal with larger dx → horizontal handles."""
        result = compute_auto_handles(0, 0, 100, 60, 400, 50, 100, 60)
        assert result == ("right", "left")

    def test_diagonal_predominantly_vertical(self) -> None:
        """Diagonal with larger dy → vertical handles."""
        result = compute_auto_handles(0, 0, 100, 60, 50, 400, 100, 60)
        assert result == ("bottom", "top")
