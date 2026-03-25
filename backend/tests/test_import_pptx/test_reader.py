"""Tests for PPTX reader — shape extraction, fill colours, hyperlinks, geometry."""

from __future__ import annotations

from app.import_pptx.reader import PptxShape, PptxSlide, read_pptx


class TestReadPptx:
    """read_pptx() extracts slides and shapes from a DoView PPTX."""

    def test_returns_correct_slide_count(self, minimal_doview_pptx: str) -> None:
        slides = read_pptx(minimal_doview_pptx)
        assert len(slides) == 4

    def test_slide_indices_are_sequential(self, minimal_doview_pptx: str) -> None:
        slides = read_pptx(minimal_doview_pptx)
        assert [s.index for s in slides] == [0, 1, 2, 3]

    def test_overview_slide_has_shapes(self, minimal_doview_pptx: str) -> None:
        slides = read_pptx(minimal_doview_pptx)
        # Overview: title textbox + Final Outcomes rect + grey bar + 3 tiles + footer
        assert len(slides[0].shapes) >= 5

    def test_shapes_are_pptx_shape_instances(self, minimal_doview_pptx: str) -> None:
        slides = read_pptx(minimal_doview_pptx)
        for slide in slides:
            for shape in slide.shapes:
                assert isinstance(shape, PptxShape)


class TestFillColorExtraction:
    """Fill colours are extracted as hex strings."""

    def test_coloured_rect_has_fill(self, minimal_doview_pptx: str) -> None:
        slides = read_pptx(minimal_doview_pptx)
        # Find the "Topic Alpha" tile on overview (fill=FFFFBA)
        overview = slides[0]
        alpha = [s for s in overview.shapes if "Topic Alpha" in s.text]
        assert len(alpha) == 1
        assert alpha[0].fill_color == "FFFFBA"

    def test_white_rect_has_ffffff(self, minimal_doview_pptx: str) -> None:
        slides = read_pptx(minimal_doview_pptx)
        overview = slides[0]
        fo = [s for s in overview.shapes if s.text == "Final Outcomes"]
        assert len(fo) == 1
        assert fo[0].fill_color == "FFFFFF"

    def test_grey_bar_has_bebebe(self, minimal_doview_pptx: str) -> None:
        slides = read_pptx(minimal_doview_pptx)
        overview = slides[0]
        grey_bars = [s for s in overview.shapes if s.fill_color == "BEBEBE"]
        assert len(grey_bars) >= 1
        assert grey_bars[0].height == 18000

    def test_textbox_has_no_fill(self, minimal_doview_pptx: str) -> None:
        slides = read_pptx(minimal_doview_pptx)
        overview = slides[0]
        footers = [s for s in overview.shapes if s.is_textbox and "Footer" in s.text]
        assert len(footers) >= 1
        assert footers[0].fill_color is None


class TestHyperlinkResolution:
    """Shape hyperlinks resolve to correct slide indices."""

    def test_overview_tile_links_to_slide(self, minimal_doview_pptx: str) -> None:
        slides = read_pptx(minimal_doview_pptx)
        overview = slides[0]
        alpha = [s for s in overview.shapes if "Topic Alpha" in s.text]
        assert len(alpha) == 1
        # Should link to slide 2 (outcomes map)
        assert alpha[0].hyperlink_slide_index == 2

    def test_final_outcomes_tile_links_to_slide(self, minimal_doview_pptx: str) -> None:
        slides = read_pptx(minimal_doview_pptx)
        overview = slides[0]
        fo = [s for s in overview.shapes if s.text == "Final Outcomes"]
        assert len(fo) == 1
        assert fo[0].hyperlink_slide_index == 1

    def test_back_to_overview_links_to_slide_0(self, minimal_doview_pptx: str) -> None:
        slides = read_pptx(minimal_doview_pptx)
        s1 = slides[1]
        back = [s for s in s1.shapes if "Back to Overview" in s.text]
        assert len(back) == 1
        assert back[0].hyperlink_slide_index == 0

    def test_shape_without_hyperlink_is_none(self, minimal_doview_pptx: str) -> None:
        slides = read_pptx(minimal_doview_pptx)
        s2 = slides[2]
        outcome = [s for s in s2.shapes if s.text == "Step one done"]
        assert len(outcome) == 1
        assert outcome[0].hyperlink_slide_index is None


class TestArrowGeometry:
    """rightArrow shapes are detected via preset geometry."""

    def test_arrow_has_right_arrow_geometry(self, minimal_doview_pptx: str) -> None:
        slides = read_pptx(minimal_doview_pptx)
        s2 = slides[2]
        arrows = [s for s in s2.shapes if s.preset_geometry and "arrow" in s.preset_geometry.lower()]
        assert len(arrows) >= 1

    def test_arrow_has_grey_fill(self, minimal_doview_pptx: str) -> None:
        slides = read_pptx(minimal_doview_pptx)
        s2 = slides[2]
        arrows = [s for s in s2.shapes if s.preset_geometry and "arrow" in s.preset_geometry.lower()]
        assert arrows[0].fill_color == "C8C8C8"


class TestTextboxDetection:
    """Text boxes are distinguished from auto shapes."""

    def test_textbox_flagged(self, minimal_doview_pptx: str) -> None:
        slides = read_pptx(minimal_doview_pptx)
        overview = slides[0]
        textboxes = [s for s in overview.shapes if s.is_textbox]
        assert len(textboxes) >= 1

    def test_rect_not_textbox(self, minimal_doview_pptx: str) -> None:
        slides = read_pptx(minimal_doview_pptx)
        overview = slides[0]
        tiles = [s for s in overview.shapes if "Topic Alpha" in s.text]
        assert tiles[0].is_textbox is False


class TestNonDoviewPptx:
    """Non-DoView PPTX files parse without error."""

    def test_reads_without_error(self, non_doview_pptx: str) -> None:
        slides = read_pptx(non_doview_pptx)
        assert len(slides) == 2

    def test_no_hyperlinks(self, non_doview_pptx: str) -> None:
        slides = read_pptx(non_doview_pptx)
        for slide in slides:
            for shape in slide.shapes:
                assert shape.hyperlink_slide_index is None
