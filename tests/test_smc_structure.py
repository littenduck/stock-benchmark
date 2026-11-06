from backend.benchmark import smc_structure as smc


def _v_shape():
    # Falls to 80 then rises: a swing low at index 6 and a swing high at index 12 (both with 3 bars either side).
    closes = [100, 98, 96, 94, 92, 90, 80, 90, 92, 94, 96, 98, 104, 98, 96, 94, 92, 90, 88]
    return closes, [c + 1 for c in closes], [c - 1 for c in closes]


def test_swings_need_bars_on_both_sides_and_are_found_at_the_extremes():
    closes, highs, lows = _v_shape()
    swings = smc.smc_structure_find_swings(highs, lows)
    assert [s["index"] for s in swings["lows"]] == [6]
    assert [s["index"] for s in swings["highs"]] == [12]


def test_bos_up_when_a_close_breaks_the_last_swing_high_in_an_uptrend():
    closes, highs, lows = _v_shape()
    closes = closes + [106]
    highs, lows = [c + 1 for c in closes], [c - 1 for c in closes]
    opens = closes[:]
    swings = smc.smc_structure_find_swings(highs, lows)
    events = smc.smc_structure_find_breaks(opens, highs, lows, closes, swings)
    up_events = [e for e in events if e["direction"] == "up"]
    assert up_events, "a close above the swing high at 105 should break it"
    assert up_events[0]["kind"] == "BOS"
    assert up_events[0]["level_index"] == 12


def test_choch_is_the_first_break_against_the_trend():
    closes = [100, 98, 96, 94, 92, 90, 80, 90, 92, 94, 96, 98, 104, 98, 96, 94, 92, 90, 88, 106, 60]
    highs = [c + 1 for c in closes]
    lows = [c - 1 for c in closes]
    opens = closes[:]
    swings = smc.smc_structure_find_swings(highs, lows)
    events = smc.smc_structure_find_breaks(opens, highs, lows, closes, swings)
    assert [e["kind"] for e in events][:2] == ["BOS", "CHoCH"]
    assert events[1]["direction"] == "down"


def test_fair_value_gap_is_the_space_between_bar_one_and_bar_three():
    highs = [10, 11, 15, 16]
    lows = [9, 10, 13, 14]
    closes = [10, 11, 14, 15]
    gaps = smc.smc_structure_find_fair_value_gaps(highs, lows, closes)
    assert gaps[0]["direction"] == "up"
    assert (gaps[0]["low"], gaps[0]["high"]) == (10, 13)  # from the high of the first bar to the low of the third
    assert gaps[0]["mitigated_index"] is None


def test_fair_value_gap_is_marked_mitigated_when_price_trades_back_in():
    highs = [10, 11, 15, 16, 12]
    lows = [9, 10, 13, 14, 11]
    closes = [10, 11, 14, 15, 12]
    gaps = smc.smc_structure_find_fair_value_gaps(highs, lows, closes)
    assert gaps[0]["mitigated_index"] == 4


def test_equal_highs_within_tolerance_are_reported_and_far_apart_ones_are_not():
    swings = {"highs": [{"index": 3, "price": 100.0}, {"index": 9, "price": 100.1}, {"index": 15, "price": 120.0}], "lows": []}
    equal = smc.smc_structure_find_equal_levels(swings)
    assert [e["kind"] for e in equal] == ["EQH"]
    assert (equal[0]["first_index"], equal[0]["second_index"]) == (3, 9)


def test_sweep_is_a_bar_that_trades_above_a_swing_high_and_closes_back_below_it():
    highs = [10, 11, 12, 14, 11, 10, 9, 15, 11, 10]
    lows = [h - 2 for h in highs]
    closes = [h - 1 for h in highs]
    closes[7] = 12  # bar 7 trades to 15, above the swing high of 14 at bar 3, but closes at 12
    swings = smc.smc_structure_find_swings(highs, lows)
    sweeps = smc.smc_structure_find_sweeps(highs, lows, closes, swings)
    high_sweeps = [sweep for sweep in sweeps if sweep["side"] == "high"]
    assert [(sweep["index"], sweep["price"]) for sweep in high_sweeps] == [(7, 14)]


def test_no_look_ahead_in_swings_when_bars_after_are_missing():
    highs = [1, 2, 3, 4, 9]
    lows = [0, 1, 2, 3, 8]
    assert smc.smc_structure_find_swings(highs, lows) == {"highs": [], "lows": []}


def test_analyse_returns_all_parts_for_a_short_series():
    closes = [100.0 + (i % 5) for i in range(40)]
    result = smc.smc_structure_analyse(closes, [c + 1 for c in closes], [c - 1 for c in closes], closes)
    assert set(result) == {"swings", "events", "fair_value_gaps", "equal_levels", "sweeps"}
