from math import comb


def fisher_exact_p(pass_a: int, runs_a: int, pass_b: int, runs_b: int) -> float:
    """Two-sided Fisher exact p-value for two groups of pass/fail counts.

    Small p means the pass rates really differ; large p means the gap could
    easily be chance.
    """
    if runs_a == 0 or runs_b == 0:
        return 1.0
    total_pass = pass_a + pass_b
    total_runs = runs_a + runs_b

    def prob(k: int) -> float:
        return comb(runs_a, k) * comb(runs_b, total_pass - k) / comb(total_runs, total_pass)

    low = max(0, total_pass - runs_b)
    high = min(runs_a, total_pass)
    observed = prob(pass_a)
    # Sum every outcome at least as unlikely as the observed one.
    p = sum(prob(k) for k in range(low, high + 1) if prob(k) <= observed * (1 + 1e-9))
    return min(1.0, p)