import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout

from .adapters.base import AgentAdapter
from .schemas import AgentOutput, CaseResult, TestCase
from .scoring import score_case


def _call_adapter(adapter: AgentAdapter, text: str, timeout_s: float | None):
    if timeout_s is None:
        return adapter.run(text)
    executor = ThreadPoolExecutor(max_workers=1)
    try:
        return executor.submit(adapter.run, text).result(timeout=timeout_s)
    finally:
        executor.shutdown(wait=False)  # do not wait for a hung adapter


def run_case(
    adapter: AgentAdapter, case: TestCase, timeout_s: float | None = None
) -> CaseResult:
    """Run one test case through an adapter, then score it."""
    start = time.perf_counter()
    try:
        output = _call_adapter(adapter, case.input, timeout_s)
    except FuturesTimeout:
        output = AgentOutput(error=f"timeout after {timeout_s}s")
    except Exception as error:  # one bad case must not stop the whole run
        output = AgentOutput(error=f"{type(error).__name__}: {error}")
    latency_ms = (time.perf_counter() - start) * 1000

    if not isinstance(output, AgentOutput):
        output = AgentOutput(
            error=f"invalid output: adapter returned {type(output).__name__}"
        )

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


def run_suite(
    adapter: AgentAdapter,
    cases: list[TestCase],
    timeout_s: float | None = None,
    repeats: int = 1,
    pause_s: float = 0.0,
) -> list[CaseResult]:
    """Run every case `repeats` times, one at a time. Results are grouped by case.

    pause_s waits between calls (not before the first) and is not counted in latency.
    """
    if repeats < 1:
        raise ValueError("repeats must be at least 1")
    results: list[CaseResult] = []
    for case in cases:
        for _ in range(repeats):
            if results and pause_s > 0:
                time.sleep(pause_s)
            results.append(run_case(adapter, case, timeout_s))
    return results