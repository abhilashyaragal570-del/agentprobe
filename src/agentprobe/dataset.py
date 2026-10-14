import json
from pathlib import Path

from .schemas import TestCase


def load_cases(path) -> list[TestCase]:
    cases: list[TestCase] = []
    seen: set[str] = set()
    lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            case = TestCase(**json.loads(line))
        except ValueError as error:  # bad JSON or failed validation
            raise ValueError(f"{path} line {number}: {error}") from error
        if case.id in seen:
            raise ValueError(f"{path} line {number}: duplicate id '{case.id}'")
        seen.add(case.id)
        cases.append(case)
    return cases

