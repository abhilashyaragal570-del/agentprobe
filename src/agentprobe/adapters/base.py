from typing import Protocol

from ..schemas import AgentOutput


class AgentAdapter(Protocol):
    """Every target (Nova, SupportOps, Automation Studio) implements this."""

    def run(self, input_text: str) -> AgentOutput:
        """Run the target agent on one input and return its output."""
        ...
