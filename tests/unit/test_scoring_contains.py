import pytest

from agentprobe.schemas import AgentOutput, TestCase
from agentprobe.scoring import contains_match, score_case


@pytest.mark.parametrize(
    "actual, expected, ok",
    [
        ("458 x 923 = 422,734.", "422734", True),
        ("The answer is 422734", "422734", True),
        ("10% of 500 is 50.", "50", True),
        ("The total is 500.", "50", False),
        ("It is 1422734", "422734", False),
        ("Hello!", "hello", True),
        ("anything", "", False),
    ],
)
def test_contains_match(actual, expected, ok):
    assert contains_match(actual, expected) is ok


def test_contains_mode_is_used_by_score_case():
    case = TestCase(
        id="a",
        input="x",
        expected_answer="422734",
        answer_match="contains",
        expected_tools=["calculator"],
    )
    output = AgentOutput(answer="It is 422,734.", tools_used=["calculator"])
    assert score_case(case, output) == []


def test_exact_mode_is_still_the_default():
    case = TestCase(id="a", input="x", expected_answer="422734")
    output = AgentOutput(answer="It is 422,734.")
    assert any("wrong answer" in r for r in score_case(case, output))