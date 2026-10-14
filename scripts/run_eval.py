from pathlib import Path

from agentprobe.adapters.mock import MockAdapter
from agentprobe.dataset import load_cases
from agentprobe.runner import run_suite
from agentprobe.storage import build_report, save_report

ROOT = Path(__file__).resolve().parents[1]

cases = load_cases(ROOT / "datasets" / "nova_tools.jsonl")
results = run_suite(MockAdapter(), cases)
report = build_report("nova_tools", "mock", results)
path = save_report(report, ROOT / "reports")

print(f"Run {report.run_id}: {report.passed}/{report.total} passed ({report.pass_rate:.0%})")
for r in results:
    status = "PASS" if r.passed else "FAIL"
    print(f"  {status} {r.case_id} ({r.latency_ms:.2f} ms) {r.failure_reasons}")
print(f"Saved to {path}")
