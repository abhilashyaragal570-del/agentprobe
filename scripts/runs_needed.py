import argparse

from agentprobe.power import ALPHA, detection_power, runs_needed

parser = argparse.ArgumentParser(
    description="How many runs per case are needed to detect a drop in pass rate?"
)
parser.add_argument("--before", type=float, required=True, help="true pass rate before, 0 to 1")
parser.add_argument("--after", type=float, required=True, help="true pass rate after, 0 to 1")
parser.add_argument("--power", type=float, default=0.8, help="wanted chance of catching it")
parser.add_argument("--max-runs", type=int, default=100, help="give up above this many runs")
args = parser.parse_args()

try:
    needed = runs_needed(args.before, args.after, args.power, max_runs=args.max_runs)
    checkpoints = [n for n in (5, 10, 20, 30, 50) if n <= args.max_runs]
    rows = [(n, detection_power(args.before, args.after, n)) for n in checkpoints]
except ValueError as exc:
    raise SystemExit(str(exc))

print(
    f"Detecting a drop from {args.before:.0%} to {args.after:.0%} "
    f"(Fisher exact test, p < {ALPHA})"
)
for n, power in rows:
    print(f"  {n:>3} runs per side: caught {power:.0%} of the time")
if needed is None:
    print(f"Not reached within {args.max_runs} runs per side. Raise --max-runs or accept a bigger drop.")
else:
    print(f"At least {needed} runs per side to catch it {args.power:.0%} of the time.")
print("This assumes both sides really have those pass rates and use the same number of runs.")