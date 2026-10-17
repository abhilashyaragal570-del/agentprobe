from .compare import compare_reports
from .configdiff import config_differences
from .schemas import RunReport


def _pct(value: float | None) -> str:
    return "-" if value is None else f"{value:.0%}"


def _cell(text: str) -> str:
    """Make text safe inside a markdown table cell."""
    return str(text).replace("|", "\\|").replace("\n", " ")


def _shown(value: str | None) -> str:
    return "(not recorded)" if value is None else value


def comparison_markdown(before: RunReport, after: RunReport) -> str:
    """Render a comparison of two reports as markdown you can paste anywhere."""
    lines = [
        "# AgentProbe comparison",
        "",
        f"- Before: `{before.run_id}` ({before.pass_rate:.0%} pass, "
        f"{before.repeats} runs per case)",
        f"- After: `{after.run_id}` ({after.pass_rate:.0%} pass, "
        f"{after.repeats} runs per case)",
        "",
    ]

    diffs = config_differences(before.agent_config, after.agent_config)
    if diffs:
        lines.append(
            "**Warning:** the agent configuration differs between these runs, "
            "so differences below may come from the config change, not the agent code."
        )
        for key, (old, new) in diffs.items():
            lines.append(f"- {key}: {_shown(old)} -> {_shown(new)}")
        lines.append("")
    elif not before.agent_config and not after.agent_config:
        lines.append("Note: neither report recorded its agent configuration.")
        lines.append("")

    for label, report in (("before", before), ("after", after)):
        if report.errored:
            lines.append(
                f"Note: the {label} report has {report.errored} errored runs "
                "(rate limit, timeout or connection). They are ignored here."
            )
            lines.append("")

    lines.append("| Case | Before | After | Verdict | p-value | Errored (before / after) |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for d in compare_reports(before, after):
        p = "-" if d.p_value is None else f"{d.p_value:.2f}"
        lines.append(
            f"| {_cell(d.case_id)} | {_pct(d.before)} | {_pct(d.after)} | "
            f"{d.verdict.upper()} | {p} | {d.before_errored} / {d.after_errored} |"
        )
    lines.append("")
    lines.append(
        "NOISE means the difference could easily be chance. "
        "INCONCLUSIVE means one side had no usable runs."
    )
    return "\n".join(lines) + "\n"