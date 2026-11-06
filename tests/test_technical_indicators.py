import math

import pytest

from backend.benchmark import technical_indicators as ti


def test_sma_is_the_plain_mean_of_the_window_and_none_before_it():
    result = ti.technical_indicators_sma([1, 2, 3, 4, 5], 3)
    assert result == [None, None, 2, 3, 4]


def test_ema_is_seeded_with_the_first_value_and_uses_two_over_n_plus_one():
    result = ti.technical_indicators_ema([1, 2, 3], 2)
    assert result[0] == 1
    assert result[1] == pytest.approx(2 * (2 / 3) + 1 * (1 / 3))
    assert result[2] == pytest.approx(3 * (2 / 3) + result[1] * (1 / 3))


def test_rsi_is_100_when_only_gains_and_0_when_only_losses():
    rising = [float(value) for value in range(1, 30)]
    falling = [float(value) for value in range(30, 1, -1)]
    assert ti.technical_indicators_rsi(rising)[-1] == pytest.approx(100)
    assert ti.technical_indicators_rsi(falling)[-1] == pytest.approx(0)


def test_rsi_first_value_is_the_plain_mean_of_the_first_fourteen_moves_then_wilder_smoothing():
    closes = [44, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28, 46.00, 46.03]
    moves = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gain = sum(max(m, 0) for m in moves[:14]) / 14
    loss = sum(max(-m, 0) for m in moves[:14]) / 14
    result = ti.technical_indicators_rsi(closes)
    assert result[:14] == [None] * 14
    assert result[14] == pytest.approx(100 - 100 / (1 + gain / loss))
    gain = (gain * 13 + max(moves[14], 0)) / 14
    loss = (loss * 13 + max(-moves[14], 0)) / 14
    assert result[15] == pytest.approx(100 - 100 / (1 + gain / loss))


def test_macd_histogram_is_line_minus_signal_with_no_gaps():
    closes = [100 + math.sin(index / 3) * 5 for index in range(60)]
    macd = ti.technical_indicators_macd(closes)
    assert len(macd["histogram"]) == 60
    assert macd["histogram"][-1] == pytest.approx(macd["macd"][-1] - macd["signal"][-1])


def test_bollinger_percent_b_is_75_one_standard_deviation_above_the_middle():
    closes = [9.0, 11.0] * 10  # middle 10, population deviation 1: bands at 8 and 12; the last close 11 sits at 75%
    bands = ti.technical_indicators_bollinger(closes)
    assert bands["middle"][-1] == pytest.approx(10)
    assert bands["percent_b"][-1] == pytest.approx(75)
    breakout = ti.technical_indicators_bollinger([10.0] * 19 + [12.0])
    assert breakout["percent_b"][-1] > 100  # above the upper band
    flat = ti.technical_indicators_bollinger([10.0] * 25)
    assert flat["percent_b"][-1] is None  # no width, so %B is undefined


def test_bollinger_middle_and_width_use_the_population_standard_deviation():
    window = [float(v) for v in range(1, 21)]
    bands = ti.technical_indicators_bollinger(window)
    middle = sum(window) / 20
    deviation = math.sqrt(sum((v - middle) ** 2 for v in window) / 20)
    assert bands["middle"][-1] == pytest.approx(middle)
    assert bands["upper"][-1] == pytest.approx(middle + 2 * deviation)
    assert bands["lower"][-1] == pytest.approx(middle - 2 * deviation)


def test_volume_ratio_compares_today_with_the_days_before_not_including_today():
    volumes = [100.0] * 30 + [300.0]
    result = ti.technical_indicators_volume_ratio(volumes)
    assert result[29] is None
    assert result[30] == pytest.approx(3.0)
