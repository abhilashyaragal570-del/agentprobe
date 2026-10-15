from .schemas import CaseResult, CaseSummary


def summarize_cases(results: list[CaseResult]) -> list[CaseSummary]:
    """Group results by case id (keeping first-seen order) and roll each group up.

    Errored runs are counted separately and left out of pass_rate, flaky and
    average latency, because the agent never got a fair chance on them.
    """
    groups: dict[str, list[CaseResult]] = {}
    for result in results:
        groups.setdefault(result.case_id, []).append(result)

    summaries: list[CaseSummary] = []
    for case_id, group in groups.items():
        scored = [r for r in group if not r.errored]
        passed = sum(1 for r in scored if r.passed)
        latencies = [r.latency_ms for r in scored if r.latency_ms is not None]
        summaries.append(
            CaseSummary(
                case_id=case_id,
                runs=len(group),
                passed=passed,
                errored=len(group) - len(scored),
                pass_rate=passed / len(scored) if scored else 0.0,
                avg_latency_ms=sum(latencies) / len(latencies) if latencies else None,
                flaky=0 < passed < len(scored),
            )
        )
    return summaries