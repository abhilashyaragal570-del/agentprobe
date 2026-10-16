from pathlib import Path

import pytest

from agentprobe.dataset import load_cases

DATASETS = sorted((Path(__file__).resolve().parents[2] / "datasets").glob("*.jsonl"))


def test_datasets_were_found():
    assert DATASETS, "no .jsonl files found in datasets/"


@pytest.mark.parametrize("path", DATASETS, ids=lambda p: p.name)
def test_dataset_loads_and_has_unique_ids(path):
    cases = load_cases(path)
    assert cases, f"{path.name} has no cases"
    ids = [c.id for c in cases]
    assert len(ids) == len(set(ids)), f"{path.name} has duplicate case ids"


@pytest.mark.parametrize("path", DATASETS, ids=lambda p: p.name)
def test_every_case_has_a_real_input_and_a_usable_expected_answer(path):
    # An empty expected_tools list is valid: it means the agent must use no tools.
    for case in load_cases(path):
        assert case.input.strip(), f"{case.id} has an empty input"
        if case.expected_answer is not None:
            assert case.expected_answer.strip(), f"{case.id} has an empty expected answer"


def test_border_cases_expect_the_calculator():
    path = next(p for p in DATASETS if p.name == "nova_border.jsonl")
    for case in load_cases(path):
        assert case.expected_tools == ["calculator"]
        assert case.answer_match == "contains"