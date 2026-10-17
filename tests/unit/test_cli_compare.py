import pytest

from agentprobe.cli.compare import main


def test_help_exits_cleanly(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    assert "Compare two AgentProbe reports" in capsys.readouterr().out