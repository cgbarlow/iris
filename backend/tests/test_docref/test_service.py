"""Unit tests for DocRef service functions (ADR-112)."""

from __future__ import annotations

import pytest

from app.docref.service import _parse_index_html, _slug_to_title


class TestSlugToTitle:
    def test_simple_slug(self) -> None:
        assert _slug_to_title("social-security-act-2018") == "Social Security Act 2018"

    def test_slug_with_numbers(self) -> None:
        assert _slug_to_title("crimes-act-1961") == "Crimes Act 1961"

    def test_single_word(self) -> None:
        assert _slug_to_title("act") == "Act"


class TestParseIndexHtml:
    def test_extracts_documents_from_table(self) -> None:
        html = '''
        <table>
        <tr><td><a href="/social-security-act-2018/2025-07-01/en/">Social Security Act 2018</a> <span class="badge">39</span></td>
        <td>2025-07-01</td></tr>
        <tr><td><a href="/crimes-act-1961/2025-11-27/en/">Crimes Act 1961</a> <span class="badge">57</span></td>
        <td>2025-11-27</td></tr>
        </table>
        '''
        docs = _parse_index_html(html)
        assert len(docs) == 2
        assert docs[0]["slug"] == "social-security-act-2018"
        assert docs[0]["title"] == "Social Security Act 2018"
        assert docs[0]["latest_version"] == "2025-07-01"
        assert docs[1]["slug"] == "crimes-act-1961"
        assert docs[1]["latest_version"] == "2025-11-27"

    def test_empty_html_returns_empty(self) -> None:
        docs = _parse_index_html("<html><body>No table</body></html>")
        assert docs == []

    def test_skips_nav_links(self) -> None:
        html = '''
        <tr><td><a href="/about/2024-01-01/en/">About</a></td><td>2024-01-01</td></tr>
        <tr><td><a href="/crimes-act-1961/2025-11-27/en/">Crimes Act 1961</a></td><td>2025-11-27</td></tr>
        '''
        docs = _parse_index_html(html)
        assert len(docs) == 1
        assert docs[0]["slug"] == "crimes-act-1961"
