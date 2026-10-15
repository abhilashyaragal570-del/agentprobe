import argparse
import os
from getpass import getpass
from pathlib import Path

from agentprobe.adapters.nova import NovaAdapter
from agentprobe.dataset import load_cases
from agentprobe.runner import run_suite
from agentprobe.storage import build_report, save_report

ROOT = Path(__file__).resolve().parents[1]

parser = argparse.ArgumentParser()
parser.add_argument("--repeats", type=int, default=3, help="runs per case")
parser.add_argument("--pause", type=float, default=4.0, help="seconds between calls")
parser.add_argument("--only", nargs="*", help="run only these case ids")
args = parser.parse_args()

if not os.environ.get("NOVA_PASSWORD"):
    os.environ["NOVA_PASSWORD"] = getpass("NOVA_PASSWORD: ")

cases = load_cases(ROOT / "datasets" / "nova_live.jsonl")
if args.only:
    cases = [c for c in cases if c.id in args.only]
    if not cases:
        raise SystemExit(f"No cases match {args.only}")

# The timeout must cover Nova's own 429 retries.
results = run_suite(
    NovaAdapter(), cases, timeout_s=150, repeats=args.repeats, pause_s=args.pause
)
report = build_report("nova_live", "nova", results, repeats=args.repeats)
path = save_report(report, ROOT / "reports")

print(
    f"Run {report.run_id}: {report.passed}/{report.total} runs passed "
    f"({report.pass_rate:.0%}), {args.repeats} runs per case"
)
for s in report.summaries:
    label = "FLAKY" if s.flaky else ("PASS " if s.passed == s.runs else "FAIL ")
    print(f"  {label} {s.case_id}: {s.passed}/{s.runs} ({s.avg_latency_ms:.0f} ms avg)")
for r in results:
    if not r.passed:
        print(f"    - {r.case_id}: {r.failure_reasons}")
print(f"Saved to {path}")