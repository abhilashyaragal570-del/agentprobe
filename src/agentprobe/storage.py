import uuid
from datetime import datetime, timezone
from pathlib import Path

from .schemas import CaseResult, RunReport
from .scoring import pass_rate
from .summary import summarize_cases


def build_report(
    dataset: str,
    adapter_name: str,
    results: list[CaseResult],
    repeats: int = 1,
    agent_config: dict[str, str] | None = None,
) -> RunReport:
    now = datetime.now(timezone.utc)
    return RunReport(
        run_id=now.strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6],
        started_at=now.isoformat(),
        dataset=dataset,
        adapter=adapter_name,
        total=len(results),
        passed=sum(1 for r in results if r.passed),
        pass_rate=pass_rate(results),
        results=results,
        repeats=repeats,
        summaries=summarize_cases(results),
        agent_config=dict(agent_config or {}),
    )


def save_report(report: RunReport, directory) -> Path:
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{report.run_id}.json"
    path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_report(path) -> RunReport:
    text = Path(path).read_text(encoding="utf-8-sig")
    return RunReport.model_validate_json(text)