import time

from .adapters.base import AgentAdapter
from .schemas import AgentOutput, CaseResult, TestCase


def run_case(adapter: AgentAdapter, case: TestCase) -> CaseResult:
    """Run one test case through an adapter and record the raw outcome."""
    start = time.perf_counter()
    try:
        output = adapter.run(case.input)
    except Exception as error:  # one bad case must not stop the whole run
        output = AgentOutput(error=f"{type(error).__name__}: {error}")
    latency_ms = (time.perf_counter() - start) * 1000

    return CaseResult(
        case_id=case.id,
        passed=False,  # real scoring arrives in Step 12
        answer=output.answer,
        tools_used=output.tools_used,
        latency_ms=latency_ms,
        failure_reasons=["not scored yet"],
        error=output.error,
    )


def run_suite(adapter: AgentAdapter, cases: list[TestCase]) -> list[CaseResult]:
    """Run every case, one at a time, and return all results."""
    return [run_case(adapter, case) for case in cases]
