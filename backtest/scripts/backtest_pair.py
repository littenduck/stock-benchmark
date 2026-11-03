"""Run the strategy set on a base/leverage ETF pair, using a subset of the entry dates.

Pairs (see PAIRS): QQQ/TQQQ, and SOXX/SOXL. The base ETF (1x) drives the signals.
The leverage ETF (3x) is what the leveraged strategies hold. Strategies that need
other tickers (P-U: TLT, SCHD, GLD, DBC, IEF, SPY and sector ETFs) are not run here.

Entry dates: SOXL starts 2010-03-11, so the pair run uses a test subset of the QQQ
entry dates from backtest_strategies.py, chosen from 2010 onward. A subset of
entries is used so that each market cycle contributes one high and one low.

Engine, tax model and chart code come from backtest_strategies.py. The signal
definitions here are the same as there, with the tickers as parameters.

Run:  python3 scripts/backtest_pair.py soxx_soxl
      python3 scripts/backtest_pair.py qqq_tqqq    # cross-check against the main run
"""

from __future__ import annotations

import argparse

import pandas as pd
import yfinance as yf

import backtest_strategies as bs

# Test subset for the pair runs. Each is an entry date from bs.ENTRY_SCENARIOS
# (one high and one low per cycle, 2010 onward).
SUBSET = [
    "2011-02-16", "2012-06-04", "2014-03-07", "2015-08-24", "2018-10-01", "2018-12-24",
    "2020-02-19", "2020-03-23", "2021-11-22", "2022-10-13", "2024-07-10", "2025-04-07",
]

PAIRS = {
    "qqq_tqqq": {"base": "QQQ", "lev": "TQQQ", "entries": None},  # None = all 42 entries
    "soxx_soxl": {"base": "SOXX", "lev": "SOXL", "entries": SUBSET},
}


def load_prices(base: str, lev: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = yf.download([base, lev], start="2009-01-01", auto_adjust=False, actions=True, progress=False)
    adj = raw["Adj Close"][[base, lev]].dropna(subset=[base])
    close = raw["Close"][[base, lev]].reindex(adj.index)
    div = raw["Dividends"][[base, lev]].reindex(adj.index).fillna(0.0)
    return adj, (div / close).fillna(0.0)


def grid_for(ticker: str, initial: float = 50_000.0, pct: float = 0.10, unit: float = 10_000.0):
    state = {"ref": None}

    def step(eng, day):
        p = eng.price(day, ticker)
        if state["ref"] is None:
            eng.buy(day, ticker, initial)
            state["ref"] = p
        elif p <= state["ref"] * (1 - pct) and eng.cash >= unit:
            eng.buy(day, ticker, unit)
            state["ref"] = p
        elif p >= state["ref"] * (1 + pct) and eng.shares[ticker] > 1e-9:
            eng.sell(day, ticker, unit / p)
            state["ref"] = p
    return step


def add_on_dip_for(ticker: str, initial_frac: float = 0.5, drop: float = 0.10, add_frac: float = 0.25):
    state = {"last": None}

    def step(eng, day):
        p = eng.price(day, ticker)
        if state["last"] is None:
            eng.buy(day, ticker, eng.cash * initial_frac)
            state["last"] = p
        elif p <= state["last"] * (1 - drop) and eng.cash > 1:
            eng.buy(day, ticker, eng.cash * add_frac)
            state["last"] = p
    return step


def build_strategies(adj: pd.DataFrame, dates: pd.DatetimeIndex, base: str, lev: str) -> list[bs.Strategy]:
    start = dates[0]
    b, l = adj[base], adj[lev]

    def on(s: pd.Series) -> pd.Series:
        return s.loc[dates]

    always = pd.Series(True, index=dates)
    sma200 = b.rolling(200).mean()

    sig_100_225 = on(b.rolling(100).mean() > b.rolling(225).mean())
    sig_50_200 = on(b.rolling(50).mean() > b.rolling(200).mean())
    sig_5_20 = on(b.rolling(5).mean() > b.rolling(20).mean())
    sig_20_50 = on(b.rolling(20).mean() > b.rolling(50).mean())
    sig_20_200 = on(b.rolling(20).mean() > b.rolling(200).mean())
    sig_sma225 = on(b > b.rolling(225).mean())
    sig_sma210 = on(b > b.rolling(210).mean())

    macd = b.ewm(span=12, adjust=False).mean() - b.ewm(span=26, adjust=False).mean()
    sig_macd = on(macd > macd.ewm(span=9, adjust=False).mean())

    sig_turtle = on(bs.state_machine(
        b > b.rolling(20).max().shift(1),
        b < b.rolling(10).min().shift(1),
    ))

    rsi14 = bs.rsi(b)
    sig_rsi = on(bs.state_machine(rsi14 < 30, rsi14 > 55))

    mid = b.rolling(20).mean()
    lower = mid - 2 * b.rolling(20).std()
    sig_boll = on(bs.state_machine(b < lower, b > mid))

    sig_trail = bs.trailing_stop_on(on(l), on(b), on(sma200))

    month_firsts = set(pd.Series(dates).groupby(dates.to_period("M")).first()) - {start}
    targets = pd.date_range(start, dates[-1], freq="14D")[1:]
    pos = dates.searchsorted(targets)
    biweekly = set(dates[pos[pos < len(dates)]])

    return [
        bs.Strategy("A", f"{base} buy & hold", f"{base} all-in hold", "benchmark",
                    f"Buy {base} with all 100k on START, hold to the end.",
                    bs.timing_step(base, always)),
        bs.Strategy("B", f"{lev} buy & hold", f"{lev} all-in hold", "benchmark",
                    f"Buy {lev} with all 100k on START, hold to the end.",
                    bs.timing_step(lev, always)),
        bs.Strategy("C", f"{base} monthly DCA 1500", f"{base} monthly DCA 1500", "DCA",
                    f"On the first trading day of each month, buy 1500 of {base} from the 100k pool. Unspent cash is idle.",
                    bs.dca_step(month_firsts, bs.MONTHLY, base)),
        bs.Strategy("D", f"{base} biweekly DCA 1000", f"{base} biweekly DCA 1000", "DCA",
                    f"Every 14 days from START, buy 1000 of {base} from the 100k pool. Stops when cash runs out.",
                    bs.dca_step(biweekly, bs.BIWEEKLY, base)),
        bs.Strategy("E", f"SMA 225 single, {lev}", f"SMA 225 single line → {lev}", "moving average",
                    f"Signal: {base} close above its 225-day SMA: all-in {lev}. Below: all cash.",
                    bs.timing_step(lev, sig_sma225)),
        bs.Strategy("F", f"SMA 50/200 cross, {lev}", f"SMA 50/200 golden/death cross → {lev}", "moving average",
                    f"Signal: 50-day SMA vs 200-day SMA of {base}. Golden cross: all-in {lev}. Death cross: all cash.",
                    bs.timing_step(lev, sig_50_200)),
        bs.Strategy("G", f"SMA 100/225 cross, {lev}", f"SMA 100/225 golden/death cross → {lev}", "moving average",
                    f"Signal: 100-day SMA of {base} vs 225-day SMA. Golden cross: all-in {lev}. Death cross: all cash.",
                    bs.timing_step(lev, sig_100_225)),
        bs.Strategy("H", f"SMA 5/20 cross, {lev}", f"SMA 5/20 golden/death cross → {lev}", "moving average",
                    f"Signal: 5-day SMA of {base} vs 20-day SMA. Golden cross: all-in {lev}. Death cross: all cash.",
                    bs.timing_step(lev, sig_5_20)),
        bs.Strategy("I", f"SMA 20/50 cross, {lev}", f"SMA 20/50 golden/death cross → {lev}", "moving average",
                    f"Signal: 20-day SMA of {base} vs 50-day SMA. Golden cross: all-in {lev}. Death cross: all cash.",
                    bs.timing_step(lev, sig_20_50)),
        bs.Strategy("J", f"SMA 20/200 cross, {lev}", f"SMA 20/200 golden/death cross → {lev}", "moving average",
                    f"Signal: 20-day SMA of {base} vs 200-day SMA. Golden cross: all-in {lev}. Death cross: all cash.",
                    bs.timing_step(lev, sig_20_200)),
        bs.Strategy("K", f"10-month SMA trend, {base}", f"10-month SMA (210 days) → {base}", "moving average",
                    f"Signal: {base} close above its 210-day SMA: all-in {base}. Below: all cash.",
                    bs.timing_step(base, sig_sma210)),
        bs.Strategy("L", f"MACD 12/26/9, {lev}", f"MACD golden/death cross → {lev}", "indicator",
                    f"Signal: MACD line of {base} vs its 9-day EMA. Above: all-in {lev}. Below: all cash.",
                    bs.timing_step(lev, sig_macd)),
        bs.Strategy("M", f"Turtle 20/10 breakout, {lev}", f"Turtle breakout 20/10 → {lev}", "indicator",
                    f"Enter {lev} when {base} closes above its prior 20-day high. Exit when it closes below its prior 10-day low.",
                    bs.timing_step(lev, sig_turtle)),
        bs.Strategy("N", f"RSI(14) 30/55, {lev}", f"RSI(14) oversold 30 in / 55 out → {lev}", "indicator",
                    f"Enter {lev} when {base} RSI(14) falls below 30. Exit to cash when RSI rises above 55.",
                    bs.timing_step(lev, sig_rsi)),
        bs.Strategy("O", f"Bollinger 20,2σ, {lev}", f"Bollinger 20,2σ mean reversion → {lev}", "indicator",
                    f"Enter {lev} when {base} closes below the lower band. Exit to cash when it closes above the 20-day SMA.",
                    bs.timing_step(lev, sig_boll)),
        bs.Strategy("V", f"Trailing stop 30%, {lev}", f"Trailing stop 30%, re-enter when {base} is above its 200-day SMA ({lev})", "risk control",
                    f"Hold {lev}. Sell all after a 30% fall from the peak since buying. Re-enter when {base} closes above its 200-day SMA.",
                    bs.timing_step(lev, sig_trail)),
        bs.Strategy("W", f"Grid {lev}", f"Grid trading {lev} (10% steps, 10k per cell)", "risk control",
                    f"Start with 50k in {lev}. Each 10% fall from the last trade price buys 10k. Each 10% rise sells 10k.",
                    grid_for(lev)),
        bs.Strategy("X", f"Add on 10% dips, {lev}", f"Add on dips {lev} (add 25% of remaining cash per 10% fall)", "risk control",
                    f"Start by buying {lev} with 50% of cash. Each 10% fall from the last buy adds 25% of the remaining cash. Never sells.",
                    add_on_dip_for(lev)),
    ]


def entry_name(label: str, entry: str) -> str:
    # The entry date comes from a QQQ peak or trough, so the name says so: 2011-02-16_QQQ-high.
    side = "high" if " high " in label else "low"
    return f"{entry}_QQQ-{side}"


def run(pair_id: str) -> None:
    cfg = PAIRS[pair_id]
    base, lev = cfg["base"], cfg["lev"]
    bs.TICKERS = [base, lev]  # the engine builds its holdings from this list
    out_dir = bs.OUT_DIR / pair_id
    out_dir.mkdir(parents=True, exist_ok=True)

    adj, yld = load_prices(base, lev)
    wanted = cfg["entries"]
    entries = [
        (entry_name(label, entry), entry)
        for label, entry in bs.ENTRY_SCENARIOS
        if wanted is None or entry in wanted
    ]

    rows = []
    for i, (label, entry) in enumerate(entries):
        dates = adj.index[adj.index >= entry]
        strategies = build_strategies(adj, dates, base, lev)
        ideal: dict[str, float] = {}
        ideal_curves: dict[str, pd.Series] = {}
        taxed_curves: dict[str, dict[str, pd.Series]] = {name: {} for name, _, _ in bs.TAX_SCENARIOS}
        for s in strategies:
            eng = bs.simulate(adj, yld, dates, s.step)
            equity = pd.Series(eng.equity, index=dates)
            ideal[s.letter] = float(equity.iloc[-1])
            ideal_curves[s.letter] = equity
            rows.append(bs.metrics(s.letter, s.name, "ideal", equity, eng.trades, 0.0, 0.0) | {"entry": label})
            for scenario, state_rate, wash_on in bs.TAX_SCENARIOS:
                taxed, total_tax, wash, taxed_eng = bs.run_taxed(
                    adj, yld, dates,
                    lambda letter=s.letter: next(x.step for x in build_strategies(adj, dates, base, lev) if x.letter == letter),
                    state_rate, wash_on)
                rows.append(bs.metrics(s.letter, s.name, scenario, taxed, taxed_eng.trades, total_tax, wash) | {"entry": label})
                taxed_curves[scenario][s.letter] = taxed

        curves = taxed_curves["federal+CA"]
        final_tax = {letter: float(eq.iloc[-1]) for letter, eq in curves.items()}
        bs.make_chart(strategies, curves, ideal, final_tax, entry, out_dir / f"chart_{label}.png")
        if i == 0:
            bs.write_rules(strategies, out_dir / "rules.md")
        print(f"[{i + 1}/{len(entries)}] {label}  {dates[0]:%Y-%m-%d} -> {dates[-1]:%Y-%m-%d}", flush=True)

    summary = pd.DataFrame(rows)
    summary.to_csv(out_dir / "summary_all.csv", index=False)
    print(f"\nWrote {len(entries)} entries to {out_dir}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pair", choices=sorted(PAIRS))
    args = parser.parse_args()
    run(args.pair)


if __name__ == "__main__":
    main()
