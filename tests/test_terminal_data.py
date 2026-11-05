import math

import pandas
import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException

from stock_benchmark_backend import terminal_data, web_server


def _bars(count=260):
    dates = pandas.bdate_range(end="2026-11-02", periods=count)
    closes = [100 + 10 * math.sin(index / 9) + index * 0.05 for index in range(count)]
    return pandas.DataFrame({"Open": [c - 0.3 for c in closes], "High": [c + 1.2 for c in closes], "Low": [c - 1.2 for c in closes],
                             "Close": closes, "Volume": [1_000_000 + 1000 * (index % 17) for index in range(count)]}, index=dates)


def _strategy(strategy_id, evaluation):
    return {"strategy_id": strategy_id, "display_name": {"en": strategy_id, "zh": strategy_id}, "evaluation": evaluation}


def test_payload_has_every_series_the_page_draws_and_matching_lengths():
    payload = terminal_data.terminal_data_build_payload("AMD", _bars(), "stock", {"AMD": {"price": 120.0, "trailing_eps": 3.0}}, [], "2026-11-02")
    count = payload["bar_count"]
    assert count == 260 and len(payload["dates"]) == count
    assert all(len(series) == count for series in payload["ohlcv"].values())
    assert all(len(series) == count for series in payload["indicators"].values())
    assert payload["indicators"]["sma200"][198] is None and payload["indicators"]["sma200"][199] is not None


def test_pe_uses_the_last_close_for_the_symbol_itself_and_the_proxy_price_for_leveraged_etfs():
    bars = _bars()
    payload = terminal_data.terminal_data_build_payload("AMD", bars, "stock", {"AMD": {"price": 999.0, "trailing_eps": 4.0}}, [], None)
    assert payload["dip_buy"]["pe"] == pytest.approx(float(bars["Close"].iloc[-1]) / 4.0)
    muu = terminal_data.terminal_data_build_payload("MUU", bars, "etf", {"MU": {"price": 800.0, "trailing_eps": 40.0}}, [], None)
    assert muu["dip_buy"]["pe"] == pytest.approx(20.0)
    assert muu["dip_buy"]["lights"]["pe"] == "yellow"


def test_loss_making_and_no_match_show_the_right_pe_lights():
    loss = terminal_data.terminal_data_build_payload("RKLB", _bars(), "stock", {"RKLB": {"price": 50.0, "trailing_eps": -2.0}}, [], None)
    assert loss["dip_buy"]["pe"] is None and loss["dip_buy"]["lights"]["pe"] == "grey"
    etf = terminal_data.terminal_data_build_payload("RAM", _bars(), "etf", {}, [], None)
    assert etf["dip_buy"]["lights"]["pe"] == "white"


def test_strategy_cards_put_dip_buy_first_and_explain_other_results():
    failing = {"is_pass": False, "score_percent": 40.0, "not_applicable": False, "unknown_weight_ratio": 0.0,
               "gate_result_list": [{"is_pass": True, "display_name": {"en": "GATE 0", "zh": "GATE 0 市场"}},
                                    {"is_pass": False, "display_name": {"en": "GATE 2 Breakout", "zh": "GATE 2 突破"}}]}
    payload = terminal_data.terminal_data_build_payload("AMD", _bars(), "stock", {}, [
        _strategy("momentum", failing), _strategy("etf_only", {"is_pass": None, "not_applicable": True, "score_percent": None, "gate_result_list": []}),
        _strategy("missing", None)], None)
    cards = {card["strategy_id"]: card for card in payload["strategy_card_list"]}
    assert payload["strategy_card_list"][0]["strategy_id"] == "dip_buy"
    assert cards["momentum"]["text"]["en"] == "Failed at: GATE 2 Breakout"
    assert cards["momentum"]["text"]["zh"] == "未通过的门槛：GATE 2 突破"
    assert cards["etf_only"]["not_applicable"] is True
    assert cards["missing"]["text"]["en"] == "No result in the last snapshot."


def test_every_text_is_bilingual_and_the_explanation_names_the_numbers():
    payload = terminal_data.terminal_data_build_payload("AMD", _bars(), "stock", {}, [], None)
    dip = payload["strategy_card_list"][0]
    for line in dip["explanation_list"]:
        assert set(line["text"]) == {"en", "zh"} and line["text"]["en"] and line["text"]["zh"]
    rsi_line = next(line for line in dip["explanation_list"] if line["name"] == "RSI(14)")
    assert rsi_line["value"] == "{:.1f}".format(payload["dip_buy"]["rsi"])
    assert "15" in rsi_line["text"]["en"] or "25" in rsi_line["text"]["en"] or "8" in rsi_line["text"]["en"]


def test_event_log_is_newest_first_and_capped():
    payload = terminal_data.terminal_data_build_payload("AMD", _bars(), "stock", {}, [], None)
    dates = [event["date"] for event in payload["event_list"]]
    assert dates == sorted(dates, reverse=True) and len(payload["event_list"]) <= terminal_data.EVENT_LOG_LENGTH


def test_unknown_symbol_is_404_and_a_missing_history_is_503(monkeypatch):
    with pytest.raises(HTTPException) as unknown:
        web_server.web_server_get_terminal_payload("NOPE_NOT_IN_SNAPSHOT")
    assert unknown.value.status_code == 404

    def no_history(symbol):
        raise terminal_data.TerminalDataUnavailable(symbol)
    monkeypatch.setattr(terminal_data, "terminal_data_load_bars", no_history)
    snapshot = web_server.web_server_load_snapshot_or_empty_snapshot()
    known = snapshot["symbol_result_list"][0]["symbol"]
    with pytest.raises(HTTPException) as unavailable:
        web_server.web_server_get_terminal_payload(known)
    assert unavailable.value.status_code == 503


def test_terminal_routes_serve_the_page_and_its_files_and_api_returns_a_payload(monkeypatch):
    client = TestClient(web_server.app)
    assert client.get("/terminal/AMD").status_code == 200
    assert client.get("/terminal.js").status_code == 200
    assert client.get("/terminal.css").status_code == 200
    monkeypatch.setattr(terminal_data, "terminal_data_load_bars", lambda symbol: _bars())
    known = web_server.web_server_load_snapshot_or_empty_snapshot()["symbol_result_list"][0]["symbol"]
    response = client.get("/api/v1/terminal/" + known)
    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == known and body["dip_buy"]["score"] >= 0
    assert body["strategy_card_list"][0]["strategy_id"] == "dip_buy"


def test_an_empty_download_is_retried_then_cached_and_a_persistent_failure_is_not_cached(monkeypatch):
    calls = []
    monkeypatch.setattr(terminal_data.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(terminal_data, "_bars_cache_by_symbol", {})
    answers = [{}, {}, {"ZZZ": _bars()}]
    monkeypatch.setattr(terminal_data.market_data, "market_data_fetch_daily_price_history_for_symbol_list",
                        lambda symbol_list, period: (calls.append(1), answers.pop(0))[1])
    bars = terminal_data.terminal_data_load_bars("ZZZ")
    assert len(calls) == 3 and len(bars) == 260
    terminal_data.terminal_data_load_bars("ZZZ")
    assert len(calls) == 3  # served from the cache

    monkeypatch.setattr(terminal_data, "_bars_cache_by_symbol", {})
    monkeypatch.setattr(terminal_data.market_data, "market_data_fetch_daily_price_history_for_symbol_list", lambda symbol_list, period: {})
    with pytest.raises(terminal_data.TerminalDataUnavailable):
        terminal_data.terminal_data_load_bars("ZZZ")
    assert "ZZZ" not in terminal_data._bars_cache_by_symbol
