"""Tests for slide/shape classification into DoView types."""

from __future__ import annotations

from app.import_pptx.classifier import (
    ClassifiedSlide,
    ShapeRole,
    SlideType,
    classify_slides,
    group_into_columns,
)
from app.import_pptx.reader import PptxShape, read_pptx


class TestSlideClassification:
    """classify_slides() assigns correct slide types."""

    def test_overview_slide_detected(self, minimal_doview_pptx: str) -> None:
        slides = read_pptx(minimal_doview_pptx)
        classified = classify_slides(slides)
        assert classified[0].slide_type == SlideType.OVERVIEW

    def test_final_outcomes_slide_detected(self, minimal_doview_pptx: str) -> None:
        slides = read_pptx(minimal_doview_pptx)
        classified = classify_slides(slides)
        assert classified[1].slide_type == SlideType.FINAL_OUTCOMES

    def test_outcomes_map_slide_detected(self, minimal_doview_pptx: str) -> None:
        slides = read_pptx(minimal_doview_pptx)
        classified = classify_slides(slides)
        assert classified[2].slide_type == SlideType.OUTCOMES_MAP

    def test_info_slide_skipped(self, minimal_doview_pptx: str) -> None:
        slides = read_pptx(minimal_doview_pptx)
        classified = classify_slides(slides)
        assert classified[3].slide_type == SlideType.SKIP


class TestOverviewShapeClassification:
    """Shapes on the overview slide are classified correctly."""

    def test_overview_tiles_identified(self, minimal_doview_pptx: str) -> None:
        slides = read_pptx(minimal_doview_pptx)
        classified = classify_slides(slides)
        overview = classified[0]
        tiles = [cs for cs in overview.shapes if cs.role == ShapeRole.OVERVIEW_TILE]
        # 3 coloured tiles + 1 Final Outcomes white tile = 4
        assert len(tiles) >= 4

    def test_footer_identified(self, minimal_doview_pptx: str) -> None:
        slides = read_pptx(minimal_doview_pptx)
        classified = classify_slides(slides)
        overview = classified[0]
        footers = [cs for cs in overview.shapes if cs.role == ShapeRole.FOOTER]
        assert len(footers) >= 1

    def test_grey_bar_identified(self, minimal_doview_pptx: str) -> None:
        slides = read_pptx(minimal_doview_pptx)
        classified = classify_slides(slides)
        overview = classified[0]
        bars = [cs for cs in overview.shapes if cs.role == ShapeRole.GREY_BAR]
        assert len(bars) >= 1


class TestFinalOutcomesShapeClassification:
    """Shapes on the final outcomes slide are classified correctly."""

    def test_final_outcomes_identified(self, minimal_doview_pptx: str) -> None:
        slides = read_pptx(minimal_doview_pptx)
        classified = classify_slides(slides)
        fo_slide = classified[1]
        outcomes = [cs for cs in fo_slide.shapes if cs.role == ShapeRole.FINAL_OUTCOME]
        assert len(outcomes) == 2  # "Outcome A achieved", "Outcome B achieved"

    def test_page_title_extracted(self, minimal_doview_pptx: str) -> None:
        slides = read_pptx(minimal_doview_pptx)
        classified = classify_slides(slides)
        fo_slide = classified[1]
        assert fo_slide.page_title == "Final Outcomes"

    def test_nav_button_identified(self, minimal_doview_pptx: str) -> None:
        slides = read_pptx(minimal_doview_pptx)
        classified = classify_slides(slides)
        fo_slide = classified[1]
        navs = [cs for cs in fo_slide.shapes if cs.role == ShapeRole.NAV_BUTTON]
        assert len(navs) == 1


class TestOutcomesMapShapeClassification:
    """Shapes on the outcomes map slide are classified correctly."""

    def test_outcome_boxes_identified(self, minimal_doview_pptx: str) -> None:
        slides = read_pptx(minimal_doview_pptx)
        classified = classify_slides(slides)
        om_slide = classified[2]
        boxes = [cs for cs in om_slide.shapes if cs.role == ShapeRole.OUTCOME_BOX]
        assert len(boxes) == 4  # 2 per column × 2 columns

    def test_causal_arrow_identified(self, minimal_doview_pptx: str) -> None:
        slides = read_pptx(minimal_doview_pptx)
        classified = classify_slides(slides)
        om_slide = classified[2]
        arrows = [cs for cs in om_slide.shapes if cs.role == ShapeRole.CAUSAL_ARROW]
        assert len(arrows) == 1

    def test_page_title_extracted(self, minimal_doview_pptx: str) -> None:
        slides = read_pptx(minimal_doview_pptx)
        classified = classify_slides(slides)
        om_slide = classified[2]
        assert om_slide.page_title == "Topic Alpha"


class TestColumnGrouping:
    """group_into_columns() clusters shapes by x-position."""

    def test_two_columns_detected(self, minimal_doview_pptx: str) -> None:
        slides = read_pptx(minimal_doview_pptx)
        classified = classify_slides(slides)
        om_slide = classified[2]
        boxes = [cs.shape for cs in om_slide.shapes if cs.role == ShapeRole.OUTCOME_BOX]
        columns = group_into_columns(boxes)
        assert len(columns) == 2

    def test_columns_ordered_left_to_right(self, minimal_doview_pptx: str) -> None:
        slides = read_pptx(minimal_doview_pptx)
        classified = classify_slides(slides)
        om_slide = classified[2]
        boxes = [cs.shape for cs in om_slide.shapes if cs.role == ShapeRole.OUTCOME_BOX]
        columns = group_into_columns(boxes)
        assert columns[0][0].left < columns[1][0].left

    def test_each_column_sorted_top_to_bottom(self, minimal_doview_pptx: str) -> None:
        slides = read_pptx(minimal_doview_pptx)
        classified = classify_slides(slides)
        om_slide = classified[2]
        boxes = [cs.shape for cs in om_slide.shapes if cs.role == ShapeRole.OUTCOME_BOX]
        columns = group_into_columns(boxes)
        for col in columns:
            tops = [s.top for s in col]
            assert tops == sorted(tops)

    def test_empty_input_returns_empty(self) -> None:
        assert group_into_columns([]) == []

    def test_single_shape_returns_one_column(self) -> None:
        shape = PptxShape(
            slide_index=0, shape_id=1, name="r", text="x",
            left=100, top=200, width=300, height=400,
            fill_color="FFFFBA", preset_geometry="rect",
            hyperlink_slide_index=None, is_textbox=False, is_picture=False,
        )
        cols = group_into_columns([shape])
        assert len(cols) == 1
        assert cols[0] == [shape]
