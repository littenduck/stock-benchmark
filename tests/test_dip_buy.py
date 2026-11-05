import pytest

from stock_benchmark_backend import dip_buy


@pytest.mark.parametrize("rsi, points", [(29.9, 25), (30, 15), (34.99, 15), (35, 8), (45, 8), (45.1, 0)])
def test_rsi_points_follow_the_spec_bands(rsi, points):
    assert dip_buy.dip_buy_rsi_points(rsi) == points


@pytest.mark.parametrize("percent_b, points", [(-5, 20), (9.9, 20), (10, 12), (24.9, 12), (25, 6), (50, 6), (50.1, 0)])
def test_percent_b_points_follow_the_spec_bands(percent_b, points):
    assert dip_buy.dip_buy_percent_b_points(percent_b) == points


@pytest.mark.parametrize("histogram, state, points", [
    ([-1.0, 0.5], "turned_positive", 25),
    ([-2.0, -1.0], "negative_shrinking", 15),
    ([-1.0, -2.0], "negative_expanding", 0),
    ([1.0, 2.0], "positive", 0),
])
def test_macd_state_and_points(histogram, state, points):
    assert dip_buy.dip_buy_macd_state(histogram) == state
    assert dip_buy.dip_buy_macd_points(state) == points


@pytest.mark.parametrize("score, verdict", [(80, "buy"), (100, "buy"), (79, "wait"), (50, "wait"), (49, "no"), (0, "no")])
def test_verdict_thresholds(score, verdict):
    assert dip_buy.dip_buy_verdict(score) == verdict


def _evaluate(rsi, percent_b, histogram, close=100.0, volume_ratio=1.0, eps=None, earnings_known=True, pe=None):
    count = len(histogram)
    closes = [close] * (count - 1) + [close]
    return dip_buy.dip_buy_evaluate(
        closes=closes, volumes=[1.0] * count, rsi_list=[None] * (count - 1) + [rsi],
        percent_b_list=[None] * (count - 1) + [percent_b], macd_histogram_list=histogram,
        sma20_list=[close * 0.9] * count, sma50_list=[close * 1.1] * count, sma200_list=[close] * count,
        volume_ratio_list=[None] * (count - 1) + [volume_ratio], pe=pe, earnings_known=earnings_known,
        pe_has_single_match=True)


def test_amd_on_2026_11_02_scores_50_as_checked_by_hand():
    result = _evaluate(rsi=34.6, percent_b=-0.66, histogram=[-4.4, -8.75], close=110.0, volume_ratio=1.53)
    assert result["rsi_points"] == 15 and result["percent_b_points"] == 20 and result["macd_points"] == 0
    assert result["raw_points"] == 35 and result["score"] == 50 and result["verdict"] == "wait"


def test_a_full_turn_scores_80_or_more():
    result = _evaluate(rsi=28, percent_b=5, histogram=[-0.5, 0.2])
    assert result["raw_points"] == 25 + 20 + 25 and result["score"] == 100 and result["verdict"] == "buy"


def test_lights_and_counts_leave_out_sma200_and_count_seven_items():
    result = _evaluate(rsi=40, percent_b=30, histogram=[-1.0, -2.0], close=100.0, volume_ratio=0.5, pe=20.0)
    assert result["lights"]["rsi"] == "yellow" and result["lights"]["percent_b"] == "yellow"
    assert result["lights"]["macd"] == "red" and result["lights"]["pe"] == "yellow"
    assert result["lights"]["sma20"] == "green" and result["lights"]["sma50"] == "red"
    assert result["lights"]["volume"] == "yellow"  # unchanged close with light volume is neutral
    assert sum(result["counts"].values()) == 7
    assert result["sma200_light"] == "green"


def test_loss_making_stock_has_grey_pe_and_is_not_counted_as_red_or_green():
    result = _evaluate(rsi=40, percent_b=30, histogram=[-1.0, -2.0], earnings_known=True, pe=None)
    assert result["lights"]["pe"] == "grey"
    assert sum(result["counts"].values()) == 6


def test_no_single_match_shows_white_pe():
    result = _evaluate(rsi=40, percent_b=30, histogram=[-1.0, -2.0], earnings_known=False, pe=None)
    assert result["lights"]["pe"] == "white"


def test_volume_light_rules():
    assert dip_buy._light_for_volume(1.5, -1) == "red"
    assert dip_buy._light_for_volume(0.8, -1) == "green"
    assert dip_buy._light_for_volume(1.5, 1) == "green"
    assert dip_buy._light_for_volume(0.8, 1) == "yellow"
