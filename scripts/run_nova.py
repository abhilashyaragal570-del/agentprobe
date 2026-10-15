import os
from getpass import getpass
from pathlib import Path

from agentprobe.adapters.nova import NovaAdapter
from agentprobe.dataset import load_cases
from agentprobe.runner import run_suite
from agentprobe.storage import build_report, save_report

ROOT = Path(__file__).resolve().parents[1]

if not os.environ.get("NOVA_PASSWORD"):
    os.environ["NOVA_PASSWORD"] = getpass("NOVA_PASSWORD: ")

cases = load_cases(ROOT / "datasets" / "nova_live.jsonl")
results = run_suite(NovaAdapter(), cases, timeout_s=90)
report = build_report("nova_live", "nova", results)
path = save_report(report, ROOT / "reports")

print(f"Run {report.run_id}: {report.passed}/{report.total} passed ({report.pass_rate:.0%})")
for r in results:
    status = "PASS" if r.passed else "FAIL"
    print(f"  {status} {r.case_id} ({r.latency_ms:.0f} ms) {r.failure_reasons}")
print(f"Saved to {path}")