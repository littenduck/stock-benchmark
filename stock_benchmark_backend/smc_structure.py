"""Smart-money structure from daily bars, by plain rules (no prediction).

A swing high (low) is a bar whose high (low) is the highest (lowest) of the bars SWING_BARS before and after it. It is only known
SWING_BARS bars later, so nothing here looks at a bar that had not closed yet. From the swings we find:
- BOS (break of structure): a close beyond the last swing in the trend direction;
- CHoCH (change of character): a close beyond the last swing against the trend, the first sign of a reversal;
- order blocks: the last opposite candle before the break that caused it;
- fair value gaps: a three-bar gap that the middle bar leaves open;
- equal highs and equal lows: two swings at nearly the same price;
- liquidity sweeps: a bar that trades beyond a swing but closes back inside it.
"""
from typing import List

SWING_BARS = 3
EQUAL_LEVEL_TOLERANCE_RATIO = 0.002


def smc_structure_find_swings(highs: List[float], lows: List[float]) -> dict:
    swing_high_list, swing_low_list = [], []
    for index in range(SWING_BARS, len(highs) - SWING_BARS):
        before_high = highs[index - SWING_BARS:index]
        after_high = highs[index + 1:index + SWING_BARS + 1]
        if highs[index] > max(before_high) and highs[index] >= max(after_high):
            swing_high_list.append({"index": index, "price": highs[index]})
        before_low = lows[index - SWING_BARS:index]
        after_low = lows[index + 1:index + SWING_BARS + 1]
        if lows[index] < min(before_low) and lows[index] <= min(after_low):
            swing_low_list.append({"index": index, "price": lows[index]})
    return {"highs": swing_high_list, "lows": swing_low_list}


def smc_structure_find_breaks(opens: List[float], highs: List[float], lows: List[float], closes: List[float], swings: dict) -> List[dict]:
    """BOS and CHoCH events, each with the order block that caused it. A swing is broken once."""
    events, trend = [], None
    broken_high_index_set, broken_low_index_set = set(), set()
    for bar in range(len(closes)):
        known_highs = [s for s in swings["highs"] if s["index"] + SWING_BARS < bar and s["index"] not in broken_high_index_set]
        known_lows = [s for s in swings["lows"] if s["index"] + SWING_BARS < bar and s["index"] not in broken_low_index_set]
        if known_highs and closes[bar] > known_highs[-1]["price"]:
            level = known_highs[-1]
            kind = "CHoCH" if trend == "down" else "BOS"
            trend = "up"
            broken_high_index_set.add(level["index"])
            events.append({"index": bar, "kind": kind, "direction": "up", "level_index": level["index"], "price": level["price"],
                           "order_block": _smc_structure_find_order_block(opens, highs, lows, closes, level["index"], bar, "down")})
        elif known_lows and closes[bar] < known_lows[-1]["price"]:
            level = known_lows[-1]
            kind = "CHoCH" if trend == "up" else "BOS"
            trend = "down"
            broken_low_index_set.add(level["index"])
            events.append({"index": bar, "kind": kind, "direction": "down", "level_index": level["index"], "price": level["price"],
                           "order_block": _smc_structure_find_order_block(opens, highs, lows, closes, level["index"], bar, "up")})
    return events


def _smc_structure_find_order_block(opens, highs, lows, closes, from_index: int, to_index: int, candle_direction: str):
    """The last candle between the broken swing and the break that moves against the break: a down candle before an up break."""
    for bar in range(to_index - 1, from_index - 1, -1):
        if candle_direction == "down" and closes[bar] < opens[bar] or candle_direction == "up" and closes[bar] > opens[bar]:
            return {"index": bar, "low": lows[bar], "high": highs[bar]}
    return None


def smc_structure_find_fair_value_gaps(highs: List[float], lows: List[float], closes: List[float]) -> List[dict]:
    """A bullish gap: the bar's low is above the high two bars back. Mitigated once price trades back into the gap."""
    gap_list = []
    for bar in range(2, len(closes)):
        if lows[bar] > highs[bar - 2]:
            gap = {"start_index": bar - 2, "index": bar - 1, "direction": "up", "low": highs[bar - 2], "high": lows[bar]}
        elif highs[bar] < lows[bar - 2]:
            gap = {"start_index": bar - 2, "index": bar - 1, "direction": "down", "low": highs[bar], "high": lows[bar - 2]}
        else:
            continue
        gap["mitigated_index"] = next((later for later in range(bar + 1, len(closes))
                                       if lows[later] <= gap["high"] and highs[later] >= gap["low"]), None)
        gap_list.append(gap)
    return gap_list


def smc_structure_find_equal_levels(swings: dict) -> List[dict]:
    equal_list = []
    for kind, swing_list in (("EQH", swings["highs"]), ("EQL", swings["lows"])):
        for first, second in zip(swing_list, swing_list[1:]):
            if abs(first["price"] - second["price"]) <= first["price"] * EQUAL_LEVEL_TOLERANCE_RATIO:
                equal_list.append({"kind": kind, "first_index": first["index"], "second_index": second["index"],
                                   "price": (first["price"] + second["price"]) / 2})
    return equal_list


def smc_structure_find_sweeps(highs: List[float], lows: List[float], closes: List[float], swings: dict) -> List[dict]:
    sweep_list, swept_index_set = [], set()
    for bar in range(len(closes)):
        known_highs = [s for s in swings["highs"] if s["index"] + SWING_BARS < bar]
        known_lows = [s for s in swings["lows"] if s["index"] + SWING_BARS < bar]
        if known_highs and highs[bar] > known_highs[-1]["price"] >= closes[bar]:
            level = known_highs[-1]
            if ("high", level["index"]) not in swept_index_set:
                swept_index_set.add(("high", level["index"]))
                sweep_list.append({"index": bar, "side": "high", "price": level["price"]})
        if known_lows and lows[bar] < known_lows[-1]["price"] <= closes[bar]:
            level = known_lows[-1]
            if ("low", level["index"]) not in swept_index_set:
                swept_index_set.add(("low", level["index"]))
                sweep_list.append({"index": bar, "side": "low", "price": level["price"]})
    return sweep_list


def smc_structure_analyse(opens: List[float], highs: List[float], lows: List[float], closes: List[float]) -> dict:
    swings = smc_structure_find_swings(highs, lows)
    return {
        "swings": swings,
        "events": smc_structure_find_breaks(opens, highs, lows, closes, swings),
        "fair_value_gaps": smc_structure_find_fair_value_gaps(highs, lows, closes),
        "equal_levels": smc_structure_find_equal_levels(swings),
        "sweeps": smc_structure_find_sweeps(highs, lows, closes, swings),
    }
