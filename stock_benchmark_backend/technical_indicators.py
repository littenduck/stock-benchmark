"""Price indicators for the terminal page, computed from daily bars in time order.

Every function returns a list the same length as its input, with None where there is not yet enough history. The formulas are the
ones in the dip_buy spec: EMA seeded with the first value, RSI with Wilder smoothing, Bollinger bands with the population standard
deviation, and %B in percent (below 0 means under the lower band).
"""
import math
from typing import List, Optional, Sequence

RSI_PERIOD = 14
MACD_FAST_PERIOD = 12
MACD_SLOW_PERIOD = 26
MACD_SIGNAL_PERIOD = 9
BOLLINGER_PERIOD = 20
BOLLINGER_WIDTH = 2.0
VOLUME_AVERAGE_PERIOD = 30


def technical_indicators_sma(values: Sequence[float], period: int) -> List[Optional[float]]:
    result: List[Optional[float]] = [None] * len(values)
    for index in range(period - 1, len(values)):
        result[index] = sum(values[index - period + 1:index + 1]) / period
    return result


def technical_indicators_ema(values: Sequence[float], period: int) -> List[float]:
    """EMA_t = price * k + EMA_(t-1) * (1 - k), k = 2 / (period + 1), seeded with the first value."""
    factor = 2 / (period + 1)
    result = [values[0]]
    for value in values[1:]:
        result.append(value * factor + result[-1] * (1 - factor))
    return result


def technical_indicators_rsi(closes: Sequence[float], period: int = RSI_PERIOD) -> List[Optional[float]]:
    """Wilder's RSI: the first average is a plain mean of the first `period` moves, then each new move is averaged in with weight 1/period."""
    result: List[Optional[float]] = [None] * len(closes)
    if len(closes) <= period:
        return result
    gains = [max(closes[i] - closes[i - 1], 0.0) for i in range(1, len(closes))]
    losses = [max(closes[i - 1] - closes[i], 0.0) for i in range(1, len(closes))]
    average_gain = sum(gains[:period]) / period
    average_loss = sum(losses[:period]) / period
    result[period] = _technical_indicators_rsi_value(average_gain, average_loss)
    for offset in range(period, len(gains)):
        average_gain = (average_gain * (period - 1) + gains[offset]) / period
        average_loss = (average_loss * (period - 1) + losses[offset]) / period
        result[offset + 1] = _technical_indicators_rsi_value(average_gain, average_loss)
    return result


def _technical_indicators_rsi_value(average_gain: float, average_loss: float) -> float:
    if average_loss == 0:
        return 100.0 if average_gain > 0 else 50.0
    return 100 - 100 / (1 + average_gain / average_loss)


def technical_indicators_macd(closes: Sequence[float]) -> dict:
    """MACD line = EMA12 - EMA26; signal = EMA9 of the MACD line; histogram = MACD line - signal. No None: the EMAs start at bar 0."""
    macd_line = [fast - slow for fast, slow in zip(technical_indicators_ema(closes, MACD_FAST_PERIOD),
                                                   technical_indicators_ema(closes, MACD_SLOW_PERIOD))]
    signal_line = technical_indicators_ema(macd_line, MACD_SIGNAL_PERIOD)
    return {"macd": macd_line, "signal": signal_line,
            "histogram": [line - signal for line, signal in zip(macd_line, signal_line)]}


def technical_indicators_bollinger(closes: Sequence[float], period: int = BOLLINGER_PERIOD,
                                   width: float = BOLLINGER_WIDTH) -> dict:
    middle_list: List[Optional[float]] = [None] * len(closes)
    upper_list: List[Optional[float]] = [None] * len(closes)
    lower_list: List[Optional[float]] = [None] * len(closes)
    percent_b_list: List[Optional[float]] = [None] * len(closes)
    for index in range(period - 1, len(closes)):
        window = closes[index - period + 1:index + 1]
        middle = sum(window) / period
        deviation = math.sqrt(sum((value - middle) ** 2 for value in window) / period)
        upper, lower = middle + width * deviation, middle - width * deviation
        middle_list[index], upper_list[index], lower_list[index] = middle, upper, lower
        if upper > lower:
            percent_b_list[index] = (closes[index] - lower) / (upper - lower) * 100
    return {"middle": middle_list, "upper": upper_list, "lower": lower_list, "percent_b": percent_b_list}


def technical_indicators_volume_ratio(volumes: Sequence[float], period: int = VOLUME_AVERAGE_PERIOD) -> List[Optional[float]]:
    """Each day's volume over the average of the `period` days before it (today is not in its own average)."""
    result: List[Optional[float]] = [None] * len(volumes)
    for index in range(period, len(volumes)):
        average = sum(volumes[index - period:index]) / period
        if average > 0:
            result[index] = volumes[index] / average
    return result
