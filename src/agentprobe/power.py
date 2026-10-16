from functools import lru_cache
from math import comb

from .stats import fisher_exact_p

ALPHA = 0.05


def _pmf(runs: int, p: float) -> list[float]:
    """Probability of 0..runs passes when each run passes with chance p."""
    return [comb(runs, k) * p**k * (1 - p) ** (runs - k) for k in range(runs + 1)]


@lru_cache(maxsize=None)
def _significant(before_passed: int, after_passed: int, runs: int, alpha: float) -> bool:
    return fisher_exact_p(before_passed, runs, after_passed, runs) < alpha


def _check(p_before: float, p_after: float, runs: int) -> None:
    if not (0.0 <= p_before <= 1.0 and 0.0 <= p_after <= 1.0):
        raise ValueError("pass rates must be between 0 and 1")
    if p_after > p_before:
        raise ValueError("p_after must not be higher than p_before (this measures drops)")
    if runs < 1:
        raise ValueError("runs must be at least 1")


def detection_power(
    p_before: float, p_after: float, runs: int, alpha: float = ALPHA
) -> float:
    """Chance that compare calls a drop WORSE, with `runs` runs on each side.

    p_before and p_after are the true pass rates. With p_after equal to
    p_before this is the false alarm rate. Only a drop in the observed pass
    rate counts, matching how compare labels WORSE.
    """
    _check(p_before, p_after, runs)
    before = _pmf(runs, p_before)
    after = _pmf(runs, p_after)
    total = 0.0
    for x, px in enumerate(before):
        if px < 1e-15:
            continue
        for y, py in enumerate(after):
            if py < 1e-15 or y >= x:
                continue
            if _significant(x, y, runs, alpha):
                total += px * py
    return total


def runs_needed(
    p_before: float,
    p_after: float,
    target_power: float = 0.8,
    alpha: float = ALPHA,
    max_runs: int = 100,
) -> int | None:
    """Smallest runs per side whose power reaches target_power, or None.

    Power is not perfectly smooth in the number of runs, because counts are
    whole numbers. A slightly larger number can occasionally score lower, so
    treat the answer as a minimum, not an exact threshold.
    """
    _check(p_before, p_after, 1)
    if not 0.0 < target_power < 1.0:
        raise ValueError("target_power must be between 0 and 1")
    for runs in range(2, max_runs + 1):
        if detection_power(p_before, p_after, runs, alpha) >= target_power:
            return runs
    return None