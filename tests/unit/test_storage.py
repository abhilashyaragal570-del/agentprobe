from pathlib import Path

from agentprobe.adapters.mock import MockAdapter
from agentprobe.dataset import load_cases
from agentprobe.runner import run_suite
from agentprobe.storage import build_report, load_report, save_report

ROOT = Path(__file__).resolve().parents[2]


def _report(wrong=None):
    cases = load_cases(ROOT / "datasets" / "nova_tools.jsonl")
    results = run_suite(MockAdapter(wrong_inputs=wrong), cases)
    return build_report("nova_tools", "mock", results)


def test_report_summary_numbers():
    report = _report(wrong={"What is 458 * 923?"})
    assert report.total == 3
    assert report.passed == 2
    assert report.pass_rate == 2 / 3


def test_save_and_load_round_trip(tmp_path):
    report = _report()
    path = save_report(report, tmp_path)
    assert path.exists()
    loaded = load_report(path)
    assert loaded == report


def test_each_run_gets_a_unique_id():
    assert _report().run_id != _report().run_id
