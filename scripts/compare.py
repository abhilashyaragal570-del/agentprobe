import sys

from agentprobe.compare import compare_reports
from agentprobe.configdiff import config_differences
from agentprobe.storage import load_report

if len(sys.argv) != 3:
    raise SystemExit("Usage: python scripts\\compare.py BEFORE.json AFTER.json")

before = load_report(sys.argv[1])
after = load_report(sys.argv[2])


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

for d in compare_reports(before, after):
    extra = "" if d.p_value is None else f"  (p={d.p_value:.2f})"
    print(f"  {d.verdict.upper():8} {d.case_id}: {pct(d.before)} -> {pct(d.after)}{extra}")
print("NOISE means the difference could easily be chance. Add more repeats to tell.")