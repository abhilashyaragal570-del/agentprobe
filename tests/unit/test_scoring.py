from pathlib import Path

from agentprobe.adapters.mock import MockAdapter
from agentprobe.dataset import load_cases
from agentprobe.runner import run_suite
from agentprobe.schemas import AgentOutput, CaseResult, TestCase
from agentprobe.scoring import exact_match, pass_rate, score_case

ROOT = Path(__file__).resolve().parents[2]


def test_exact_match_ignores_outer_spaces():
    assert exact_match(" Hello ", "Hello")


def test_correct_output_passes():
    case = TestCase(id="a", input="x", expected_answer="5", expected_tools=["calculator"])
    output = AgentOutput(answer="5", tools_used=["calculator"])
    assert score_case(case, output) == []


def test_wrong_answer_fails_with_reason():
    case = TestCase(id="a", input="x", expected_answer="5")
    reasons = score_case(case, AgentOutput(answer="6"))
    assert any("wrong answer" in r for r in reasons)


def test_wrong_tool_fails_with_reason():
    case = TestCase(id="a", input="x", expected_tools=["calculator"])
    reasons = score_case(case, AgentOutput(answer="", tools_used=[]))
    assert any("wrong tools" in r for r in reasons)


def test_unexpected_tool_use_fails():
    case = TestCase(id="a", input="x", expected_tools=[])
    reasons = score_case(case, AgentOutput(tools_used=["calculator"]))
    assert any("wrong tools" in r for r in reasons)


def test_adapter_error_fails():
    case = TestCase(id="a", input="x")
    reasons = score_case(case, AgentOutput(error="boom"))
    assert any("adapter error" in r for r in reasons)


def test_pass_rate():
    results = [
        CaseResult(case_id="a", passed=True),
        CaseResult(case_id="b", passed=True),
        CaseResult(case_id="c", passed=False),
        CaseResult(case_id="d", passed=True),
    ]
    assert pass_rate(results) == 0.75


def test_empty_results_pass_rate():
    assert pass_rate([]) == 0.0


def test_full_suite_with_mock_all_pass():
    cases = load_cases(ROOT / "datasets" / "nova_tools.jsonl")
    results = run_suite(MockAdapter(), cases)
    assert pass_rate(results) == 1.0


def test_full_suite_catches_one_wrong_answer():
    cases = load_cases(ROOT / "datasets" / "nova_tools.jsonl")
    adapter = MockAdapter(wrong_inputs={"What is 458 * 923?"})
    results = run_suite(adapter, cases)
    failed = [r for r in results if not r.passed]
    assert [r.case_id for r in failed] == ["calc-001"]
    assert pass_rate(results) == 2 / 3
