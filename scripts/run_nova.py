import argparse
import os
from collections import Counter
from getpass import getpass
from pathlib import Path

from agentprobe.adapters.nova import NovaAdapter
from agentprobe.configdiff import parse_config_pairs
from agentprobe.dataset import load_cases
from agentprobe.runner import RunAborted, run_suite
from agentprobe.storage import build_report, save_report

ROOT = Path(__file__).resolve().parents[1]

parser = argparse.ArgumentParser()
parser.add_argument("--repeats", type=int, default=3, help="runs per case")
parser.add_argument("--pause", type=float, default=4.0, help="seconds between calls")
parser.add_argument("--only", nargs="*", help="run only these case ids")
parser.add_argument(
    "--abort-after",
    type=int,
    default=5,
    help="stop after this many errored runs in a row (0 = never stop)",
)
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
try:
    results = run_suite(
        NovaAdapter(),
        cases,
        timeout_s=150,
        repeats=args.repeats,
        pause_s=args.pause,
        abort_after_errors=args.abort_after,
    )
except RunAborted as exc:
    raise SystemExit(
        f"ABORTED after {len(exc.results)} runs: {exc}\n"
        "Nova is probably not running or is rate limited. No report was saved.\n"
        "Fix that, wait a few minutes, and run again."
    )

report = build_report(
    "nova_live",
    "nova",
    results,
    repeats=args.repeats,
    agent_config=agent_config,
)
path = save_report(report, ROOT / "reports")

scored = report.total - report.errored
print(
    f"Run {report.run_id}: {report.passed}/{scored} scored runs passed "
    f"({report.pass_rate:.0%}), {args.repeats} runs per case"
)
if report.errored:
    print(
        f"WARNING: {report.errored} of {report.total} runs errored (rate limit, "
        "timeout or connection) and are NOT counted. Re-run those cases before "
        "you compare."
    )
if agent_config:
    print("Config: " + ", ".join(f"{k}={v}" for k, v in agent_config.items()))
else:
    print("Config: not recorded (use --config key=value to record it)")
for s in report.summaries:
    if s.scored == 0:
        label = "ERROR"
    elif s.flaky:
        label = "FLAKY"
    elif s.passed == s.scored:
        label = "PASS "
    else:
        label = "FAIL "
    latency = "-" if s.avg_latency_ms is None else f"{s.avg_latency_ms:.0f} ms avg"
    extra = f", {s.errored} errored" if s.errored else ""
    print(f"  {label} {s.case_id}: {s.passed}/{s.scored} ({latency}{extra})")
for r in results:
    if r.passed or r.errored:
        continue
    took = "" if r.latency_ms is None else f" [{r.latency_ms / 1000:.0f}s]"
    print(f"    - {r.case_id}{took}: {r.failure_reasons}")
error_counts = Counter((r.error or "unknown")[:120] for r in results if r.errored)
for message, count in error_counts.most_common():
    print(f"    ! {count} errored: {message}")
print(f"Saved to {path}")