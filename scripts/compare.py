import sys

from agentprobe.compare import compare_reports
from agentprobe.storage import load_report

if len(sys.argv) != 3:
    raise SystemExit("Usage: python scripts\\compare.py BEFORE.json AFTER.json")

before = load_report(sys.argv[1])
after = load_report(sys.argv[2])


def pct(value):
    return "  -  " if value is None else f"{value:.0%}".rjust(5)


print(f"before: {before.run_id} ({before.pass_rate:.0%}, {before.repeats} per case)")
print(f"after:  {after.run_id} ({after.pass_rate:.0%}, {after.repeats} per case)")
for d in compare_reports(before, after):
    extra = "" if d.p_value is None else f"  (p={d.p_value:.2f})"
    print(f"  {d.verdict.upper():8} {d.case_id}: {pct(d.before)} -> {pct(d.after)}{extra}")
print("NOISE means the difference could easily be chance. Add more repeats to tell.")