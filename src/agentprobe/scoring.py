import re

from .schemas import AgentOutput, TestCase


def exact_match(actual: str, expected: str) -> bool:
    return actual.strip() == expected.strip()


def contains_match(actual: str, expected: str) -> bool:
    """True if expected appears as a standalone value in actual.

    Commas inside numbers are ignored (422,734 equals 422734), and "50"
    does not match inside "500".
    """
    text = re.sub(r"(?<=\d),(?=\d)", "", actual).lower()
    wanted = re.sub(r"(?<=\d),(?=\d)", "", expected).strip().lower()
    if not wanted:
        return False
    pattern = r"(?<![\w.])" + re.escape(wanted) + r"(?![\w])"
    return re.search(pattern, text) is not None


def answer_matches(case: TestCase, actual: str) -> bool:
    if case.answer_match == "contains":
        return contains_match(actual, case.expected_answer)
    return exact_match(actual, case.expected_answer)


def score_case(case: TestCase, output: AgentOutput) -> list[str]:
    """Return a list of failure reasons. An empty list means the case passed."""
    reasons: list[str] = []

    if output.error:
        reasons.append(f"adapter error: {output.error}")
    elif not output.answer.strip():
        # The call finished without an error but said nothing, for example a
        # stalled call. Report it first so it is not mistaken for a tool problem.
        reasons.append("empty answer")

    if case.expected_answer is not None and not answer_matches(case, output.answer):
        reasons.append(
            f"wrong answer ({case.answer_match}): expected '{case.expected_answer}', "
            f"got '{output.answer}'"
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