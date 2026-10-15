import time

from agentprobe.adapters.mock import MockAdapter
from agentprobe.runner import run_suite
from agentprobe.schemas import TestCase


def test_pause_is_not_counted_in_latency():
    cases = [TestCase(id="a", input="x")]
    start = time.perf_counter()
    results = run_suite(MockAdapter(), cases, repeats=3, pause_s=0.2)
    total = time.perf_counter() - start
    assert total >= 0.4  # two pauses happened
    assert all(r.latency_ms < 100 for r in results)


def test_no_pause_before_the_first_call():
    start = time.perf_counter()
    run_suite(MockAdapter(), [TestCase(id="a", input="x")], repeats=1, pause_s=1.0)
    assert time.perf_counter() - start < 0.5