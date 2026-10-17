from agentprobe.markdown_report import comparison_markdown
from agentprobe.schemas import CaseSummary, RunReport


def summary(case_id, runs, passed, errored=0):
    scored = runs - errored
    rate = passed / scored if scored else 0.0
    return CaseSummary(
        case_id=case_id, runs=runs, passed=passed, pass_rate=rate, errored=errored
    )


def report(*summaries, run_id="r", config=None, errored=0):
    return RunReport(
        run_id=run_id,
        started_at="2026-01-01T00:00:00Z",
        dataset="d",
        adapter="a",
        total=0,
        passed=0,
        pass_rate=0.0,
        results=[],
        summaries=list(summaries),
        agent_config=config or {},
        errored=errored,
    )


def test_has_title_and_both_run_ids():
    text = comparison_markdown(
        report(summary("c", 10, 10), run_id="old-run"),
        report(summary("c", 10, 10), run_id="new-run"),
    )
    assert text.startswith("# AgentProbe comparison")
    assert "`old-run`" in text
    assert "`new-run`" in text


def test_table_has_header_separator_and_a_row_per_case():
    text = comparison_markdown(
        report(summary("a", 10, 10), summary("b", 10, 10)),
        report(summary("a", 10, 10), summary("b", 10, 10)),
    )
    assert "| Case | Before | After | Verdict | p-value |" in text
    assert "| --- | --- | --- | --- | --- | --- |" in text
    assert "| a | 100% | 100% | SAME | - | 0 / 0 |" in text
    assert "| b | 100% | 100% | SAME | - | 0 / 0 |" in text


def test_worse_row_shows_rates_verdict_and_p_value():
    text = comparison_markdown(
        report(summary("c", 10, 10)), report(summary("c", 10, 5))
    )
    assert "| c | 100% | 50% | WORSE | 0." in text


def test_new_and_removed_rows_show_dash_for_missing_rate():
    text = comparison_markdown(
        report(summary("a", 5, 5)), report(summary("b", 5, 5))
    )
    assert "| a | 100% | - | REMOVED | - | 0 / 0 |" in text
    assert "| b | - | 100% | NEW | - | 0 / 0 |" in text


def test_config_difference_warning_lists_changed_keys():
    text = comparison_markdown(
        report(summary("c", 10, 10), config={"prompt": "pirate"}),
        report(summary("c", 10, 10), config={"prompt": "soft"}),
    )
    assert "**Warning:**" in text
    assert "- prompt: pirate -> soft" in text


def test_note_when_neither_report_recorded_config():
    text = comparison_markdown(report(summary("c", 10, 10)), report(summary("c", 10, 10)))
    assert "neither report recorded" in text


def test_no_config_message_when_configs_match():
    cfg = {"prompt": "pirate"}
    text = comparison_markdown(
        report(summary("c", 10, 10), config=cfg),
        report(summary("c", 10, 10), config=cfg),
    )
    assert "Warning" not in text
    assert "neither report recorded" not in text


def test_errored_runs_get_a_note_and_a_column_value():
    text = comparison_markdown(
        report(summary("c", 10, 10)),
        report(summary("c", 10, 5, errored=5), errored=5),
    )
    assert "the after report has 5 errored runs" in text
    assert "| c | 100% | 100% | SAME | - | 0 / 5 |" in text


def test_pipe_in_case_id_is_escaped():
    text = comparison_markdown(
        report(summary("a|b", 5, 5)), report(summary("a|b", 5, 5))
    )
    assert "| a\\|b |" in text


def test_output_ends_with_exactly_one_newline():
    text = comparison_markdown(report(summary("c", 5, 5)), report(summary("c", 5, 5)))
    assert text.endswith("\n")
    assert not text.endswith("\n\n")