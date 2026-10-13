import pytest

from benchmark_harness.contracts import Assertion
from benchmark_harness.samples import template_cases
from benchmark_harness.scoring import assertion_passes, score_api


def test_assertion_normalization_shape_and_weighting() -> None:
    assert assertion_passes(
        Assertion(name="text", kind="exact", expected="YES", weight=1), "yes\n", "casefold"
    )
    assert assertion_passes(
        Assertion(name="regex", kind="regex", expected=r"^\d+$", weight=1), "42", "strip"
    )
    assert not assertion_passes(
        Assertion(name="json", kind="json_equal", expected={"n": 1}, weight=1), "{not json", "strip"
    )
    assert not assertion_passes(
        Assertion(name="shape", kind="json_keys", expected=["n"], weight=1),
        {"n": 1, "extra": 2},
        "none",
    )
    case = template_cases()[2]
    score = score_api(case, {"city": "Oslo", "count": "3"})
    assert score.functional == 0 and score.compliance == 1
    assert score.composite == 0
    with pytest.raises(ValueError):
        score_api(next(c for c in template_cases() if c.track == "coding"), "not verifier evidence")


def test_optional_author_profile_is_named_and_pending_not_zero() -> None:
    case = template_cases()[0]
    score = score_api(case, case.accepted[0], profile="author-style-70-15-15-v1")
    assert score.functional == 1 and score.compliance == 1
    assert score.rubric is None and score.composite is None and score.review == "pending"


def test_json_oracle_is_type_sensitive() -> None:
    assertion = Assertion(name="integer", kind="json_equal", expected={"n": 1}, weight=1)
    assert assertion_passes(assertion, '{"n":1}', "none")
    assert not assertion_passes(assertion, '{"n":true}', "none")
    assert not assertion_passes(assertion, '{"n":1.0}', "none")
