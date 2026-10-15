from dataclasses import dataclass

from .schemas import CaseSummary, RunReport
from .stats import fisher_exact_p

ALPHA = 0.05


@dataclass
class CaseDiff:
    case_id: str
    before: float | None
    after: float | None
    verdict: str  # same, better, worse, noise, new, removed
    p_value: float | None = None


def _verdict(b: CaseSummary, a: CaseSummary) -> tuple[str, float | None]:
    if b.passed * a.runs == a.passed * b.runs:  # identical pass rates
        return "same", None
    p = fisher_exact_p(b.passed, b.runs, a.passed, a.runs)
    if p >= ALPHA:
        return "noise", p  # a gap this size is easy to get by chance
    return ("better" if a.pass_rate > b.pass_rate else "worse"), p


def compare_reports(before: RunReport, after: RunReport) -> list[CaseDiff]:
    """Compare per-case results of two reports, in order of first appearance."""
    old = {s.case_id: s for s in before.summaries}
    new = {s.case_id: s for s in after.summaries}
    case_ids = list(old) + [c for c in new if c not in old]

    diffs: list[CaseDiff] = []
    for case_id in case_ids:
        b, a = old.get(case_id), new.get(case_id)
        if b is None:
            diffs.append(CaseDiff(case_id, None, a.pass_rate, "new"))
        elif a is None:
            diffs.append(CaseDiff(case_id, b.pass_rate, None, "removed"))
        else:
            verdict, p = _verdict(b, a)
            diffs.append(CaseDiff(case_id, b.pass_rate, a.pass_rate, verdict, p))
    return diffs