import pytest

from agentprobe.adapters.mock import MockAdapter
from agentprobe.runner import run_suite
from agentprobe.schemas import AgentOutput, RunReport, TestCase
from agentprobe.storage import build_report


class AlternatingAdapter:
    """Right on calls 1, 3, 5..., wrong on calls 2, 4, 6..."""

    def __init__(self):
        self.calls = 0

    def run(self, input_text):
        self.calls += 1
        return AgentOutput(answer="yes" if self.calls % 2 == 1 else "no")


def test_repeats_multiplies_results_and_groups_by_case():
    cases = [TestCase(id="a", input="x"), TestCase(id="b", input="y")]
    results = run_suite(MockAdapter(), cases, repeats=3)
    assert [r.case_id for r in results] == ["a", "a", "a", "b", "b", "b"]


def test_repeats_must_be_positive():
    with pytest.raises(ValueError):
        run_suite(MockAdapter(), [], repeats=0)


def test_a_case_that_sometimes_fails_is_flaky():
    case = TestCase(id="a", input="x", expected_answer="yes")
    results = run_suite(AlternatingAdapter(), [case], repeats=4)
    report = build_report("d", "alt", results, repeats=4)
    summary = report.summaries[0]
    assert summary.runs == 4
    assert summary.passed == 2
    assert summary.pass_rate == 0.5
    assert summary.flaky is True


def test_a_stable_case_is_not_flaky():
    case = TestCase(
        id="a",
        input="What is 458 * 923?",
        expected_answer="422734",
        expected_tools=["calculator"],
    )
    results = run_suite(MockAdapter(), [case], repeats=3)
    summary = build_report("d", "mock", results, repeats=3).summaries[0]
    assert summary.passed == 3
    assert summary.flaky is False


def test_report_records_repeats():
    results = run_suite(MockAdapter(), [TestCase(id="a", input="x")], repeats=2)
    report = build_report("d", "mock", results, repeats=2)
    assert report.repeats == 2
    assert report.total == 2


def test_old_reports_without_the_new_fields_still_load():
    old = (
        '{"run_id":"r","started_at":"t","dataset":"d","adapter":"a",'
        '"total":0,"passed":0,"pass_rate":0.0,"results":[]}'
    )
    report = RunReport.model_validate_json(old)
    assert report.repeats == 1
    assert report.summaries == []