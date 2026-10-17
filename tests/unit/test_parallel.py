import threading
import time

import pytest

from agentprobe.runner import RunAborted, run_suite
from agentprobe.schemas import AgentOutput, TestCase


class CountingAdapter:
    """Thread-safe adapter. Sleeps per input, can be told to always error."""

    def __init__(self, delays=None, error=None):
        self.delays = delays or {}
        self.error = error
        self.calls = 0
        self._lock = threading.Lock()

    def run(self, text):
        with self._lock:
            self.calls += 1
        time.sleep(self.delays.get(text, 0))
        if self.error:
            return AgentOutput(error=self.error)
        return AgentOutput(answer=text)


class BarrierAdapter:
    """Only succeeds if two calls are running at the same time."""

    def __init__(self):
        self.barrier = threading.Barrier(2, timeout=3)

    def run(self, text):
        try:
            self.barrier.wait()
        except threading.BrokenBarrierError:
            return AgentOutput(error="calls did not overlap")
        return AgentOutput(answer=text)


def cases(*ids):
    return [TestCase(id=i, input=i) for i in ids]


def test_results_stay_in_case_order_when_calls_finish_out_of_order():
    adapter = CountingAdapter(delays={"a": 0.15})
    results = run_suite(adapter, cases("a", "b", "c"), repeats=2, workers=4)
    assert [r.case_id for r in results] == ["a", "a", "b", "b", "c", "c"]


def test_one_worker_runs_every_call_once():
    adapter = CountingAdapter()
    results = run_suite(adapter, cases("a", "b"), repeats=3, workers=1)
    assert len(results) == 6
    assert adapter.calls == 6
    assert [r.case_id for r in results] == ["a", "a", "a", "b", "b", "b"]


def test_parallel_runs_every_call_once():
    adapter = CountingAdapter()
    results = run_suite(adapter, cases("a", "b"), repeats=5, workers=3)
    assert len(results) == 10
    assert adapter.calls == 10
    assert not any(r.errored for r in results)


def test_calls_really_overlap_with_two_workers():
    results = run_suite(BarrierAdapter(), cases("a", "b"), repeats=1, workers=2)
    assert not any(r.errored for r in results)
    assert all(r.passed is not None for r in results)


def test_parallel_run_aborts_after_errors_in_a_row():
    adapter = CountingAdapter(delays={"a": 0.05}, error="error 429")
    with pytest.raises(RunAborted) as info:
        run_suite(
            adapter, cases("a"), repeats=30, workers=2, abort_after_errors=3
        )
    assert len(info.value.results) >= 3
    assert adapter.calls < 30


def test_parallel_abort_is_off_by_default():
    adapter = CountingAdapter(error="boom")
    results = run_suite(adapter, cases("a"), repeats=6, workers=2)
    assert len(results) == 6
    assert all(r.errored for r in results)


def test_workers_below_one_is_rejected():
    with pytest.raises(ValueError):
        run_suite(CountingAdapter(), cases("a"), workers=0)


def test_pause_applies_per_worker_not_across_workers():
    # 4 calls on 2 workers: each worker pauses once, so about 0.3s, not 0.9s.
    start = time.perf_counter()
    run_suite(CountingAdapter(), cases("a"), repeats=4, workers=2, pause_s=0.3)
    elapsed = time.perf_counter() - start
    assert elapsed < 0.8