from ..schemas import AgentOutput


class MockAdapter:
    """A fake agent with fixed answers, for building and testing offline."""

    def __init__(self, wrong_inputs: set[str] | None = None):
        self.wrong_inputs = wrong_inputs or set()
        self._canned = {
            "What is 458 * 923?": AgentOutput(
                answer="422734", tools_used=["calculator"]
            ),
            "Use the calculator to find 10% of 500.": AgentOutput(
                answer="50", tools_used=["calculator"]
            ),
            "Say hello in one short sentence.": AgentOutput(
                answer="Hello!", tools_used=[]
            ),
        }

    def run(self, input_text: str) -> AgentOutput:
        if input_text in self.wrong_inputs:
            return AgentOutput(answer="wrong answer", tools_used=[])
        if input_text not in self._canned:
            return AgentOutput(error=f"mock has no answer for: {input_text}")
        return self._canned[input_text]
