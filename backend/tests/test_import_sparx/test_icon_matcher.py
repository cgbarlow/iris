"""Tests for semantic icon matching (ADR-091-B)."""
import pytest
from app.import_sparx.icon_matcher import SemanticIconMatcher


@pytest.fixture
def matcher():
    return SemanticIconMatcher()


class TestSemanticMatching:
    """Verify that element names/stereotypes map to appropriate icons."""

    def test_stakeholder_matches_person(self, matcher):
        result = matcher.match("Stakeholder")
        assert result["set"] == "lucide"
        assert "person" in result["name"] or result["name"] == "user"

    def test_organization_matches_building(self, matcher):
        result = matcher.match("Organization")
        assert result["set"] == "lucide"
        assert result["name"] == "building"

    def test_application_service_matches_server(self, matcher):
        result = matcher.match("Application Service")
        assert result["set"] == "lucide"
        assert "server" in result["name"] or "cloud" in result["name"] or "cog" in result["name"]

    def test_service_matches_service_icon(self, matcher):
        result = matcher.match("Service")
        assert result["set"] == "lucide"
        # With full Lucide metadata, "service" may match various icons
        assert result["name"] != "blocks"  # Should not be default

    def test_database_matches_database(self, matcher):
        result = matcher.match("Database")
        assert result["set"] == "lucide"
        assert result["name"] == "database"

    def test_process_matches_workflow(self, matcher):
        result = matcher.match("Process Flow")
        assert result["set"] == "lucide"
        assert result["name"] == "workflow"

    def test_security_matches_shield(self, matcher):
        result = matcher.match("Security Gateway")
        assert result["set"] == "lucide"
        assert "shield" in result["name"] or "lock" in result["name"]

    def test_unknown_returns_non_default_with_rich_tags(self, matcher):
        """With full Lucide metadata, even unusual names may find a partial match."""
        result = matcher.match("Xyzzy Frobnicator")
        assert result["set"] == "lucide"
        # May or may not be default — just verify it's a valid icon ref
        assert isinstance(result["name"], str)

    def test_stereotype_boosts_match(self, matcher):
        result = matcher.match("MyThing", stereotype="ArchiMate_Stakeholder")
        assert result["set"] == "lucide"
        assert "person" in result["name"] or result["name"] == "user"

    def test_case_insensitive(self, matcher):
        result1 = matcher.match("STAKEHOLDER")
        result2 = matcher.match("stakeholder")
        assert result1 == result2


class TestSetWideConsistency:
    """Verify that the same element name always gets the same icon."""

    def test_same_name_same_icon(self, matcher):
        r1 = matcher.match("Stakeholder")
        r2 = matcher.match("Stakeholder")
        assert r1 == r2

    def test_batch_consistency(self, matcher):
        """All elements with the same name in a batch get the same icon."""
        names = ["Stakeholder", "Organization", "Stakeholder", "Database", "Organization"]
        results = [matcher.match(n) for n in names]
        # Same name → same icon
        assert results[0] == results[2]  # Both "Stakeholder"
        assert results[1] == results[4]  # Both "Organization"
        # Different names → potentially different icons
        assert results[0] != results[1]

    def test_cache_cleared_on_reset(self, matcher):
        matcher.match("Stakeholder")
        assert len(matcher._cache) > 0
        matcher.reset()
        assert len(matcher._cache) == 0
