from pydantic import BaseModel, Field


class TestCase(BaseModel):
    id: str
    input: str
    expected_answer: str | None = None
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
