from typing import Literal

from pydantic import BaseModel, Field


class TestCase(BaseModel):
    __test__ = False
    id: str
    input: str
    expected_answer: str | None = None
    answer_match: Literal["exact", "contains"] = "exact"
    expected_tools: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class AgentOutput(BaseModel):
    """What an adapter returns after running one test input."""

    answer: str = ""
    tools_used: list[str] = Field(default_factory=list)
    error: str | None = None


class CaseResult(BaseModel):
    """The scored outcome of one test case."""

    case_id: str
    passed: bool
    answer: str = ""
    tools_used: list[str] = Field(default_factory=list)
    latency_ms: float | None = None
    failure_reasons: list[str] = Field(default_factory=list)
    error: str | None = None
    # True when the run ended in an adapter error (rate limit, timeout,
    # connection problem). The agent never got a fair chance, so the run is
    # left out of pass rates and comparisons.
    errored: bool = False


class CaseSummary(BaseModel):
    """All repeated runs of one test case, rolled up.

    runs counts every run. pass_rate and flaky only look at the scored runs,
    which are the runs that did not error.
    """

    case_id: str
    runs: int
    passed: int
    pass_rate: float
    avg_latency_ms: float | None = None
    flaky: bool = False
    errored: int = 0

    @property
    def scored(self) -> int:
        return self.runs - self.errored


class RunReport(BaseModel):
    """One complete evaluation run: summary plus every case result."""

    run_id: str
    started_at: str
    dataset: str
    adapter: str
    total: int
    passed: int
    pass_rate: float
    results: list[CaseResult]
    repeats: int = 1
    summaries: list[CaseSummary] = Field(default_factory=list)
    # Settings of the agent under test, e.g. {"prompt": "pirate"}.
    # Empty for reports saved before this field existed.
    agent_config: dict[str, str] = Field(default_factory=dict)
    # Number of runs that errored and are not counted in pass_rate.
    errored: int = 0