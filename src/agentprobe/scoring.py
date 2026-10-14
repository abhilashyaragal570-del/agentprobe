from .schemas import AgentOutput, TestCase


def exact_match(actual: str, expected: str) -> bool:
    return actual.strip() == expected.strip()


def score_case(case: TestCase, output: AgentOutput) -> list[str]:
    """Return a list of failure reasons. An empty list means the case passed."""
    reasons: list[str] = []

    if output.error:
        reasons.append(f"adapter error: {output.error}")

    if case.expected_answer is not None and not exact_match(
        output.answer, case.expected_answer
    ):
        reasons.append(
            f"wrong answer: expected '{case.expected_answer}', got '{output.answer}'"
        )

    if sorted(output.tools_used) != sorted(case.expected_tools):
        reasons.append(
            f"wrong tools: expected {case.expected_tools}, got {output.tools_used}"
        )

    return reasons


def pass_rate(results) -> float:
    if not results:
        return 0.0
    return sum(1 for r in results if r.passed) / len(results)
