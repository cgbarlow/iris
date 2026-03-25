"""Slide and shape classification for DoView PPTX import."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field

from app.import_pptx.reader import PptxShape, PptxSlide


# ---------------------------------------------------------------------------
# Thresholds (EMU unless noted)
# ---------------------------------------------------------------------------

_MIN_HLINKS_FOR_OVERVIEW = 3
_GREY_BAR_MAX_HEIGHT = 25000
_COLUMN_GAP_TOLERANCE = 200000
_FULL_WIDTH_RATIO = 0.75  # shape width ≥ 75% of slide width
_SLIDE_WIDTH_EMU = 9144000  # default 10-inch slide = 9144000 EMU
_FOOTER_TOP_THRESHOLD = 6000000  # shapes with top > this are footers
_SEPARATOR_MAX_HEIGHT = 25000  # decorative separators

# Grey shades used for navigation / decorative elements
_NAV_GREY_FILLS = frozenset({"E6E6E6"})
_SEPARATOR_FILLS = frozenset({"969696", "808080", "999999", "BEBEBE"})
_ARROW_FILL = "C8C8C8"


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class SlideType(enum.Enum):
    OVERVIEW = "overview"
    FINAL_OUTCOMES = "final_outcomes"
    OUTCOMES_MAP = "outcomes_map"
    SKIP = "skip"


class ShapeRole(enum.Enum):
    OVERVIEW_TILE = "overview_tile"
    FINAL_OUTCOME = "final_outcome"
    OUTCOME_BOX = "outcome_box"
    CAUSAL_ARROW = "causal_arrow"
    PAGE_TITLE = "page_title"
    NAV_BUTTON = "nav_button"
    GREY_BAR = "grey_bar"
    FOOTER = "footer"
    SEPARATOR = "separator"
    SKIP = "skip"


# ---------------------------------------------------------------------------
# Classified shape
# ---------------------------------------------------------------------------


@dataclass
class ClassifiedShape:
    shape: PptxShape
    role: ShapeRole


@dataclass
class ClassifiedSlide:
    slide: PptxSlide
    slide_type: SlideType
    shapes: list[ClassifiedShape]
    page_title: str | None = None


# ---------------------------------------------------------------------------
# Compliance validation
# ---------------------------------------------------------------------------


def validate_doview_compliance(slides: list[PptxSlide]) -> list[str]:
    """Validate that a PPTX has DoView structure.

    Returns a list of violation messages.  Empty list means compliant.
    """
    violations: list[str] = []

    # 1. Overview slide exists
    overview_idx = _find_overview_slide_index(slides)
    if overview_idx is None:
        violations.append(
            "No overview slide found — DoView models require a navigation "
            "overview page with tiles linking to sub-pages "
            f"(need ≥{_MIN_HLINKS_FOR_OVERVIEW} shapes with inter-slide hyperlinks)"
        )

    # 2. Content slides exist (non-overview slides with coloured rects)
    has_content = False
    for i, slide in enumerate(slides):
        if i == overview_idx:
            continue
        colored_rects = [
            s for s in slide.shapes
            if s.fill_color
            and not s.is_textbox
            and s.fill_color.upper() not in _NAV_GREY_FILLS
            and s.fill_color.upper() != _ARROW_FILL
        ]
        if len(colored_rects) >= 2:
            has_content = True
            break
    if not has_content:
        violations.append(
            "No outcome content slides found — DoView models require "
            "outcomes map or final outcomes pages with coloured rectangles"
        )

    # 3. DoView structural elements (arrows OR final outcome white+grey pairs)
    has_arrows = any(
        any(
            s.preset_geometry and "arrow" in s.preset_geometry.lower()
            for s in slide.shapes
        )
        for slide in slides
    )
    has_final_outcomes = _has_white_grey_bar_pairs(slides)
    if not has_arrows and not has_final_outcomes:
        violations.append(
            "No DoView structural elements found — expected causal arrows "
            "between outcome columns or final outcome boxes with grey top rules"
        )

    # 4. Internal hyperlinks (overview tiles link within the deck)
    if overview_idx is not None:
        overview = slides[overview_idx]
        internal_links = [
            s for s in overview.shapes
            if s.hyperlink_slide_index is not None
        ]
        if not internal_links:
            violations.append(
                "Overview tiles have no inter-slide hyperlinks — "
                "DoView models use intra-model navigation"
            )

    return violations


# ---------------------------------------------------------------------------
# Slide classification
# ---------------------------------------------------------------------------


def classify_slides(
    slides: list[PptxSlide],
) -> list[ClassifiedSlide]:
    """Classify every slide and its shapes into DoView roles."""
    overview_idx = _find_overview_slide_index(slides)

    # Determine which slides are targeted by a "Final Outcomes" tile
    final_outcomes_targets: set[int] = set()
    if overview_idx is not None:
        for shape in slides[overview_idx].shapes:
            if (
                shape.hyperlink_slide_index is not None
                and shape.fill_color
                and shape.fill_color.upper() == "FFFFFF"
                and "final" in shape.text.lower()
            ):
                final_outcomes_targets.add(shape.hyperlink_slide_index)

    result: list[ClassifiedSlide] = []
    for slide in slides:
        if slide.index == overview_idx:
            classified = _classify_overview_slide(slide, overview_idx)
        elif slide.index in final_outcomes_targets:
            classified = _classify_final_outcomes_slide(slide, overview_idx)
        elif _is_outcomes_map(slide, overview_idx):
            classified = _classify_outcomes_map_slide(slide, overview_idx)
        else:
            classified = ClassifiedSlide(
                slide=slide,
                slide_type=SlideType.SKIP,
                shapes=[ClassifiedShape(s, ShapeRole.SKIP) for s in slide.shapes],
            )
        result.append(classified)
    return result


# ---------------------------------------------------------------------------
# Column grouping
# ---------------------------------------------------------------------------


def group_into_columns(
    shapes: list[PptxShape],
    tolerance: int = _COLUMN_GAP_TOLERANCE,
) -> list[list[PptxShape]]:
    """Group shapes into columns by left-edge x-position clustering.

    Returns columns ordered left-to-right, each sorted top-to-bottom.
    """
    if not shapes:
        return []

    sorted_shapes = sorted(shapes, key=lambda s: s.left)
    columns: list[list[PptxShape]] = [[sorted_shapes[0]]]

    for shape in sorted_shapes[1:]:
        last_col_left = columns[-1][0].left
        if abs(shape.left - last_col_left) <= tolerance:
            columns[-1].append(shape)
        else:
            columns.append([shape])

    # Sort each column top-to-bottom
    for col in columns:
        col.sort(key=lambda s: s.top)

    return columns


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _find_overview_slide_index(slides: list[PptxSlide]) -> int | None:
    """Find the overview slide (most hyperlinked shapes, ≥ threshold)."""
    best_idx: int | None = None
    best_count = 0
    for slide in slides:
        count = sum(
            1 for s in slide.shapes
            if s.hyperlink_slide_index is not None
        )
        if count >= _MIN_HLINKS_FOR_OVERVIEW and count > best_count:
            best_count = count
            best_idx = slide.index
    return best_idx


def _has_white_grey_bar_pairs(slides: list[PptxSlide]) -> bool:
    """Check if any slide has white rect + BEBEBE grey bar pairs."""
    for slide in slides:
        white_rects = [
            s for s in slide.shapes
            if s.fill_color and s.fill_color.upper() == "FFFFFF"
            and s.height > _GREY_BAR_MAX_HEIGHT
            and not s.is_textbox
        ]
        grey_bars = [
            s for s in slide.shapes
            if s.fill_color and s.fill_color.upper() == "BEBEBE"
            and s.height <= _GREY_BAR_MAX_HEIGHT
        ]
        if white_rects and grey_bars:
            return True
    return False


def _is_outcomes_map(slide: PptxSlide, overview_idx: int | None) -> bool:
    """Detect if a slide is an outcomes map (has arrow shapes)."""
    has_arrows = any(
        s.preset_geometry and "arrow" in s.preset_geometry.lower()
        for s in slide.shapes
    )
    has_coloured_rects = sum(
        1 for s in slide.shapes
        if s.fill_color
        and not s.is_textbox
        and s.fill_color.upper() not in _NAV_GREY_FILLS
        and s.fill_color.upper() != _ARROW_FILL
        and s.fill_color.upper() != "BEBEBE"
    ) >= 3
    return has_arrows and has_coloured_rects


def _is_full_width(shape: PptxShape) -> bool:
    """Check if a shape spans ≥ 75% of the default slide width."""
    return shape.width >= _SLIDE_WIDTH_EMU * _FULL_WIDTH_RATIO


def _is_separator(shape: PptxShape) -> bool:
    """Detect decorative full-width thin separator lines."""
    return (
        shape.height <= _SEPARATOR_MAX_HEIGHT
        and _is_full_width(shape)
        and shape.fill_color is not None
        and shape.fill_color.upper() in _SEPARATOR_FILLS
        and not shape.text
    )


def _is_footer(shape: PptxShape) -> bool:
    """Detect footer text boxes at the bottom of the slide."""
    return shape.is_textbox and shape.top >= _FOOTER_TOP_THRESHOLD


def _is_nav_button(shape: PptxShape, overview_idx: int | None) -> bool:
    """Detect 'Back to Overview' navigation buttons."""
    return (
        shape.hyperlink_slide_index == overview_idx
        and shape.fill_color is not None
        and shape.fill_color.upper() in _NAV_GREY_FILLS
    )


def _is_grey_bar(shape: PptxShape) -> bool:
    """Detect thin BEBEBE grey bars (final outcome decorators)."""
    return (
        shape.fill_color is not None
        and shape.fill_color.upper() == "BEBEBE"
        and shape.height <= _GREY_BAR_MAX_HEIGHT
    )


# ---------------------------------------------------------------------------
# Per-slide classifiers
# ---------------------------------------------------------------------------


def _classify_overview_slide(
    slide: PptxSlide, overview_idx: int | None,
) -> ClassifiedSlide:
    classified: list[ClassifiedShape] = []
    for shape in slide.shapes:
        if _is_footer(shape):
            classified.append(ClassifiedShape(shape, ShapeRole.FOOTER))
        elif _is_separator(shape):
            classified.append(ClassifiedShape(shape, ShapeRole.SEPARATOR))
        elif _is_grey_bar(shape):
            classified.append(ClassifiedShape(shape, ShapeRole.GREY_BAR))
        elif shape.hyperlink_slide_index is not None and shape.fill_color:
            classified.append(ClassifiedShape(shape, ShapeRole.OVERVIEW_TILE))
        elif shape.is_textbox and not shape.fill_color:
            classified.append(ClassifiedShape(shape, ShapeRole.SKIP))
        else:
            classified.append(ClassifiedShape(shape, ShapeRole.SKIP))
    return ClassifiedSlide(
        slide=slide, slide_type=SlideType.OVERVIEW, shapes=classified,
    )


def _classify_final_outcomes_slide(
    slide: PptxSlide, overview_idx: int | None,
) -> ClassifiedSlide:
    classified: list[ClassifiedShape] = []
    page_title: str | None = None

    for shape in slide.shapes:
        if _is_footer(shape):
            classified.append(ClassifiedShape(shape, ShapeRole.FOOTER))
        elif _is_nav_button(shape, overview_idx):
            classified.append(ClassifiedShape(shape, ShapeRole.NAV_BUTTON))
        elif _is_separator(shape):
            classified.append(ClassifiedShape(shape, ShapeRole.SEPARATOR))
        elif _is_grey_bar(shape):
            classified.append(ClassifiedShape(shape, ShapeRole.GREY_BAR))
        elif (
            shape.fill_color
            and shape.fill_color.upper() == "FFFFFF"
            and not shape.is_textbox
            and shape.height > _GREY_BAR_MAX_HEIGHT
        ):
            # White rectangle — could be title or final outcome
            if page_title is None and _is_full_width(shape) and shape.text:
                page_title = shape.text
                classified.append(ClassifiedShape(shape, ShapeRole.PAGE_TITLE))
            else:
                classified.append(ClassifiedShape(shape, ShapeRole.FINAL_OUTCOME))
        else:
            classified.append(ClassifiedShape(shape, ShapeRole.SKIP))

    return ClassifiedSlide(
        slide=slide,
        slide_type=SlideType.FINAL_OUTCOMES,
        shapes=classified,
        page_title=page_title,
    )


def _classify_outcomes_map_slide(
    slide: PptxSlide, overview_idx: int | None,
) -> ClassifiedSlide:
    classified: list[ClassifiedShape] = []
    page_title: str | None = None

    # Identify the page title: first full-width coloured rect
    for shape in slide.shapes:
        if (
            page_title is None
            and not shape.is_textbox
            and shape.fill_color
            and shape.fill_color.upper() not in _NAV_GREY_FILLS
            and shape.fill_color.upper() != _ARROW_FILL
            and shape.fill_color.upper() != "BEBEBE"
            and _is_full_width(shape)
            and shape.text
        ):
            page_title = shape.text
            break

    for shape in slide.shapes:
        if _is_footer(shape):
            classified.append(ClassifiedShape(shape, ShapeRole.FOOTER))
        elif _is_nav_button(shape, overview_idx):
            classified.append(ClassifiedShape(shape, ShapeRole.NAV_BUTTON))
        elif _is_separator(shape):
            classified.append(ClassifiedShape(shape, ShapeRole.SEPARATOR))
        elif shape.preset_geometry and "arrow" in shape.preset_geometry.lower():
            classified.append(ClassifiedShape(shape, ShapeRole.CAUSAL_ARROW))
        elif (
            not shape.is_textbox
            and shape.fill_color
            and shape.fill_color.upper() not in _NAV_GREY_FILLS
            and shape.fill_color.upper() != _ARROW_FILL
            and shape.fill_color.upper() != "BEBEBE"
            and _is_full_width(shape)
            and shape.text == page_title
        ):
            classified.append(ClassifiedShape(shape, ShapeRole.PAGE_TITLE))
        elif (
            not shape.is_textbox
            and shape.fill_color
            and shape.fill_color.upper() not in _NAV_GREY_FILLS
            and shape.fill_color.upper() != _ARROW_FILL
            and shape.fill_color.upper() != "BEBEBE"
            and not _is_full_width(shape)
            and shape.height > _GREY_BAR_MAX_HEIGHT
        ):
            classified.append(ClassifiedShape(shape, ShapeRole.OUTCOME_BOX))
        else:
            classified.append(ClassifiedShape(shape, ShapeRole.SKIP))

    return ClassifiedSlide(
        slide=slide,
        slide_type=SlideType.OUTCOMES_MAP,
        shapes=classified,
        page_title=page_title,
    )
