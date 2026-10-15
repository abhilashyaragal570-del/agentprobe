import json

import pytest

from agentprobe.configdiff import config_differences, parse_config_pairs
from agentprobe.schemas import CaseResult
from agentprobe.storage import build_report, load_report, save_report


def _results():
    return [CaseResult(case_id="a", passed=True), CaseResult(case_id="b", passed=False)]


def test_parse_pairs():
    assert parse_config_pairs(["prompt=pirate", "model = x=y"]) == {
        "prompt": "pirate",
        "model": "x=y",
    }


def test_parse_empty():
    assert parse_config_pairs(None) == {}
    assert parse_config_pairs([]) == {}


@pytest.mark.parametrize("bad", ["novalue", "=x", ""])
def test_parse_rejects_bad_pairs(bad):
    with pytest.raises(ValueError):
        parse_config_pairs([bad])


def test_no_differences():
    assert config_differences({"a": "1"}, {"a": "1"}) == {}
    assert config_differences({}, {}) == {}


def test_differences_changed_added_removed():
    diffs = config_differences({"a": "1", "b": "2"}, {"a": "9", "c": "3"})
    assert diffs == {"a": ("1", "9"), "b": ("2", None), "c": (None, "3")}


def test_config_saved_and_loaded(tmp_path):
    report = build_report("ds", "ad", _results(), agent_config={"prompt": "pirate"})
    path = save_report(report, tmp_path)
    assert load_report(path).agent_config == {"prompt": "pirate"}


def test_config_defaults_to_empty():
    assert build_report("ds", "ad", _results()).agent_config == {}


def test_old_report_without_config_still_loads(tmp_path):
    data = build_report("ds", "ad", _results()).model_dump()
    del data["agent_config"]
    path = tmp_path / "old.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert load_report(path).agent_config == {}