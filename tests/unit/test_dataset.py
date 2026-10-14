from pathlib import Path

import pytest

from agentprobe.dataset import load_cases

ROOT = Path(__file__).resolve().parents[2]


def test_nova_dataset_loads():
    cases = load_cases(ROOT / "datasets" / "nova_tools.jsonl")
    assert len(cases) == 3
    assert cases[0].id == "calc-001"


def test_duplicate_ids_rejected(tmp_path):
    file = tmp_path / "bad.jsonl"
    file.write_text(
        '{"id":"a","input":"x"}\n{"id":"a","input":"y"}\n', encoding="utf-8"
    )
    with pytest.raises(ValueError, match="duplicate"):
        load_cases(file)


def test_malformed_line_gives_clear_error(tmp_path):
    file = tmp_path / "bad.jsonl"
    file.write_text('{"id":"a"}\n', encoding="utf-8")  # missing "input"
    with pytest.raises(ValueError, match="line 1"):
        load_cases(file)
