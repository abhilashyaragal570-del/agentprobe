import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures import TimeoutError as FuturesTimeout

from .adapters.base import AgentAdapter
from .schemas import AgentOutput, CaseResult, TestCase
from .scoring import score_case


class RunAborted(Exception):
    """Raised when too many runs in a row errored, so the target is probably
    down or rate limited. The runs finished so far are in .results."""

    def __init__(self, message: str, results: list[CaseResult]):
        super().__init__(message)
        self.results = results


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
        errored=bool(output.error),
    )


def _abort(streak: int, last: CaseResult, results: list[CaseResult]) -> RunAborted:
    return RunAborted(
        f"{streak} errored runs in a row. Last error: {(last.error or '')[:200]}",
        results,
    )


def _run_sequential(
    adapter: AgentAdapter,
    cases: list[TestCase],
    timeout_s: float | None,
    repeats: int,
    pause_s: float,
    abort_after_errors: int,
) -> list[CaseResult]:
    results: list[CaseResult] = []
    streak = 0
    for case in cases:
        for _ in range(repeats):
            if results and pause_s > 0:
                time.sleep(pause_s)
            result = run_case(adapter, case, timeout_s)
            results.append(result)
            streak = streak + 1 if result.errored else 0
            if abort_after_errors and streak >= abort_after_errors:
                raise _abort(streak, result, results)
    return results


def _run_parallel(
    adapter: AgentAdapter,
    cases: list[TestCase],
    timeout_s: float | None,
    repeats: int,
    pause_s: float,
    abort_after_errors: int,
    workers: int,
) -> list[CaseResult]:
    jobs = [case for case in cases for _ in range(repeats)]
    local = threading.local()

    def work(case: TestCase) -> CaseResult:
        # Each worker pauses between its own calls, not before its first.
        if pause_s > 0 and getattr(local, "started", False):
            time.sleep(pause_s)
        local.started = True
        return run_case(adapter, case, timeout_s)

    executor = ThreadPoolExecutor(max_workers=workers)
    futures = {executor.submit(work, case): index for index, case in enumerate(jobs)}
    done: dict[int, CaseResult] = {}
    streak = 0
    try:
        for future in as_completed(futures):
            result = future.result()  # run_case never raises
            done[futures[future]] = result
            streak = streak + 1 if result.errored else 0
            if abort_after_errors and streak >= abort_after_errors:
                executor.shutdown(wait=False, cancel_futures=True)
                raise _abort(streak, result, [done[i] for i in sorted(done)])
    finally:
        executor.shutdown(wait=False)
    return [done[i] for i in sorted(done)]


def run_suite(
    adapter: AgentAdapter,
    cases: list[TestCase],
    timeout_s: float | None = None,
    repeats: int = 1,
    pause_s: float = 0.0,
    abort_after_errors: int = 0,
    workers: int = 1,
) -> list[CaseResult]:
    """Run every case `repeats` times. Results are grouped by case, in case order.

    pause_s waits between calls (not before the first) and is not counted in latency.
    abort_after_errors stops the run with RunAborted once that many errored runs
    happen in a row. 0 turns this off.
    workers runs that many calls at once. 1 (the default) is fully sequential.
    With more than one worker the pause applies per worker, and "in a row" is
    counted in the order the calls finish.
    """
    if repeats < 1:
        raise ValueError("repeats must be at least 1")
    if workers < 1:
        raise ValueError("workers must be at least 1")
    if workers == 1:
        return _run_sequential(
            adapter, cases, timeout_s, repeats, pause_s, abort_after_errors
        )
    return _run_parallel(
        adapter, cases, timeout_s, repeats, pause_s, abort_after_errors, workers
    )