import pytest

from agentprobe.compare import compare_reports
from agentprobe.runner import RunAborted, run_case, run_suite
from agentprobe.schemas import AgentOutput, CaseResult, CaseSummary, TestCase
from agentprobe.scoring import pass_rate
from agentprobe.storage import build_report
from agentprobe.summary import summarize_cases


class FakeAdapter:
    """Returns the given outputs in order, repeating the last one."""

    def __init__(self, *outputs):
        self.outputs = list(outputs)
        self.calls = 0

    def run(self, text):
        index = min(self.calls, len(self.outputs) - 1)
        self.calls += 1
        return self.outputs[index]


def _case():
    return TestCase(id="a", input="q")


def _r(case_id="a", passed=True, errored=False):
    return CaseResult(
        case_id=case_id,
        passed=passed and not errored,
        errored=errored,
        answer="x",
        latency_ms=1.0,
    )


def _report(results):
    return build_report("ds", "ad", results, repeats=10)


def test_run_case_marks_adapter_error_as_errored():
    result = run_case(FakeAdapter(AgentOutput(error="error 429")), _case())
    assert result.errored is True
    assert result.passed is False


def test_run_case_without_error_is_not_errored():
    result = run_case(FakeAdapter(AgentOutput(answer="hi")), _case())
    assert result.errored is False
    assert result.passed is True


def test_summary_leaves_errored_runs_out():
    results = [_r() for _ in range(3)] + [_r(errored=True) for _ in range(2)]
    s = summarize_cases(results)[0]
    assert (s.runs, s.passed, s.errored, s.scored) == (5, 3, 2, 3)
    assert s.pass_rate == 1.0
    assert s.flaky is False


def test_summary_when_every_run_errored():
    s = summarize_cases([_r(errored=True) for _ in range(3)])[0]
    assert s.scored == 0
    assert s.pass_rate == 0.0
    assert s.avg_latency_ms is None
    assert s.flaky is False


def test_pass_rate_ignores_errored_runs():
    results = [_r(), _r(passed=False), _r(errored=True), _r(errored=True)]
    assert pass_rate(results) == 0.5
    assert pass_rate([_r(errored=True)]) == 0.0


def test_build_report_counts_errored_runs():
    results = [_r(), _r(), _r(errored=True)]
    report = _report(results)
    assert report.total == 3
    assert report.errored == 1
    assert report.passed == 2
    assert report.pass_rate == 1.0


def test_compare_ignores_errored_runs():
    before = _report([_r() for _ in range(10)])
    after = _report([_r() for _ in range(5)] + [_r(errored=True) for _ in range(5)])
    d = compare_reports(before, after)[0]
    assert d.verdict == "same"
    assert d.after_errored == 5


def test_compare_is_inconclusive_when_one_side_never_ran():
    before = _report([_r() for _ in range(10)])
    after = _report([_r(errored=True) for _ in range(10)])
    d = compare_reports(before, after)[0]
    assert d.verdict == "inconclusive"
    assert d.after is None


def test_compare_still_detects_a_real_regression():
    before = _report([_r() for _ in range(10)])
    after = _report([_r() for _ in range(2)] + [_r(passed=False) for _ in range(8)])
    assert compare_reports(before, after)[0].verdict == "worse"


def test_suite_aborts_after_errors_in_a_row():
    adapter = FakeAdapter(AgentOutput(error="error 429"))
    with pytest.raises(RunAborted) as info:
        run_suite(adapter, [_case()], repeats=10, abort_after_errors=3)
    assert len(info.value.results) == 3
    assert adapter.calls == 3


def test_suite_does_not_abort_when_errors_are_interleaved():
    adapter = FakeAdapter(
        AgentOutput(error="error 429"), AgentOutput(answer="ok"),
        AgentOutput(error="error 429"), AgentOutput(answer="ok"),
        AgentOutput(error="error 429"), AgentOutput(answer="ok"),
    )
    results = run_suite(adapter, [_case()], repeats=6, abort_after_errors=2)
    assert len(results) == 6


def test_abort_is_off_by_default():
    adapter = FakeAdapter(AgentOutput(error="boom"))
    results = run_suite(adapter, [_case()], repeats=4)
    assert len(results) == 4


def test_old_reports_without_the_new_fields_still_load():
    result = CaseResult.model_validate({"case_id": "a", "passed": True})
    summary = CaseSummary.model_validate(
        {"case_id": "a", "runs": 4, "passed": 4, "pass_rate": 1.0}
    )
    assert result.errored is False
    assert summary.errored == 0
    assert summary.scored == 4