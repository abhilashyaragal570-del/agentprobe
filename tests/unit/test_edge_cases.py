import time

from agentprobe.adapters.mock import MockAdapter
from agentprobe.dataset import load_cases
from agentprobe.runner import run_case, run_suite
from agentprobe.schemas import TestCase

import pytest


class SlowAdapter:
    def run(self, input_text):
        time.sleep(0.5)
        return MockAdapter().run(input_text)


class NoneAdapter:
    def run(self, input_text):
        return None


class DictAdapter:
    def run(self, input_text):
        return {"answer": "422734"}


class FlakyAdapter:
    def run(self, input_text):
        if input_text == "bad":
            raise RuntimeError("boom")
        return MockAdapter().run(input_text)


def test_slow_adapter_times_out():
    case = TestCase(id="a", input="What is 458 * 923?")
    result = run_case(SlowAdapter(), case, timeout_s=0.05)
    assert result.passed is False
    assert "timeout" in result.error
    assert result.failure_reasons


def test_fast_adapter_within_timeout_is_scored_normally():
    case = TestCase(
        id="a",
        input="What is 458 * 923?",
        expected_answer="422734",
        expected_tools=["calculator"],
    )
    result = run_case(MockAdapter(), case, timeout_s=2.0)
    assert result.passed is True


@pytest.mark.parametrize("adapter", [NoneAdapter(), DictAdapter()])
def test_invalid_output_type_is_recorded(adapter):
    result = run_case(adapter, TestCase(id="a", input="x"))
    assert result.passed is False
    assert "invalid output" in result.error


def test_suite_continues_after_a_crash():
    cases = [
        TestCase(id="a", input="bad"),
        TestCase(id="b", input="Say hello in one short sentence.", expected_answer="Hello!"),
    ]
    results = run_suite(FlakyAdapter(), cases)
    assert results[0].passed is False
    assert "boom" in results[0].error
    assert results[1].passed is True


def test_malformed_json_line_reports_line_number(tmp_path):
    file = tmp_path / "bad.jsonl"
    file.write_text('{"id":"a","input":"x"}\n{"id": \n', encoding="utf-8")
    with pytest.raises(ValueError, match="line 2"):
        load_cases(file)


def test_blank_lines_are_skipped(tmp_path):
    file = tmp_path / "ok.jsonl"
    file.write_text('{"id":"a","input":"x"}\n\n\n{"id":"b","input":"y"}\n', encoding="utf-8")
    assert [c.id for c in load_cases(file)] == ["a", "b"]


def test_empty_file_gives_no_cases(tmp_path):
    file = tmp_path / "empty.jsonl"
    file.write_text("", encoding="utf-8")
    assert load_cases(file) == []
