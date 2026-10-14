from agentprobe.adapters.mock import MockAdapter


def test_mock_returns_fixed_answer():
    output = MockAdapter().run("What is 458 * 923?")
    assert output.answer == "422734"
    assert output.tools_used == ["calculator"]


def test_mock_can_be_told_to_answer_wrongly():
    adapter = MockAdapter(wrong_inputs={"What is 458 * 923?"})
    output = adapter.run("What is 458 * 923?")
    assert output.answer == "wrong answer"
    assert output.tools_used == []


def test_mock_reports_unknown_input_as_error():
    output = MockAdapter().run("something unexpected")
    assert output.error is not None
