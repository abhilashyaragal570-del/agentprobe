import argparse
import os
from getpass import getpass
from pathlib import Path

from agentprobe.adapters.nova import NovaAdapter
from agentprobe.configdiff import parse_config_pairs
from agentprobe.dataset import load_cases
from agentprobe.runner import run_suite
from agentprobe.storage import build_report, save_report

ROOT = Path(__file__).resolve().parents[1]

parser = argparse.ArgumentParser()
parser.add_argument("--repeats", type=int, default=3, help="runs per case")
parser.add_argument("--pause", type=float, default=4.0, help="seconds between calls")
parser.add_argument("--only", nargs="*", help="run only these case ids")
parser.add_argument(
    "--config",
    nargs="*",
    default=[],
    metavar="KEY=VALUE",
    help="agent settings to record in the report, e.g. prompt=pirate",
)
args = parser.parse_args()

try:
    agent_config = parse_config_pairs(args.config)
except ValueError as exc:
    raise SystemExit(str(exc))

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
report = build_report(
    "nova_live",
    "nova",
    results,
    repeats=args.repeats,
    agent_config=agent_config,
)
path = save_report(report, ROOT / "reports")

print(
    f"Run {report.run_id}: {report.passed}/{report.total} runs passed "
    f"({report.pass_rate:.0%}), {args.repeats} runs per case"
)
if agent_config:
    print("Config: " + ", ".join(f"{k}={v}" for k, v in agent_config.items()))
else:
    print("Config: not recorded (use --config key=value to record it)")
for s in report.summaries:
    label = "FLAKY" if s.flaky else ("PASS " if s.passed == s.runs else "FAIL ")
    print(f"  {label} {s.case_id}: {s.passed}/{s.runs} ({s.avg_latency_ms:.0f} ms avg)")
for r in results:
    if not r.passed:
        took = "" if r.latency_ms is None else f" [{r.latency_ms / 1000:.0f}s]"
        print(f"    - {r.case_id}{took}: {r.failure_reasons}")
print(f"Saved to {path}")