"""Tests for AI Pydantic schemas (ADR-093)."""

import pytest
from pydantic import ValidationError

from app.ai.models import (
    ModelParameters,
    ProviderCreate,
    ProviderTestResult,
    QARequest,
    QAResponse,
)


class TestModelParameters:
    def test_defaults(self):
        p = ModelParameters()
        assert p.temperature is None
        assert p.max_tokens is None
        assert p.top_p is None

    def test_valid_values(self):
        p = ModelParameters(temperature=0.7, max_tokens=4096, top_p=0.9)
        assert p.temperature == 0.7
        assert p.max_tokens == 4096

    def test_temperature_out_of_range(self):
        with pytest.raises(ValidationError):
            ModelParameters(temperature=2.5)

    def test_temperature_negative(self):
        with pytest.raises(ValidationError):
            ModelParameters(temperature=-0.1)

    def test_max_tokens_zero(self):
        with pytest.raises(ValidationError):
            ModelParameters(max_tokens=0)

    def test_top_p_range(self):
        with pytest.raises(ValidationError):
            ModelParameters(top_p=1.1)

    # --- Advanced parameters (ADR-114) ---

    def test_top_k_valid(self):
        p = ModelParameters(top_k=40)
        assert p.top_k == 40

    def test_top_k_zero_invalid(self):
        with pytest.raises(ValidationError):
            ModelParameters(top_k=0)

    def test_min_p_valid(self):
        p = ModelParameters(min_p=0.1)
        assert p.min_p == 0.1

    def test_min_p_out_of_range(self):
        with pytest.raises(ValidationError):
            ModelParameters(min_p=1.5)

    def test_frequency_penalty_valid(self):
        p = ModelParameters(frequency_penalty=-0.5)
        assert p.frequency_penalty == -0.5

    def test_frequency_penalty_out_of_range(self):
        with pytest.raises(ValidationError):
            ModelParameters(frequency_penalty=2.5)

    def test_presence_penalty_valid(self):
        p = ModelParameters(presence_penalty=1.0)
        assert p.presence_penalty == 1.0

    def test_presence_penalty_out_of_range(self):
        with pytest.raises(ValidationError):
            ModelParameters(presence_penalty=-2.5)

    def test_stop_sequences(self):
        p = ModelParameters(stop=["END", "\n"])
        assert p.stop == ["END", "\n"]

    def test_stop_sequences_empty(self):
        p = ModelParameters(stop=[])
        assert p.stop == []

    def test_all_advanced_parameters(self):
        p = ModelParameters(
            temperature=0.7, max_tokens=4096, top_p=0.9,
            top_k=40, min_p=0.05, frequency_penalty=0.5,
            presence_penalty=-0.5, stop=["END"],
        )
        dumped = p.model_dump(exclude_none=True)
        assert dumped["top_k"] == 40
        assert dumped["min_p"] == 0.05
        assert dumped["frequency_penalty"] == 0.5
        assert dumped["presence_penalty"] == -0.5
        assert dumped["stop"] == ["END"]


class TestProviderCreate:
    def test_valid_minimal(self):
        p = ProviderCreate(name="test", provider_type="openai", model="gpt-4o")
        assert p.name == "test"
        assert p.provider_type == "openai"
        assert p.timeout_ms == 30000
        assert p.retries == 3
        assert p.is_active is True

    def test_invalid_provider_type(self):
        with pytest.raises(ValidationError):
            ProviderCreate(name="x", provider_type="invalid", model="m")

    def test_name_too_long(self):
        with pytest.raises(ValidationError):
            ProviderCreate(name="x" * 101, provider_type="openai", model="m")

    def test_model_required(self):
        with pytest.raises(ValidationError):
            ProviderCreate(name="x", provider_type="openai", model="")

    def test_timeout_range(self):
        with pytest.raises(ValidationError):
            ProviderCreate(name="x", provider_type="openai", model="m", timeout_ms=500)

    def test_all_provider_types(self):
        for pt in ["openai", "anthropic", "ollama", "lmstudio", "openrouter", "custom"]:
            p = ProviderCreate(name="x", provider_type=pt, model="m")
            assert p.provider_type == pt


class TestQARequest:
    def test_valid(self):
        r = QARequest(question="What is the architecture?")
        assert r.question == "What is the architecture?"
        assert r.provider_id is None

    def test_empty_question(self):
        with pytest.raises(ValidationError):
            QARequest(question="")

    def test_question_too_long(self):
        with pytest.raises(ValidationError):
            QARequest(question="x" * 4001)

    def test_max_question_length(self):
        r = QARequest(question="x" * 4000)
        assert len(r.question) == 4000


class TestProviderTestResult:
    def test_ok(self):
        r = ProviderTestResult(ok=True, latency_ms=250)
        assert r.ok is True
        assert r.latency_ms == 250
        assert r.error is None

    def test_error(self):
        r = ProviderTestResult(ok=False, error="Connection refused")
        assert r.ok is False
        assert r.error == "Connection refused"
