import pytest

from agentprobe.compare import compare_reports
from agentprobe.schemas import CaseSummary, RunReport
from agentprobe.stats import fisher_exact_p


def test_identical_groups_have_p_of_one():
    assert fisher_exact_p(5, 10, 5, 10) == pytest.approx(1.0)


def test_one_miss_in_three_is_not_significant():
    assert fisher_exact_p(3, 3, 2, 3) == pytest.approx(1.0)


def test_a_big_gap_is_significant():
    assert fisher_exact_p(10, 10, 3, 10) < 0.01


def test_known_value():
    # classic 2x2 example: 8/10 vs 2/10 -> p about 0.023
    assert fisher_exact_p(8, 10, 2, 10) == pytest.approx(0.0237, abs=0.001)


def test_zero_runs_is_safe():
    assert fisher_exact_p(0, 0, 3, 3) == 1.0


def report(counts, runs=10):
    summaries = [
        CaseSummary(case_id=c, runs=runs, passed=p, pass_rate=p / runs)
        for c, p in counts.items()
    ]
    return RunReport(
        run_id="r", started_at="t", dataset="d", adapter="a",
        total=0, passed=0, pass_rate=0.0, results=[],
        repeats=runs, summaries=summaries,
    )


def test_compare_calls_small_gaps_noise_and_big_gaps_real():
    diffs = compare_reports(
        report({"a": 10, "b": 10, "c": 2}),
        report({"a": 9, "b": 3, "c": 10}),
    )
    assert {d.case_id: d.verdict for d in diffs} == {
        "a": "noise",
        "b": "worse",
        "c": "better",
    }