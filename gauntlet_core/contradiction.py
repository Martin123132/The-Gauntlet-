from __future__ import annotations

"""Small symbolic contradiction checks adapted from the original MBT tools."""

from dataclasses import dataclass
from enum import Enum
import re
from typing import Callable


class ContradictionType(str, Enum):
    DIRECT_NEGATION = "direct_negation"
    PROPERTY_MISMATCH = "property_mismatch"
    DEFINITIONAL_VIOLATION = "definitional_violation"
    UNIVERSAL_COUNTEREXAMPLE = "universal_counterexample"
    TEMPORAL_CONFLICT = "temporal_conflict"


@dataclass(frozen=True)
class ClaimPair:
    id: str
    premise: str
    query: str


@dataclass(frozen=True)
class Contradiction:
    claim_id: str
    type: ContradictionType
    note: str
    repair_suggestion: str
    score: float


Rule = Callable[[ClaimPair], Contradiction | None]


class ContradictionEngine:
    """Rule-based contradiction detector for sentence pairs."""

    def __init__(self, rules: list[Rule] | None = None) -> None:
        self.rules = rules or [
            self._direct_negation_rule,
            self._temporal_rule,
            self._property_mismatch_rule,
            self._definitional_rule,
            self._universal_rule,
        ]

    def detect(self, claim: ClaimPair) -> Contradiction | None:
        for rule in self.rules:
            result = rule(claim)
            if result:
                return result
        return None

    def _direct_negation_rule(self, claim: ClaimPair) -> Contradiction | None:
        premise = normalize_text(claim.premise)
        query = normalize_text(claim.query)
        premise_key = strip_negation(premise)
        query_key = strip_negation(query)
        if premise_key and premise_key == query_key and has_negation(premise) != has_negation(query):
            return Contradiction(
                claim.id,
                ContradictionType.DIRECT_NEGATION,
                "One sentence affirms what the other denies.",
                "Clarify scope, context, or evidence for the negation.",
                0.9,
            )
        return None

    def _property_mismatch_rule(self, claim: ClaimPair) -> Contradiction | None:
        premise = claim.premise.lower()
        query = claim.query.lower()
        premise_number = extract_number(premise)
        query_number = extract_number(query)
        shared_terms = content_words(premise) & content_words(query)
        if premise_number is not None and query_number is not None:
            if premise_number != query_number and len(shared_terms) >= 3:
                return Contradiction(
                    claim.id,
                    ContradictionType.PROPERTY_MISMATCH,
                    f"Shared subject language uses conflicting numeric values: {premise_number:g} vs {query_number:g}.",
                    "Normalize units, define measurement context, or explain why both values can coexist.",
                    0.75,
                )
        opposite_pairs = [
            ("increases", "decreases"),
            ("increase", "decrease"),
            ("positive", "negative"),
            ("finite", "infinite"),
            ("continuous", "discrete"),
            ("conserved", "violated"),
            ("expands", "contracts"),
        ]
        for left, right in opposite_pairs:
            if ((left in premise and right in query) or (right in premise and left in query)) and len(shared_terms) >= 2:
                return Contradiction(
                    claim.id,
                    ContradictionType.PROPERTY_MISMATCH,
                    f"Potential property conflict between '{left}' and '{right}'.",
                    "Separate comparison cases from the paper's own claim, or define the condition where each property applies.",
                    0.68,
                )
        return None

    def _definitional_rule(self, claim: ClaimPair) -> Contradiction | None:
        joined = f"{claim.premise} {claim.query}".lower()
        patterns = [
            ("triangle", "three sides"),
            ("prime number", "only divisible"),
            ("conservation", "created or destroyed"),
        ]
        if has_negation(claim.query.lower()):
            for subject, property_text in patterns:
                if subject in joined and property_text in joined:
                    return Contradiction(
                        claim.id,
                        ContradictionType.DEFINITIONAL_VIOLATION,
                        f"The query appears to deny a definitional property of {subject}.",
                        "Either revise the definition or show why this case is an explicit exception.",
                        0.82,
                    )
        return None

    def _universal_rule(self, claim: ClaimPair) -> Contradiction | None:
        premise = claim.premise.lower()
        query = claim.query.lower()
        if re.search(r"\b(all|always|every|never)\b", premise) and re.search(
            r"\b(exception|counterexample|except|however|but|not all)\b", query
        ):
            return Contradiction(
                claim.id,
                ContradictionType.UNIVERSAL_COUNTEREXAMPLE,
                "A universal claim is challenged by exception language.",
                "Weaken the quantifier, name exceptions, or justify why the exception is outside scope.",
                0.86,
            )
        return None

    def _temporal_rule(self, claim: ClaimPair) -> Contradiction | None:
        premise = claim.premise.lower()
        query = claim.query.lower()
        years = set(re.findall(r"\b(?:18|19|20)\d{2}\b", f"{premise} {query}"))
        if len(years) >= 2 and re.search(r"\b(always|never|unchanged|constant)\b", premise):
            return Contradiction(
                claim.id,
                ContradictionType.TEMPORAL_CONFLICT,
                "A time-bound statement conflicts with absolute time language.",
                "Replace absolute wording with a date range and explain what changed.",
                0.86,
            )
        return None


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "because",
    "by",
    "for",
    "from",
    "has",
    "have",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "with",
}


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", "", text.lower())).strip()


def has_negation(text: str) -> bool:
    return bool(re.search(r"\b(no|not|never|none|cannot|can't|does not|do not|isn't|aren't)\b", text.lower()))


def strip_negation(text: str) -> str:
    return re.sub(r"\b(no|not|never|none|cannot|cant|does not|do not|isnt|arent)\b", "", text).strip()


def extract_number(text: str) -> float | None:
    match = re.search(r"(-?\d+(?:\.\d+)?)", text)
    return float(match.group(1)) if match else None


def content_words(text: str) -> set[str]:
    return {word for word in re.findall(r"[a-zA-Z][a-zA-Z-]{2,}", text.lower()) if word not in STOPWORDS}
