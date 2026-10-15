from agentprobe.schemas import AgentOutput, TestCase
from agentprobe.scoring import score_case


def _case(**kwargs):
    return TestCase(id="t", input="q", **kwargs)


def test_empty_answer_is_reported():
    reasons = score_case(_case(), AgentOutput(answer=""))
    assert reasons == ["empty answer"]


def test_whitespace_only_answer_is_empty():
    reasons = score_case(_case(), AgentOutput(answer="  \n "))
    assert reasons == ["empty answer"]


def test_empty_answer_comes_first_before_wrong_tools():
    reasons = score_case(_case(expected_tools=["list_files"]), AgentOutput(answer=""))
    assert reasons[0] == "empty answer"
    assert len(reasons) == 2
    assert reasons[1].startswith("wrong tools")


def test_adapter_error_does_not_add_empty_answer():
    reasons = score_case(_case(), AgentOutput(answer="", error="boom"))
    assert reasons == ["adapter error: boom"]


def test_non_empty_answer_has_no_empty_reason():
    assert score_case(_case(), AgentOutput(answer="hello")) == []


def test_case_without_expected_answer_still_fails_on_empty():
    case = _case(expected_tools=["list_files"])
    output = AgentOutput(answer="", tools_used=["list_files"])
    assert score_case(case, output) == ["empty answer"]