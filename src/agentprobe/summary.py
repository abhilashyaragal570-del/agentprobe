from .schemas import CaseResult, CaseSummary


def summarize_cases(results: list[CaseResult]) -> list[CaseSummary]:
    """Group results by case id (keeping first-seen order) and roll each group up."""
    groups: dict[str, list[CaseResult]] = {}
    for result in results:
        groups.setdefault(result.case_id, []).append(result)

    summaries: list[CaseSummary] = []
    for case_id, group in groups.items():
        passed = sum(1 for r in group if r.passed)
        latencies = [r.latency_ms for r in group if r.latency_ms is not None]
        summaries.append(
            CaseSummary(
                case_id=case_id,
                runs=len(group),
                passed=passed,
                pass_rate=passed / len(group),
                avg_latency_ms=sum(latencies) / len(latencies) if latencies else None,
                flaky=0 < passed < len(group),
            )
        )
    return summaries