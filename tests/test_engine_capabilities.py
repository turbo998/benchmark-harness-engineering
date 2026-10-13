import json
from pathlib import Path

import pytest

from benchmark_harness.agents.copilot import parse_events, probe_help
from benchmark_harness.contracts import Status
from benchmark_harness.engines.harbor import parse_trial, write_trial_config
from benchmark_harness.engines.promptfoo import parse_output, write_mock_config
from benchmark_harness.samples import template_cases

FIXTURES = Path(__file__).parent / "fixtures" / "engine-outputs"


def test_promptfoo_release_contract_success_errors_and_missing_usage() -> None:
    rows = parse_output(json.loads((FIXTURES / "promptfoo.json").read_bytes()))
    assert [r.status for r in rows] == [Status.PASSED, Status.FAILED, Status.AUTH_ERROR]
    assert rows[0].native_cost_usd == 0
    assert rows[1].native_cost_usd is None and rows[1].usage.input_tokens is None
    assert rows[0].usage.reason and rows[0].usage.reason.startswith("Cache-write")
    with pytest.raises(ValueError, match="shape"):
        parse_output({"results": []})
    with pytest.raises(ValueError, match="Partial"):
        parse_output({"results": {"results": [{"response": {}}]}})


def test_harbor_inclusive_input_conversion_and_separate_verifier() -> None:
    payload = json.loads((FIXTURES / "harbor.json").read_bytes())
    row = parse_trial(payload)
    assert row.status == Status.PASSED
    assert row.usage.input_tokens == 10 and row.usage.cache_read_tokens == 5
    assert row.usage.cache_write_tokens is None
    assert row.latency_ms == 1000
    assert row.native_cost_usd is None
    with pytest.raises(ValueError, match="Cache"):
        parse_trial(payload | {"agent_result": {"n_input_tokens": 5, "n_cache_tokens": 10}})
    partial = parse_trial(payload | {"verifier_result": None})
    assert partial.status == Status.INFRASTRUCTURE_ERROR
    exception = parse_trial(
        payload
        | {
            "exception_info": {
                "exception_type": "RateLimitError",
                "exception_message": "quota exhausted",
            }
        }
    )
    assert exception.status == Status.QUOTA_ERROR
    with pytest.raises(ValueError, match="Multi-step"):
        parse_trial(payload | {"agent_result": None, "step_results": [{}]})


def test_copilot_opaque_and_malformed_event_retention() -> None:
    data = parse_events((FIXTURES / "copilot.jsonl").read_text(encoding="utf-8"))
    assert data["terminal_seen"]
    assert data["usage"]["input_tokens"] == 12
    assert data["cost_usd"] is None
    assert len(data["malformed_lines"]) == 1
    partial = parse_events('{"type":"assistant.message","data":{"content":"answer"}}')
    assert not partial["terminal_seen"]
    assert partial["usage"]["input_tokens"] is None
    assert partial["status"] != "passed"
    assert parse_events("Error: No authentication information found")["status"] == "auth_error"
    help_result = probe_help("GitHub Copilot CLI 1.0.94-3", "--prompt --model --output-format")
    assert help_result["observed_version"] == "1.0.94-3"
    assert not help_result["strict_dollar_cap"] and not help_result["live_allowed"]


def test_safe_real_config_construction(workdir: Path) -> None:
    path = write_mock_config(template_cases(), workdir / "api")
    config = json.loads(path.read_bytes())
    assert config["providers"] == ["file://mock-provider.cjs"]
    assert len(config["tests"]) == 6
    assert "fetch(" not in (path.parent / "mock-provider.cjs").read_text()
    result = write_trial_config(Path("original-fixture"), workdir / "trial.json")
    assert result["framework_max_retries"] == 0 and not result["live_allowed"]
    assert "construction-only" in result["capability"]
    with pytest.raises(RuntimeError, match="blocked"):
        write_trial_config(Path("original-fixture"), workdir / "live.json", agent="copilot-cli")


def test_observed_no_cost_engine_export() -> None:
    rows = parse_output(json.loads((FIXTURES / "promptfoo-observed.json").read_bytes()))
    assert len(rows) == 6 and all(r.status == Status.PASSED for r in rows)
    assert all(r.native_cost_usd == 0 for r in rows)
    assert all(r.usage.input_tokens == 0 for r in rows)
    assert all(r.usage.reasoning_tokens == 0 for r in rows)
