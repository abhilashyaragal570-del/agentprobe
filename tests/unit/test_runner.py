from agentprobe.adapters.mock import MockAdapter
from agentprobe.runner import run_case, run_suite
from agentprobe.schemas import TestCase


class CrashingAdapter:
    def run(self, input_text):
        raise RuntimeError("boom")


def test_run_suite_returns_one_result_per_case():
    cases = [
        TestCase(id="a", input="What is 458 * 923?"),
        TestCase(id="b", input="Say hello in one short sentence."),
    ]
    results = run_suite(MockAdapter(), cases)
    assert [r.case_id for r in results] == ["a", "b"]
    assert results[0].answer == "422734"


def test_latency_is_recorded():
    result = run_case(MockAdapter(), TestCase(id="a", input="What is 458 * 923?"))
    assert result.latency_ms is not None
    assert result.latency_ms >= 0


def test_adapter_crash_is_recorded_not_raised():
    result = run_case(CrashingAdapter(), TestCase(id="a", input="anything"))
    assert result.error is not None
    assert "boom" in result.error
