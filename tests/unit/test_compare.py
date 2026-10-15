from agentprobe.compare import compare_reports
from agentprobe.schemas import CaseSummary, RunReport


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


def verdicts(before, after, runs=10):
    diffs = compare_reports(report(before, runs), report(after, runs))
    return {d.case_id: d.verdict for d in diffs}


def test_same_better_worse():
    result = verdicts({"a": 10, "b": 2, "c": 10}, {"a": 10, "b": 10, "c": 3})
    assert result == {"a": "same", "b": "better", "c": "worse"}


def test_new_and_removed_cases():
    result = verdicts({"a": 10, "gone": 10}, {"a": 10, "fresh": 0})
    assert result == {"a": "same", "gone": "removed", "fresh": "new"}


def test_order_follows_first_appearance():
    diffs = compare_reports(report({"a": 10, "b": 10}), report({"c": 10, "a": 10}))
    assert [d.case_id for d in diffs] == ["a", "b", "c"]