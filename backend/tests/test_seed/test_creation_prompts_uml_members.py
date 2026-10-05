"""The UML creation prompts name the keys the canvas reads (ADR-260,
issue #315).

The prompts used to tell models to write class members under
``data.compartments``. The canvas reads ``data.attributes`` and
``data.operations``, so every class made by following the prompt showed a
header and nothing else.
"""

from __future__ import annotations

import pytest

from app.seed.creation_prompts import UML_CLASS_PROMPT, UML_NOTATION_PROMPT


@pytest.mark.parametrize(
    "prompt",
    [UML_NOTATION_PROMPT, UML_CLASS_PROMPT],
    ids=["uml-notation", "uml-class"],
)
class TestUmlMemberKeys:
    def test_names_the_keys_the_canvas_reads(self, prompt: str) -> None:
        assert "data.attributes" in prompt
        assert "data.operations" in prompt
        assert '"attributes": [' in prompt
        assert '"operations": [' in prompt

    def test_no_longer_mentions_compartments_key(self, prompt: str) -> None:
        assert "data.compartments" not in prompt
        assert '"compartments"' not in prompt
