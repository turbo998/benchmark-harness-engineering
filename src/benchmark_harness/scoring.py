"""Frozen deterministic assertions; machine/human rubric review is separate."""

from __future__ import annotations

import json
import re
from typing import Any

from benchmark_harness.contracts import Assertion, AssertionOutcome, Case, Score, canonical


def _text(value: Any, normalization: str) -> str:
    text = (
        value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True)
    )
    if normalization == "strip":
        return text.strip()
    if normalization == "casefold":
        return text.strip().casefold()
    return text


def assertion_passes(assertion: Assertion, response: Any, normalization: str) -> bool:
    try:
        if assertion.kind in {"json_equal", "json_keys"}:
            parsed = json.loads(response) if isinstance(response, str) else response
            if assertion.kind == "json_equal":
                return canonical(parsed) == canonical(assertion.expected)
            return isinstance(parsed, dict) and sorted(parsed) == sorted(assertion.expected)
        actual = _text(response, normalization)
        expected = _text(assertion.expected, normalization)
        if assertion.kind == "exact":
            return actual == expected
        if assertion.kind == "contains":
            return expected in actual
        return re.search(assertion.expected, actual) is not None
    except (ValueError, TypeError):
        return False


def make_score(
    outcomes: tuple[AssertionOutcome, ...],
    *,
    profile: str = "deterministic-v1",
    rubric_required: bool = False,
    functional_override: float | None = None,
    error: str | None = None,
) -> Score:
    def weighted(category: str) -> float | None:
        rows = [a for a in outcomes if a.category == category]
        denominator = sum(a.weight for a in rows)
        return sum(a.weight * a.passed for a in rows) / denominator if rows else None

    functional = weighted("functional") if functional_override is None else functional_override
    compliance = weighted("compliance")
    pending = rubric_required or profile == "author-style-70-15-15-v1"
    return Score.model_validate(
        {
            "functional": functional,
            "compliance": compliance,
            "rubric": None,
            "composite": functional if profile == "deterministic-v1" else None,
            "profile": profile,
            "review": "pending" if pending else "not_required",
            "missing_reason": error
            or ("Independent rubric review not performed" if pending else None),
            "assertions": outcomes,
        }
    )


def score_api(case: Case, response: Any, *, profile: str = "deterministic-v1") -> Score:
    if case.track != "api":
        raise ValueError("Coding scores require an independently executed verifier")
    outcomes = tuple(
        AssertionOutcome(
            name=a.name,
            category=a.category,
            weight=a.weight,
            passed=assertion_passes(a, response, case.normalization),
        )
        for a in case.assertions
    )
    return make_score(outcomes, profile=profile, rubric_required=case.rubric_version is not None)


def unattempted_score(case: Case, *, profile: str, reason: str) -> Score:
    outcomes = tuple(
        AssertionOutcome(name=a.name, category=a.category, weight=a.weight, passed=False)
        for a in case.assertions
    )
    if case.track == "coding":
        outcomes = (
            AssertionOutcome(
                name="independent-verifier",
                category="functional",
                weight=1.0,
                passed=False,
            ),
        )
    return make_score(outcomes, profile=profile, functional_override=0.0, error=reason)
