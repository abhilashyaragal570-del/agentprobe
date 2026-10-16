import pytest

from agentprobe.power import detection_power, runs_needed


def test_power_is_zero_when_even_the_biggest_gap_is_not_significant():
    # 3/3 against 0/3 gives p = 0.10, so compare would say NOISE.
    assert detection_power(1.0, 0.0, 3) == 0.0


def test_power_is_full_for_a_total_drop_with_enough_runs():
    # 5/5 against 0/5 gives p of about 0.008.
    assert detection_power(1.0, 0.0, 5) == pytest.approx(1.0)


def test_runs_needed_for_a_total_drop():
    assert runs_needed(1.0, 0.0) == 4


def test_false_alarm_rate_stays_under_alpha():
    assert detection_power(0.8, 0.8, 10) < 0.05


def test_a_small_drop_is_rarely_caught_with_ten_runs():
    assert detection_power(1.0, 0.8, 10) < 0.2


def test_more_runs_catch_a_small_drop_more_often():
    assert detection_power(1.0, 0.8, 40) > detection_power(1.0, 0.8, 10)


def test_runs_needed_gives_up_when_max_runs_is_too_small():
    assert runs_needed(1.0, 0.9, max_runs=5) is None


def test_bad_input_is_rejected():
    with pytest.raises(ValueError):
        detection_power(1.2, 0.5, 10)
    with pytest.raises(ValueError):
        detection_power(0.5, 0.8, 10)  # an improvement, not a drop
    with pytest.raises(ValueError):
        detection_power(0.9, 0.5, 0)