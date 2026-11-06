"""dip_buy: a 0 to 100 score for buying a dip, from RSI(14), %B and the MACD histogram.

Points (raw, out of 70): RSI below 30 gives 25, 30 to 35 gives 15, 35 to 45 gives 8, above 45 gives 0.
%B below 10 gives 20, 10 to 25 gives 12, 25 to 50 gives 6, above 50 gives 0.
MACD histogram turning positive (from negative) gives 25, still negative and shrinking gives 15, expanding gives 0; a positive
histogram that is not a turn gives 0.
Score = raw / 70 * 100, rounded. 80 or more: buy (可以); 50 to 79: wait (观望); below 50: no (不行).

Traffic lights and counts: PE, RSI, MACD, %B, SMA20, SMA50 and volume are counted (green, yellow, red). SMA200 is shown as a
gate but not counted. A stock with no usable EPS shows the PE light as grey (loss) or white (no single match) and is not counted.
"""
from typing import List, Optional

RAW_POINT_MAXIMUM = 70
BUY_SCORE_MINIMUM = 80
WAIT_SCORE_MINIMUM = 50
COUNTED_LIGHT_KEY_LIST = ["pe", "rsi", "macd", "percent_b", "sma20", "sma50", "volume"]


def dip_buy_rsi_points(rsi: float) -> int:
    if rsi < 30:
        return 25
    if rsi < 35:
        return 15
    if rsi <= 45:
        return 8
    return 0


def dip_buy_percent_b_points(percent_b: float) -> int:
    if percent_b < 10:
        return 20
    if percent_b < 25:
        return 12
    if percent_b <= 50:
        return 6
    return 0


def dip_buy_macd_state(histogram_list: List[float]) -> str:
    """turned_positive, negative_shrinking, negative_expanding, positive."""
    last, previous = histogram_list[-1], histogram_list[-2]
    if previous < 0 <= last:
        return "turned_positive"
    if last < 0:
        return "negative_shrinking" if last > previous else "negative_expanding"
    return "positive"


def dip_buy_macd_points(state: str) -> int:
    return {"turned_positive": 25, "negative_shrinking": 15}.get(state, 0)


def dip_buy_verdict(score: int) -> str:
    if score >= BUY_SCORE_MINIMUM:
        return "buy"
    if score >= WAIT_SCORE_MINIMUM:
        return "wait"
    return "no"


def _light_for_rsi(rsi: float) -> str:
    return "green" if rsi < 30 else "yellow" if rsi <= 45 else "red"


def _light_for_percent_b(percent_b: float) -> str:
    return "green" if percent_b < 10 else "yellow" if percent_b <= 50 else "red"


def _light_for_macd(state: str) -> str:
    return {"turned_positive": "green", "negative_shrinking": "yellow", "negative_expanding": "red"}.get(state, "yellow")


def _light_for_above(value: Optional[float], close: float) -> Optional[str]:
    if value is None:
        return None
    return "green" if close >= value else "red"


def _light_for_volume(volume_ratio: Optional[float], change: float) -> Optional[str]:
    if volume_ratio is None:
        return None
    heavy = volume_ratio >= 1.0
    if change < 0:
        return "red" if heavy else "green"
    return "green" if heavy else "yellow"


def _light_for_pe(pe: Optional[float], earnings_known: bool, has_single_match: bool) -> str:
    if not has_single_match or not earnings_known:
        return "white"
    if pe is None:
        return "grey"
    return "green" if pe < 15 else "yellow" if pe <= 40 else "red"


def dip_buy_evaluate(closes: List[float], volumes: List[float], rsi_list: List[Optional[float]], percent_b_list: List[Optional[float]],
                     macd_histogram_list: List[float], sma20_list: List[Optional[float]], sma50_list: List[Optional[float]],
                     sma200_list: List[Optional[float]], volume_ratio_list: List[Optional[float]], pe: Optional[float],
                     earnings_known: bool, pe_has_single_match: bool) -> dict:
    """The score for the last bar. Lists are the same length as closes; the last bar is the day being scored.
    pe is the price over trailing EPS (None when EPS is zero or negative, which is a loss); earnings_known is False when there is no EPS at all."""
    close = closes[-1]
    rsi, percent_b = rsi_list[-1], percent_b_list[-1]
    if rsi is None or percent_b is None:
        raise ValueError("dip_buy needs at least 30 daily bars")
    macd_state = dip_buy_macd_state(macd_histogram_list)
    rsi_points = dip_buy_rsi_points(rsi)
    percent_b_points = dip_buy_percent_b_points(percent_b)
    macd_points = dip_buy_macd_points(macd_state)
    raw_points = rsi_points + percent_b_points + macd_points
    score = round(raw_points / RAW_POINT_MAXIMUM * 100)
    change = close - closes[-2]
    light_map = {
        "pe": _light_for_pe(pe, earnings_known, pe_has_single_match),
        "rsi": _light_for_rsi(rsi),
        "macd": _light_for_macd(macd_state),
        "percent_b": _light_for_percent_b(percent_b),
        "sma20": _light_for_above(sma20_list[-1], close),
        "sma50": _light_for_above(sma50_list[-1], close),
        "volume": _light_for_volume(volume_ratio_list[-1], change),
    }
    counts = {"green": 0, "yellow": 0, "red": 0}
    for key in COUNTED_LIGHT_KEY_LIST:
        if light_map[key] in counts:
            counts[light_map[key]] += 1
    return {
        "score": score, "verdict": dip_buy_verdict(score), "raw_points": raw_points,
        "rsi": rsi, "rsi_points": rsi_points,
        "percent_b": percent_b, "percent_b_points": percent_b_points,
        "macd_histogram": macd_histogram_list[-1], "macd_state": macd_state, "macd_points": macd_points,
        "sma200_light": _light_for_above(sma200_list[-1], close),
        "pe": pe, "lights": light_map, "counts": counts,
    }
