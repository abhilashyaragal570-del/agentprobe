import argparse
import os
from collections import Counter
from pathlib import Path

from agentprobe.adapters.http import HttpAdapter
from agentprobe.configdiff import parse_config_pairs
from agentprobe.dataset import load_cases
from agentprobe.runner import RunAborted, run_suite
from agentprobe.storage import build_report, save_report

ROOT = Path(__file__).resolve().parents[1]

parser = argparse.ArgumentParser(
    description="Run a dataset against any HTTP agent that takes and returns JSON."
)
parser.add_argument("--url", required=True, help="endpoint that receives the POST")
parser.add_argument(
    "--dataset",
    required=True,
    help="name of a file in datasets/ without .jsonl",
)
parser.add_argument("--request-field", default="message", help="JSON key for the input")
parser.add_argument(
    "--answer-field",
    default="answer",
    help="dotted path to the answer in the reply, e.g. data.reply or choices.0.text",
)
parser.add_argument(
    "--tools-field",
    default=None,
    help="dotted path to the list of tool names in the reply (optional)",
)
parser.add_argument(
    "--token-env",
    default=None,
    metavar="NAME",
    help="name of an environment variable holding a bearer token",
)
parser.add_argument("--timeout", type=float, default=60.0, help="seconds per request")
parser.add_argument("--repeats", type=int, default=3, help="runs per case")
parser.add_argument("--pause", type=float, default=2.0, help="seconds between calls")
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
    help="agent settings to record in the report, e.g. model=x temperature=0",
)
args = parser.parse_args()

try:
    agent_config = parse_config_pairs(args.config)
except ValueError as exc:
    raise SystemExit(str(exc))

dataset_path = ROOT / "datasets" / f"{args.dataset}.jsonl"
if not dataset_path.exists():
    raise SystemExit(f"Dataset not found: {dataset_path}")

headers = {}
if args.token_env:
    token = os.environ.get(args.token_env)
    if not token:
        raise SystemExit(f"Environment variable {args.token_env} is not set")
    headers["Authorization"] = f"Bearer {token}"

cases = load_cases(dataset_path)
if args.only:
    cases = [c for c in cases if c.id in args.only]
    if not cases:
        raise SystemExit(f"No cases match {args.only}")

if not args.tools_field and any(c.expected_tools for c in cases):
    print(
        "Note: some cases expect tools but --tools-field is not set, so they "
        "will fail with 'wrong tools'."
    )

adapter = HttpAdapter(
    args.url,
    request_field=args.request_field,
    answer_field=args.answer_field,
    tools_field=args.tools_field,
    headers=headers,
    timeout_s=args.timeout,
)

# The run timeout must cover the adapter's own retries and waits.
try:
    results = run_suite(
        adapter,
        cases,
        timeout_s=args.timeout * 4 + 70,
        repeats=args.repeats,
        pause_s=args.pause,
        abort_after_errors=args.abort_after,
    )
except RunAborted as exc:
    raise SystemExit(
        f"ABORTED after {len(exc.results)} runs: {exc}\n"
        "The agent is probably not reachable, is rate limited, or the URL or "
        "field names are wrong. No report was saved.\n"
        "Check the last error above, fix it, and run again."
    )

report = build_report(
    args.dataset,
    "http",
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
        "timeout, connection or bad reply) and are NOT counted. Re-run those "
        "cases before you compare."
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