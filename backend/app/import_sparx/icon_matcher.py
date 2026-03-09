"""Semantic icon matcher for EA import (ADR-091-B).

Matches element names and stereotypes to Lucide icons using keyword
similarity against a tag index. Ensures set-wide consistency: the same
element name always resolves to the same icon within an import batch.

Matching strategy:
- Tokenize input into weighted tokens (head-noun weighting)
- Expand tokens with domain-specific synonyms
- Score each icon against weighted tokens
- Head noun (last significant word) gets 3× weight because in English
  compound nouns the last word determines what something IS:
  "Application Owner" is a type of Owner, not a type of Application.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import NamedTuple, TypedDict


class IconRef(TypedDict):
    set: str
    name: str


class IconTagEntry(TypedDict):
    name: str
    tags: list[str]
    category: str


class _WeightedToken(NamedTuple):
    """A token with an importance weight for scoring."""
    text: str
    weight: float


# Load icon tags from the shared JSON file
_ICON_TAGS_PATH = (
    Path(__file__).resolve().parents[3]
    / "frontend"
    / "src"
    / "lib"
    / "icons"
    / "iconTags.json"
)

DEFAULT_ICON = IconRef(set="lucide", name="blocks")

# Domain-specific synonyms for better matching.
# These expand a domain term into icon-library-friendly keywords.
# Synonyms inherit the weight of the token they expand from.
_SYNONYMS: dict[str, list[str]] = {
    "stakeholder": ["person", "actor", "human"],
    "organisation": ["organization", "company", "enterprise"],
    "application": ["app", "software"],
    "service": ["server", "cloud", "api", "cog"],
    "it": ["technology", "computer"],
    "process": ["workflow", "flow", "automation"],
    "function": ["service", "capability", "operation"],
    "role": ["person", "actor", "responsibility"],
    "actor": ["person", "stakeholder", "human"],
    "gateway": ["shield", "lock", "security", "firewall"],
    "security": ["shield", "lock", "security"],
    "driver": ["power", "energy", "motivation"],
    "goal": ["target", "objective", "aim"],
    "flow": ["workflow", "process", "automation"],
    "landscape": ["layout", "grid", "overview", "dashboard"],
    "inventory": ["list", "catalog", "registry"],
    "owner": ["person", "user", "responsible"],
    "domain": ["boxes", "group", "collection", "cluster"],
    "principle": ["direction", "guidance", "compass"],
    "requirement": ["checklist", "requirement", "compliance"],
    "constraint": ["warning", "caution", "risk"],
    "capability": ["component", "building block", "ability"],
    "deliverable": ["package", "parcel", "box"],
    "work_package": ["package", "parcel", "box"],
    "plateau": ["milestone", "checkpoint", "marker"],
    "gap": ["error", "failed", "gap"],
    "assessment": ["question", "help", "assessment"],
    "outcome": ["target", "achievement", "goal"],
    "project": ["folder", "project", "plan"],
    "unknown": ["question", "help", "unknown"],
}

# Noise words that carry no semantic value for icon matching
_NOISE_WORDS = {"the", "of", "and", "for", "in", "on", "to", "an", "is", "it", "by"}


def _stem(word: str) -> str:
    """Minimal English stemmer: strip common plural/verb suffixes."""
    if len(word) <= 3:
        return word
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"  # capabilities -> capability
    if word.endswith("ses") or word.endswith("zes") or word.endswith("xes"):
        return word[:-2]  # processes -> process
    if word.endswith("s") and not word.endswith("ss"):
        return word[:-1]  # domains -> domain
    return word


def _tokenize(text: str) -> list[str]:
    """Split text into lowercase tokens, removing noise words and stemming plurals."""
    if not text:
        return []
    # Remove ArchiMate prefixes like "ArchiMate_"
    text = re.sub(r"archimate[_\s]*", "", text, flags=re.IGNORECASE)
    # Split on whitespace, underscores, hyphens, camelCase boundaries
    tokens = re.split(r"[\s_\-/]+", text)
    # Further split camelCase
    expanded: list[str] = []
    for token in tokens:
        parts = re.sub(r"([a-z])([A-Z])", r"\1 \2", token).split()
        expanded.extend(parts)
    return [_stem(t.lower()) for t in expanded if len(t) > 1 and t.lower() not in _NOISE_WORDS]


def _build_weighted_tokens(
    name: str,
    stereotype: str | None = None,
    note: str | None = None,
) -> list[_WeightedToken]:
    """Build weighted token list with head-noun emphasis.

    In English compound nouns, the last word is the "head" — it determines
    what the thing IS. "Application Owner" is a type of Owner.
    "Security Gateway" is a type of Gateway. We give the head noun 3× weight.

    Token sources and their base weights:
    - Name tokens: 1.0 (head noun: 3.0)
    - Stereotype tokens: 0.5 (supplementary signal)
    - Note tokens: 0.3 (weak signal, large text)
    """
    weighted: list[_WeightedToken] = []

    # Name tokens with head-noun weighting
    name_tokens = _tokenize(name)
    if name_tokens:
        for i, token in enumerate(name_tokens):
            # Last token = head noun gets 3× weight
            weight = 3.0 if i == len(name_tokens) - 1 else 1.0
            weighted.append(_WeightedToken(token, weight))

    # Stereotype tokens (supplementary)
    if stereotype:
        for token in _tokenize(stereotype):
            weighted.append(_WeightedToken(token, 0.5))

    # Note tokens (weak signal)
    if note:
        for token in _tokenize(note[:100]):
            weighted.append(_WeightedToken(token, 0.3))

    # Expand with synonyms — synonyms inherit the weight of their source
    expanded: list[_WeightedToken] = list(weighted)
    for wt in weighted:
        if wt.text in _SYNONYMS:
            for syn in _SYNONYMS[wt.text]:
                expanded.append(_WeightedToken(syn, wt.weight))

    return expanded


class SemanticIconMatcher:
    """Matches element names/stereotypes to icons via keyword similarity."""

    def __init__(self, icon_set: str = "lucide"):
        self.icon_set = icon_set
        self._icon_tags: list[IconTagEntry] = self._load_tags()
        self._cache: dict[str, IconRef] = {}

    def _load_tags(self) -> list[IconTagEntry]:
        """Load icon tags from the shared JSON asset."""
        if _ICON_TAGS_PATH.exists():
            with open(_ICON_TAGS_PATH) as f:
                return json.load(f)
        return []

    def match(
        self,
        name: str,
        stereotype: str | None = None,
        note: str | None = None,
    ) -> IconRef:
        """Find best icon for an element based on its metadata."""
        # Build cache key from normalized name
        cache_key = name.strip().lower()
        if cache_key in self._cache:
            return self._cache[cache_key]

        weighted_tokens = _build_weighted_tokens(name, stereotype, note)

        if not weighted_tokens:
            self._cache[cache_key] = DEFAULT_ICON
            return DEFAULT_ICON

        # Score each icon against the weighted tokens
        best_icon = DEFAULT_ICON
        best_score = 0.0

        for entry in self._icon_tags:
            score = self._score(weighted_tokens, entry)
            if score > best_score:
                best_score = score
                best_icon = IconRef(set=self.icon_set, name=entry["name"])

        self._cache[cache_key] = best_icon
        return best_icon

    def _score(self, tokens: list[_WeightedToken], entry: IconTagEntry) -> float:
        """Score an icon entry against weighted search tokens."""
        score = 0.0
        entry_tags = entry["tags"]
        icon_name = entry["name"]
        # Stem tags and icon name segments for plural-safe matching
        stemmed_tags = {_stem(t) for t in entry_tags}
        tag_words = set()
        for tag in entry_tags:
            for word in tag.split():
                tag_words.add(_stem(word.lower()))
        name_segments = {_stem(s) for s in icon_name.split("-")}

        for token_text, weight in tokens:
            # Exact tag match (highest value) — stemmed
            if token_text in stemmed_tags:
                score += 5.0 * weight
            # Exact word match within a multi-word tag — stemmed
            elif token_text in tag_words:
                score += 3.0 * weight
            # Icon name exact segment match (e.g. "user" in "user-check") — stemmed
            elif token_text in name_segments:
                score += 4.0 * weight
            # Partial match: only for tokens >= 4 chars to avoid noise
            elif len(token_text) >= 4:
                for tag in entry_tags:
                    if token_text in tag:
                        score += 0.5 * weight
                        break

        return score

    def reset(self) -> None:
        """Clear the consistency cache (e.g., between import batches)."""
        self._cache.clear()
