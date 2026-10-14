import time

from .adapters.base import AgentAdapter
from .schemas import AgentOutput, CaseResult, TestCase
from .scoring import score_case


def run_case(adapter: AgentAdapter, case: TestCase) -> CaseResult:
    """Run one test case through an adapter, then score it."""
    start = time.perf_counter()
    try:
        output = adapter.run(case.input)
    except Exception as error:  # one bad case must not stop the whole run
        output = AgentOutput(error=f"{type(error).__name__}: {error}")
    latency_ms = (time.perf_counter() - start) * 1000

    reasons = score_case(case, output)
    return CaseResult(
        case_id=case.id,
        passed=not reasons,
        answer=output.answer,
        tools_used=output.tools_used,
        latency_ms=latency_ms,
        failure_reasons=reasons,
        error=output.error,
    )


def run_suite(adapter: AgentAdapter, cases: list[TestCase]) -> list[CaseResult]:
    """Run every case, one at a time, and return all results."""
    return [run_case(adapter, case) for case in cases]
