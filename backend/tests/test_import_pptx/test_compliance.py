"""Tests for DoView compliance validation."""

from __future__ import annotations

from app.import_pptx.classifier import validate_doview_compliance
from app.import_pptx.reader import read_pptx


class TestDoviewComplianceValid:
    """Valid DoView PPTX passes compliance."""

    def test_valid_doview_has_no_violations(self, minimal_doview_pptx: str) -> None:
        slides = read_pptx(minimal_doview_pptx)
        violations = validate_doview_compliance(slides)
        assert violations == []


class TestDoviewComplianceRejectsInvalid:
    """Non-DoView PPTX files are rejected with clear messages."""

    def test_no_overview_slide(self, non_doview_pptx: str) -> None:
        slides = read_pptx(non_doview_pptx)
        violations = validate_doview_compliance(slides)
        assert any("overview" in v.lower() for v in violations)

    def test_non_doview_has_violations(self, non_doview_pptx: str) -> None:
        slides = read_pptx(non_doview_pptx)
        violations = validate_doview_compliance(slides)
        assert len(violations) > 0

    def test_violation_messages_are_descriptive(self, non_doview_pptx: str) -> None:
        slides = read_pptx(non_doview_pptx)
        violations = validate_doview_compliance(slides)
        for v in violations:
            assert len(v) > 20  # not cryptic


class TestDoviewComplianceRealFiles:
    """All 4 sample PPTX files pass compliance."""

    _SAMPLE_FILES = [
        "/workspaces/workspace-basic/iris/temp/Rebuilding Legacy Code In Government DoView 025-09-21 Dr Paul Duignan.pptx",
        "/workspaces/workspace-basic/iris/temp/Amazon DoView Strategy Diagram  Dr Paul Duignan DoViewPlanning.Org a060.pptx",
        "/workspaces/workspace-basic/iris/temp/EU Commission Priorities 2024-2029 DoView Strategy Diagram Dr Paul Duignan DoViewPlanning.Org a040.pptx",
        "/workspaces/workspace-basic/iris/temp/NZ Inland Revenue Department (IRD) DoView Strategy Diagram Dr Paul Duignan DoViewPlanning.Org  a018.pptx",
    ]

    def test_all_real_files_pass_compliance(self) -> None:
        import os

        for path in self._SAMPLE_FILES:
            if not os.path.exists(path):
                continue  # skip if not available in CI
            slides = read_pptx(path)
            violations = validate_doview_compliance(slides)
            assert violations == [], f"{os.path.basename(path)}: {violations}"
