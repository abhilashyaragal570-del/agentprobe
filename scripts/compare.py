import argparse
from pathlib import Path

from agentprobe.compare import compare_reports
from agentprobe.configdiff import config_differences
from agentprobe.markdown_report import comparison_markdown
from agentprobe.storage import load_report

parser = argparse.ArgumentParser(description="Compare two AgentProbe reports.")
parser.add_argument("before", help="path to the BEFORE report (.json)")
parser.add_argument("after", help="path to the AFTER report (.json)")
parser.add_argument(
    "--markdown",
    metavar="FILE",
    help="also write the comparison as a markdown file",
)
args = parser.parse_args()

before = load_report(args.before)
after = load_report(args.after)


def pct(value):
    return "  -  " if value is None else f"{value:.0%}".rjust(5)


print(f"before: {before.run_id} ({before.pass_rate:.0%}, {before.repeats} per case)")
print(f"after:  {after.run_id} ({after.pass_rate:.0%}, {after.repeats} per case)")

diffs = config_differences(before.agent_config, after.agent_config)
if diffs:
    print("WARNING: the agent configuration differs between these runs:")
    for key, (old, new) in diffs.items():
        print(f"  {key}: {old if old is not None else '(not recorded)'} -> "
              f"{new if new is not None else '(not recorded)'}")
    print("Differences below may come from the config change, not the agent code.")
elif not before.agent_config and not after.agent_config:
    print("Note: neither report recorded its agent configuration.")

for label, report in (("before", before), ("after", after)):
    if report.errored:
        print(f"Note: the {label} report has {report.errored} errored runs "
              "(rate limit, timeout or connection). They are ignored here.")

for d in compare_reports(before, after):
    extra = "" if d.p_value is None else f"  (p={d.p_value:.2f})"
    if d.before_errored or d.after_errored:
        extra += f"  [errored: {d.before_errored} before, {d.after_errored} after]"
    print(f"  {d.verdict.upper():12} {d.case_id}: {pct(d.before)} -> {pct(d.after)}{extra}")
print("NOISE means the difference could easily be chance. Add more repeats to tell.")
print("INCONCLUSIVE means one side had no usable runs. Re-run that case.")

if args.markdown:
    out = Path(args.markdown)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(comparison_markdown(before, after), encoding="utf-8")
    print(f"Markdown written to {out}")