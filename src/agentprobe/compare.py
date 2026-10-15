from dataclasses import dataclass

from .schemas import CaseSummary, RunReport
from .stats import fisher_exact_p

ALPHA = 0.05


@dataclass
class CaseDiff:
    case_id: str
    before: float | None
    after: float | None
    verdict: str  # same, better, worse, noise, new, removed, inconclusive
    p_value: float | None = None
    before_errored: int = 0
    after_errored: int = 0


def _rate(s: CaseSummary) -> float | None:
    """Pass rate over scored runs, or None when every run errored."""
    return s.pass_rate if s.scored > 0 else None


def _verdict(b: CaseSummary, a: CaseSummary) -> tuple[str, float | None]:
    if b.scored == 0 or a.scored == 0:
        return "inconclusive", None  # no usable runs on one side
    if b.passed * a.scored == a.passed * b.scored:  # identical pass rates
        return "same", None
    p = fisher_exact_p(b.passed, b.scored, a.passed, a.scored)
    if p >= ALPHA:
        return "noise", p  # a gap this size is easy to get by chance
    return ("better" if a.pass_rate > b.pass_rate else "worse"), p


def compare_reports(before: RunReport, after: RunReport) -> list[CaseDiff]:
    """Compare per-case results of two reports, in order of first appearance.

    Errored runs are ignored, so a rate limit cannot look like a regression.
    """
    old = {s.case_id: s for s in before.summaries}
    new = {s.case_id: s for s in after.summaries}
    case_ids = list(old) + [c for c in new if c not in old]

    diffs: list[CaseDiff] = []
    for case_id in case_ids:
        b, a = old.get(case_id), new.get(case_id)
        if b is None:
            diffs.append(
                CaseDiff(case_id, None, _rate(a), "new", after_errored=a.errored)
            )
        elif a is None:
            diffs.append(
                CaseDiff(case_id, _rate(b), None, "removed", before_errored=b.errored)
            )
        else:
            verdict, p = _verdict(b, a)
            diffs.append(
                CaseDiff(
                    case_id,
                    _rate(b),
                    _rate(a),
                    verdict,
                    p,
                    before_errored=b.errored,
                    after_errored=a.errored,
                )
            )
    return diffs