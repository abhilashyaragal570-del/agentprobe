from pydantic import BaseModel, Field


class TestCase(BaseModel):
    id: str
    input: str
    expected_answer: str | None = None
    expected_tools: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
