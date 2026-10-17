import pytest

from agentprobe.compare import compare_reports
from agentprobe.configdiff import config_differences, parse_config_pairs
from agentprobe.schemas import CaseSummary, RunReport


def summary(case_id, runs, passed, errored=0):
    scored = runs - errored
    rate = passed / scored if scored else 0.0
    return CaseSummary(
        case_id=case_id,
        runs=runs,
        passed=passed,
        pass_rate=rate,
        errored=errored,
    )


def report(*summaries):
    return RunReport(
        run_id="r",
        started_at="2026-01-01T00:00:00Z",
        dataset="d",
        adapter="a",
        total=0,
        passed=0,
        pass_rate=0.0,
        results=[],
        summaries=list(summaries),
    )


def diff_for(before, after, case_id="c"):
    diffs = compare_reports(report(before), report(after))
    return next(d for d in diffs if d.case_id == case_id)


def test_identical_rates_are_same_with_no_p_value():
    d = diff_for(summary("c", 10, 10), summary("c", 10, 10))
    assert d.verdict == "same"
    assert d.p_value is None


def test_same_rate_with_different_run_counts_is_same():
    d = diff_for(summary("c", 10, 5), summary("c", 20, 10))
    assert d.verdict == "same"


def test_large_drop_is_worse():
    d = diff_for(summary("c", 10, 10), summary("c", 10, 5))
    assert d.verdict == "worse"
    assert d.p_value is not None and d.p_value < 0.05


def test_large_gain_is_better():
    d = diff_for(summary("c", 10, 5), summary("c", 10, 10))
    assert d.verdict == "better"
    assert d.p_value is not None and d.p_value < 0.05


def test_small_drop_is_noise():
    d = diff_for(summary("c", 10, 10), summary("c", 10, 8))
    assert d.verdict == "noise"
    assert d.p_value is not None and d.p_value >= 0.05


def test_three_runs_zero_versus_three_is_noise():
    d = diff_for(summary("c", 3, 3), summary("c", 3, 0))
    assert d.verdict == "noise"
    assert d.p_value == pytest.approx(0.10, abs=0.01)


def test_case_only_in_after_is_new():
    diffs = compare_reports(report(), report(summary("c", 10, 9)))
    assert diffs[0].verdict == "new"
    assert diffs[0].before is None
    assert diffs[0].after == pytest.approx(0.9)


def test_case_only_in_before_is_removed():
    diffs = compare_reports(report(summary("c", 10, 9)), report())
    assert diffs[0].verdict == "removed"
    assert diffs[0].after is None
    assert diffs[0].before == pytest.approx(0.9)


def test_all_runs_errored_after_is_inconclusive():
    d = diff_for(summary("c", 10, 10), summary("c", 10, 0, errored=10))
    assert d.verdict == "inconclusive"
    assert d.after is None
    assert d.after_errored == 10


def test_all_runs_errored_before_is_inconclusive():
    d = diff_for(summary("c", 10, 0, errored=10), summary("c", 10, 10))
    assert d.verdict == "inconclusive"
    assert d.before is None
    assert d.before_errored == 10


def test_errored_runs_are_ignored_not_counted_as_failures():
    # 5 of 10 runs errored, the other 5 all passed: the rate is 100%, not 50%.
    d = diff_for(summary("c", 10, 10), summary("c", 10, 5, errored=5))
    assert d.verdict == "same"
    assert d.after == pytest.approx(1.0)
    assert d.after_errored == 5


def test_order_is_before_cases_then_new_cases():
    before = report(summary("b", 5, 5), summary("a", 5, 5))
    after = report(summary("c", 5, 5), summary("a", 5, 5))
    ids = [d.case_id for d in compare_reports(before, after)]
    assert ids == ["b", "a", "c"]


def test_config_differences_reports_changed_value():
    assert config_differences({"prompt": "a"}, {"prompt": "b"}) == {
        "prompt": ("a", "b")
    }


def test_config_differences_marks_missing_keys_as_none():
    diffs = config_differences({"model": "x"}, {"temperature": "0"})
    assert diffs == {"model": ("x", None), "temperature": (None, "0")}


def test_config_differences_empty_when_identical():
    assert config_differences({"prompt": "a"}, {"prompt": "a"}) == {}
    assert config_differences({}, {}) == {}


def test_config_differences_keys_are_sorted():
    diffs = config_differences({"z": "1", "a": "1"}, {"z": "2", "a": "2"})
    assert list(diffs) == ["a", "z"]


def test_parse_config_pairs_basic_and_whitespace():
    assert parse_config_pairs(["model=x", " prompt = pirate "]) == {
        "model": "x",
        "prompt": "pirate",
    }


def test_parse_config_pairs_none_or_empty_gives_empty_dict():
    assert parse_config_pairs(None) == {}
    assert parse_config_pairs([]) == {}


def test_parse_config_pairs_keeps_equals_signs_in_value():
    assert parse_config_pairs(["note=a=b"]) == {"note": "a=b"}


@pytest.mark.parametrize("bad", ["novalue", "=x", "  =x"])
def test_parse_config_pairs_rejects_bad_input(bad):
    with pytest.raises(ValueError):
        parse_config_pairs([bad])