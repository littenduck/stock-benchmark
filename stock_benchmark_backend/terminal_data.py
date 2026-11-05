"""The data behind the symbol terminal page: daily bars, indicator series, SMC structure, the dip_buy score, the other strategies'
results from the last snapshot, and a log of recent signal events. Every explanation line is {en, zh}; each language stands alone.
"""
import time
from typing import Dict, List, Optional

import pandas

from stock_benchmark_backend import dip_buy, market_data, smc_structure, technical_indicators

HISTORY_PERIOD = "1y"  # the same window as the dashboard's history (refresh_scheduler)
BARS_CACHE_SECONDS = 600
DOWNLOAD_ATTEMPT_COUNT = 3
DOWNLOAD_RETRY_SECONDS = 1.0
EVENT_LOG_LENGTH = 8
# Leveraged single-stock ETFs have no earnings of their own: their PE is the PE of the stock they track.
PE_PROXY_BY_SYMBOL = {"MUU": "MU", "SNXX": "SNDK"}

_bars_cache_by_symbol: Dict[str, tuple] = {}


class TerminalDataUnavailable(Exception):
    pass


def terminal_data_load_bars(symbol: str) -> pandas.DataFrame:
    """Daily bars for one symbol, cached for a few minutes. Yahoo sometimes answers an empty table when it is busy, so a failed
    download is tried again after a short pause. Failures are not cached."""
    cached = _bars_cache_by_symbol.get(symbol)
    if cached and time.time() - cached[0] < BARS_CACHE_SECONDS:
        return cached[1]
    for attempt in range(DOWNLOAD_ATTEMPT_COUNT):
        history = market_data.market_data_fetch_daily_price_history_for_symbol_list([symbol], HISTORY_PERIOD).get(symbol)
        if history is not None and not history.empty:
            _bars_cache_by_symbol[symbol] = (time.time(), history)
            return history
        if attempt + 1 < DOWNLOAD_ATTEMPT_COUNT:
            time.sleep(DOWNLOAD_RETRY_SECONDS)
    raise TerminalDataUnavailable(symbol)


def _bilingual(en: str, zh: str) -> dict:
    return {"en": en, "zh": zh}


def _round_or_none(value: Optional[float], digits: int = 2) -> Optional[float]:
    return None if value is None else round(float(value), digits)


def _series_rounded(values: List[Optional[float]], digits: int = 2) -> List[Optional[float]]:
    return [_round_or_none(value, digits) for value in values]


def _event_list(dates: List[str], closes: List[float], series: dict, smc: dict) -> List[dict]:
    """The most recent signal changes, newest first. Each has an index, a date, a tone (positive, negative, neutral) and {en, zh} text."""
    found = []
    histogram, rsi, percent_b = series["macd_histogram"], series["rsi"], series["percent_b"]
    sma20 = series["sma20"]
    for bar in range(1, len(closes)):
        if histogram[bar - 1] < 0 <= histogram[bar]:
            found.append((bar, "positive", _bilingual("MACD histogram turned positive", "MACD 柱翻正")))
        elif histogram[bar - 1] >= 0 > histogram[bar]:
            found.append((bar, "negative", _bilingual("MACD histogram turned negative", "MACD 柱翻负")))
        if rsi[bar - 1] is not None and rsi[bar] is not None:
            if rsi[bar - 1] >= 30 > rsi[bar]:
                found.append((bar, "positive", _bilingual("RSI(14) fell below 30", "RSI(14) 跌破 30")))
            elif rsi[bar - 1] < 30 <= rsi[bar]:
                found.append((bar, "neutral", _bilingual("RSI(14) back above 30", "RSI(14) 回到 30 以上")))
        if percent_b[bar - 1] is not None and percent_b[bar] is not None and percent_b[bar - 1] >= 10 > percent_b[bar]:
            found.append((bar, "positive", _bilingual("%B fell below 10", "%B 跌破 10")))
        if sma20[bar - 1] is not None and sma20[bar] is not None:
            if closes[bar - 1] >= sma20[bar - 1] > closes[bar]:
                found.append((bar, "negative", _bilingual("Close crossed below SMA20", "收盘价跌破 SMA20")))
            elif closes[bar - 1] < sma20[bar - 1] <= closes[bar]:
                found.append((bar, "positive", _bilingual("Close crossed above SMA20", "收盘价站上 SMA20")))
    for event in smc["events"]:
        tone = "positive" if event["direction"] == "up" else "negative"
        found.append((event["index"], tone, _bilingual("{} {} structure".format(event["kind"], event["direction"]),
                                                       "{}，结构{}".format(event["kind"], "向上" if event["direction"] == "up" else "向下"))))
    for sweep in smc["sweeps"]:
        found.append((sweep["index"], "neutral", _bilingual("Liquidity sweep of the {} side".format(sweep["side"]),
                                                           "扫过{}流动性".format("高点" if sweep["side"] == "high" else "低点"))))
    found.sort(key=lambda item: item[0], reverse=True)
    return [{"index": bar, "date": dates[bar], "tone": tone, "text": text} for bar, tone, text in found[:EVENT_LOG_LENGTH]]


MACD_STATE_TEXT = {
    "turned_positive": _bilingual("turned positive", "由负转正"),
    "negative_shrinking": _bilingual("below zero and shrinking", "负值收窄"),
    "negative_expanding": _bilingual("below zero and expanding", "负值扩大"),
    "positive": _bilingual("above zero, not a turn", "正值，非翻正"),
}


def _dip_buy_explanation_list(result: dict) -> List[dict]:
    light = result["lights"]
    macd_state = MACD_STATE_TEXT[result["macd_state"]]
    eps_text = "n/a" if result["pe"] is None else "{:.1f}".format(result["pe"])
    return [
        {"name": "RSI(14)", "value": "{:.1f}".format(result["rsi"]), "points": result["rsi_points"], "light": light["rsi"],
         "text": _bilingual("RSI(14) {:.1f}: below 30 gives 25, 30 to 35 gives 15, 35 to 45 gives 8, above 45 gives 0. Scored {} points."
                            .format(result["rsi"], result["rsi_points"]),
                            "RSI(14) {:.1f}：低于 30 得 25 分，30 到 35 得 15 分，35 到 45 得 8 分，高于 45 得 0 分。本项得 {} 分。"
                            .format(result["rsi"], result["rsi_points"]))},
        {"name": "%B", "value": "{:.1f}%".format(result["percent_b"]), "points": result["percent_b_points"], "light": light["percent_b"],
         "text": _bilingual("%B {:.1f}%: below 10 gives 20, 10 to 25 gives 12, 25 to 50 gives 6, above 50 gives 0. Scored {} points."
                            .format(result["percent_b"], result["percent_b_points"]),
                            "%B {:.1f}%：低于 10 得 20 分，10 到 25 得 12 分，25 到 50 得 6 分，高于 50 得 0 分。本项得 {} 分。"
                            .format(result["percent_b"], result["percent_b_points"]))},
        {"name": "MACD", "value": "{:.2f}".format(result["macd_histogram"]), "points": result["macd_points"], "light": light["macd"],
         "text": _bilingual("MACD histogram {:.2f}, {}: turned positive gives 25, below zero and shrinking gives 15, expanding gives 0. "
                            "Scored {} points.".format(result["macd_histogram"], macd_state["en"], result["macd_points"]),
                            "MACD 柱 {:.2f}，{}：由负转正得 25 分，负值收窄得 15 分，负值扩大得 0 分。本项得 {} 分。"
                            .format(result["macd_histogram"], macd_state["zh"], result["macd_points"]))},
        {"name": "PE", "value": eps_text, "points": None, "light": light["pe"],
         "text": _bilingual("PE is the price over the trailing twelve-month EPS. Not counted in the score; loss-making shows grey.",
                            "PE 为股价除以过去 12 个月每股收益。不计入分数；亏损显示灰色。")},
        {"name": "SMA200", "value": "above" if result["sma200_light"] == "green" else "below" if result["sma200_light"] == "red" else "n/a",
         "points": None, "light": result["sma200_light"],
         "text": _bilingual("Trend gate: the close against the 200-day average. Shown only, not in the score.",
                            "趋势门槛：收盘价相对 200 日均线。只显示，不计入分数。")},
    ]


def _strategy_card(strategy: dict) -> dict:
    evaluation = strategy.get("evaluation")
    if evaluation is None:
        return {"strategy_id": strategy["strategy_id"], "display_name": strategy["display_name"], "score_percent": None,
                "is_pass": None, "not_applicable": False, "text": _bilingual("No result in the last snapshot.", "上次快照里没有结果。")}
    if evaluation.get("not_applicable"):
        return {"strategy_id": strategy["strategy_id"], "display_name": strategy["display_name"], "score_percent": None,
                "is_pass": None, "not_applicable": True,
                "text": _bilingual("Not applicable to this asset type.", "不适用于这种资产类型。")}
    failed_gate_list = [gate["display_name"] for gate in evaluation["gate_result_list"] if not gate["is_pass"]]
    if evaluation["is_pass"]:
        text = _bilingual("Every gate passes.", "各门槛全部通过。")
    else:
        text = _bilingual("Failed at: " + ", ".join(gate["en"] for gate in failed_gate_list),
                          "未通过的门槛：" + "、".join(gate["zh"] for gate in failed_gate_list))
    return {"strategy_id": strategy["strategy_id"], "display_name": strategy["display_name"],
            "score_percent": evaluation["score_percent"], "is_pass": evaluation["is_pass"],
            "not_applicable": False, "text": text}


def terminal_data_build_payload(symbol: str, bars: pandas.DataFrame, asset_type: str, fundamentals_by_symbol: Dict[str, dict],
                                strategy_list: List[dict], generated_at: Optional[str]) -> dict:
    """fundamentals_by_symbol: {symbol: {"price", "trailing_eps"}} from the snapshot. strategy_list: {strategy_id, display_name {en, zh},
    evaluation (from the snapshot, or None)} for each strategy."""
    dates = [index.strftime("%Y-%m-%d") for index in bars.index]
    opens, highs = [float(v) for v in bars["Open"]], [float(v) for v in bars["High"]]
    lows, closes = [float(v) for v in bars["Low"]], [float(v) for v in bars["Close"]]
    volumes = [float(v) for v in bars["Volume"]]

    sma20 = technical_indicators.technical_indicators_sma(closes, 20)
    sma50 = technical_indicators.technical_indicators_sma(closes, 50)
    sma200 = technical_indicators.technical_indicators_sma(closes, 200)
    bollinger = technical_indicators.technical_indicators_bollinger(closes)
    rsi = technical_indicators.technical_indicators_rsi(closes)
    macd = technical_indicators.technical_indicators_macd(closes)
    volume_ratio = technical_indicators.technical_indicators_volume_ratio(volumes)
    volume_average = [None if ratio is None else volumes[i] / ratio for i, ratio in enumerate(volume_ratio)]
    smc = smc_structure.smc_structure_analyse(opens, highs, lows, closes)

    pe_symbol = PE_PROXY_BY_SYMBOL.get(symbol, symbol)
    pe_fundamentals = fundamentals_by_symbol.get(pe_symbol, {})
    eps = pe_fundamentals.get("trailing_eps")
    pe_price = closes[-1] if pe_symbol == symbol else pe_fundamentals.get("price")  # the snapshot price of a proxy may be older than the bars
    pe = pe_price / eps if eps and eps > 0 and pe_price else None
    has_single_match = asset_type == "stock" or symbol in PE_PROXY_BY_SYMBOL
    result = dip_buy.dip_buy_evaluate(closes, volumes, rsi, bollinger["percent_b"], macd["histogram"], sma20, sma50, sma200,
                                      volume_ratio, pe, eps is not None, has_single_match)

    series = {"macd_histogram": macd["histogram"], "rsi": rsi, "percent_b": bollinger["percent_b"], "sma20": sma20}
    events = _event_list(dates, closes, series, smc)
    strategy_card_list = [{"strategy_id": "dip_buy", "display_name": _bilingual("dip_buy", "dip_buy"), "score_percent": result["score"],
                           "is_pass": result["verdict"] == "buy", "not_applicable": False, "verdict": result["verdict"],
                           "explanation_list": _dip_buy_explanation_list(result), "counts": result["counts"],
                           "text": _bilingual("Dip-buy score out of 100. 80 or more: buy; 50 to 79: wait; below 50: no.",
                                              "抄底分，满分 100。80 以上可以，50 到 79 观望，50 以下不行。")}]
    strategy_card_list += [_strategy_card(strategy) for strategy in strategy_list]

    return {
        "symbol": symbol, "asset_type": asset_type, "generated_at": generated_at,
        "as_of": dates[-1], "bar_count": len(dates), "dates": dates,
        "ohlcv": {"open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes},
        "indicators": {
            "sma20": _series_rounded(sma20), "sma50": _series_rounded(sma50), "sma200": _series_rounded(sma200),
            "bollinger_upper": _series_rounded(bollinger["upper"]), "bollinger_middle": _series_rounded(bollinger["middle"]),
            "bollinger_lower": _series_rounded(bollinger["lower"]), "percent_b": _series_rounded(bollinger["percent_b"]),
            "rsi": _series_rounded(rsi), "macd": _series_rounded(macd["macd"], 3), "macd_signal": _series_rounded(macd["signal"], 3),
            "macd_histogram": _series_rounded(macd["histogram"], 3), "volume_average": _series_rounded(volume_average, 0),
            "volume_ratio": _series_rounded(volume_ratio, 2),
        },
        "smc": smc,
        "dip_buy": result,
        "pipeline": {
            "scout": {"bars": len(dates), "as_of": dates[-1]},
            "filter": {"light": result["sma200_light"]},
            "analyst": {"score": result["score"]},
            "executor": {"verdict": result["verdict"]},
            "logger": {"events": len(events)},
        },
        "strategy_card_list": strategy_card_list,
        "event_list": events,
    }
