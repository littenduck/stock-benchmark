"""Backtest of classic stock strategies from the 2021-11-22 QQQ peak, 100k each.

Letters group the strategies: A-B buy and hold, C-D dollar-cost averaging,
E-K moving-average trend, L-O other technical indicators, P-S allocation,
T sector rotation, U high-dividend holding, and V-X risk control and position rules.

Market assumptions
  Trades fill at the close of the signal day, with no spread, slippage or commission.
  Prices are total-return prices (dividends reinvested). ETF expense ratios are
  already in the price. Dividends are also taxed as income each year, even though
  they are reinvested.

Tax assumptions (US, top-bracket investor, calendar tax years)
  short-term gain (held 1 year or less): 37% + 3.8% NIIT, plus state
  long-term gain (held more than 1 year): 20% + 3.8% NIIT, plus state
  state tax treats all gains and dividends at the top rate (CA: 13.3%)
  equity ETF dividends are qualified (long-term rate); TLT, IEF, DBC dividends are
  ordinary (short-term rate). Dividends are not netted against capital losses.
  losses net within the same term and year, then across terms, then carry forward
  without limit. The $3,000 ordinary-income deduction is ignored.
  wash sale: a loss is disallowed if the same ETF was bought within 30 days either
  side and the replacement was not sold on or before the loss sale.
  Tax for each year is paid on the last trading day of the year, out of the portfolio:
  cash first, then shares sold pro rata (those sales are taxed too). So later returns
  compound on the after-tax value. The position still held at the end is treated as
  sold on the last day, and its tax is paid that day.
  Simplification: reinvested dividends add no basis, which slightly overstates tax.

Outputs for the 2021-11-22 entry also include equity_static.png, equity_animation.gif
and equity_curves_*.csv, which cover the six plans A, B, C, D, E, G (the curves CSVs
cover every strategy). These replace the former backtest_peak_2021.py. Its letters
were different: biweekly DCA was F (now D), SMA 225 was D (now E), MA 100/225 was E (now G).

Run:  python3 scripts/backtest_strategies.py
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import time
from pathlib import Path
from typing import Callable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import yfinance as yf  # noqa: E402
from matplotlib.animation import FuncAnimation, PillowWriter  # noqa: E402

from backend.shared import project_paths

START = "2021-11-22"
CAPITAL = 100_000.0
MONTHLY = 1_500.0
BIWEEKLY = 1_000.0
FEDERAL_ORDINARY = 0.37
FEDERAL_LTCG = 0.20
NIIT = 0.038
CA_TOP_RATE = 0.133  # 12.3% top bracket + 1% mental health surcharge
WASH_DAYS = 30
OUT_DIR = Path(project_paths.RUNTIME_DIRECTORY) / "backtest"

SECTORS = ["XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLI", "XLU", "XLB", "XLRE", "XLC"]
TICKERS = ["QQQ", "TQQQ", "SPY", "TLT", "IEF", "GLD", "DBC", "SCHD", *SECTORS]
# Tickers that must have data on a day. TQQQ (2010) and SCHD (2011) are left out, so
# the QQQ signal history is kept. A strategy that trades them waits for its first price.
CORE_TICKERS = ["QQQ", "SPY", "TLT", "IEF", "GLD", "DBC"]
# Bond and commodity distributions are ordinary income, equity ETF dividends are qualified.
ORDINARY_DIVIDEND = {"TLT", "IEF", "DBC"}
# Tax scenarios: name, state tax rate, wash-sale rule on. The state rate is added to each federal rate.
# "CA no wash" isolates the wash-sale effect. "fed only" is for a state with no income tax.
TAX_SCENARIOS = [
    ("federal+CA", CA_TOP_RATE, True),
    ("CA no wash", CA_TOP_RATE, False),
    ("fed only", 0.0, True),
]


def load_market() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Total-return prices and dividend yields on each ex-dividend day.

    Adjusted close already reinvests dividends, so growth comes from the price path.
    Yield is dividend divided by the unadjusted close, and it sizes the dividend
    income that is taxed each year.
    """
    # Start in 2009 so the 225-day SMA is ready for an April 2010 entry. Sector
    # ETFs such as XLC start later, so only the core tickers must have data on a day.
    raw = yf.download(TICKERS, start="2009-01-01", auto_adjust=False, actions=True, progress=False)
    adj = raw["Adj Close"][TICKERS]
    adj = adj.dropna(subset=CORE_TICKERS)
    close = raw["Close"][TICKERS].reindex(adj.index)
    div = raw["Dividends"][TICKERS].reindex(adj.index).fillna(0.0)
    return adj, (div / close).fillna(0.0)


def is_long_term(bought: pd.Timestamp, sold: pd.Timestamp) -> bool:
    # Long-term means held MORE than one year.
    return sold > bought + pd.DateOffset(years=1)


@dataclass
class Lot:
    # One purchase. Lots are sold first-in first-out.
    ticker: str
    purchased: pd.Timestamp
    shares: float
    unit: float  # price per share at purchase (adjusted scale)

    def __post_init__(self) -> None:
        self.open = self.shares  # shares still held
        self.first_sell: pd.Timestamp | None = None
        self.last_sell: pd.Timestamp | None = None


class Engine:
    """Cash, lots, and a ledger of sales and dividends for one strategy run."""

    def __init__(self, adj: pd.DataFrame, yld: pd.DataFrame, dates: pd.DatetimeIndex) -> None:
        self.adj = adj
        self.yld = yld
        self.dates = dates
        self.cash = CAPITAL
        self.shares = {t: 0.0 for t in TICKERS}
        self.lots_by = {t: [] for t in TICKERS}
        self.sales: list[tuple] = []  # (day, lot, shares, price)
        self.divs: list[tuple] = []  # (day, ticker, dollars)
        self.equity: list[float] = []
        self.trades = 0
        self.unpaid = 0.0  # tax that could not be paid because the portfolio ran out

    def price(self, day: pd.Timestamp, t: str) -> float:
        return float(self.adj.at[day, t])

    def value(self, day: pd.Timestamp) -> float:
        return self.cash + sum(self.shares[t] * self.price(day, t) for t in TICKERS if self.shares[t] > 1e-9)

    def begin_day(self, day: pd.Timestamp) -> None:
        # Dividends are paid on the holdings held before today's trades.
        for t in TICKERS:
            if self.shares[t] > 1e-9 and self.yld.at[day, t] > 0:
                self.divs.append((day, t, self.shares[t] * self.price(day, t) * self.yld.at[day, t]))

    def buy(self, day: pd.Timestamp, t: str, dollars: float) -> None:
        dollars = min(dollars, self.cash)
        if dollars < 1:
            return
        p = self.price(day, t)
        self.lots_by[t].append(Lot(t, day, dollars / p, p))
        self.shares[t] += dollars / p
        self.cash -= dollars
        self.trades += 1

    def sell(self, day: pd.Timestamp, t: str, shares: float) -> None:
        shares = min(shares, self.shares[t])
        if shares < 1e-9:
            return
        p = self.price(day, t)
        need = shares
        for lot in self.lots_by[t]:
            if need <= 1e-12:
                break
            if lot.open <= 1e-12:
                continue
            q = min(lot.open, need)
            lot.open -= q
            need -= q
            lot.first_sell = lot.first_sell if lot.first_sell is not None else day
            lot.last_sell = day
            self.sales.append((day, lot, q, p))
            self.cash += q * p
        self.shares[t] -= shares
        self.trades += 1

    def buy_all(self, day: pd.Timestamp, t: str) -> None:
        self.buy(day, t, self.cash)

    def sell_all(self, day: pd.Timestamp, t: str) -> None:
        self.sell(day, t, self.shares[t])

    def withdraw(self, day: pd.Timestamp, amount: float) -> None:
        """Pay tax out of the portfolio: use cash first, then sell shares pro rata.

        A sale to raise cash is a real sale, so it is recorded in `sales` and taxed.
        """
        paid = min(amount, self.value(day))
        self.unpaid += amount - paid
        from_cash = min(paid, self.cash)
        need = paid - from_cash
        if need > 1e-9:
            held = {t: self.shares[t] * self.price(day, t) for t in TICKERS if self.shares[t] > 1e-9}
            total = sum(held.values())
            for t, v in held.items():
                # The sale adds its proceeds to cash, so take the paid part back out below.
                self.sell(day, t, need * v / total / self.price(day, t))
        self.cash -= paid

    def rebalance(self, day: pd.Timestamp, weights: dict, tol: float = 0.01) -> None:
        """Move holdings to target weights. Skip when every holding is within `tol` of target."""
        total = self.value(day)
        tickers = set(weights) | {t for t in TICKERS if self.shares[t] > 1e-9}
        drift = max(
            abs(self.shares[t] * self.price(day, t) - weights.get(t, 0.0) * total) for t in tickers
        ) / total
        if drift < tol:
            return
        # Sells first, so the cash they raise can fund the buys.
        for t in tickers:
            cur = self.shares[t] * self.price(day, t)
            target = weights.get(t, 0.0) * total
            if cur > target:
                self.sell(day, t, (cur - target) / self.price(day, t))
        for t in tickers:
            cur = self.shares[t] * self.price(day, t)
            target = weights.get(t, 0.0) * total
            if target > cur:
                self.buy(day, t, target - cur)


def simulate(adj: pd.DataFrame, yld: pd.DataFrame, dates: pd.DatetimeIndex, step: Callable,
             taxes: dict | None = None) -> Engine:
    """Run one strategy. `taxes` maps pay days to tax to withdraw from the portfolio that day."""
    eng = Engine(adj, yld, dates)
    for day in dates:
        eng.begin_day(day)
        step(eng, day)
        if taxes and day in taxes:
            eng.withdraw(day, taxes[day])
        eng.equity.append(eng.value(day))
    return eng


def settle_taxes(eng: Engine, dates: pd.DatetimeIndex, state_rate: float, wash_on: bool) -> tuple[dict, float]:
    """Tax paid per day, and total wash-sale losses disallowed in this run."""
    end = dates[-1]
    # The position still held at the end is sold on the last day, for tax purposes only.
    liquidation = [
        (end, lot, lot.open, eng.price(end, lot.ticker))
        for lots in eng.lots_by.values() for lot in lots if lot.open > 1e-9
    ]
    sales = sorted(eng.sales + liquidation, key=lambda s: s[0])

    # Per-lot tax state lives in dicts, so this function does not change the engine.
    lots = [lot for lots in eng.lots_by.values() for lot in lots]
    first_sell = {id(lot): lot.first_sell or end for lot in lots}
    repl_left = {id(lot): lot.shares for lot in lots}
    adjust = {id(lot): 0.0 for lot in lots}  # disallowed losses added to basis, dollars
    buy_day = {id(lot): lot.purchased for lot in lots}

    gains = []
    wash_total = 0.0
    for day, lot, q, price in sales:
        k = id(lot)
        basis_ps = lot.unit + adjust[k] / lot.shares
        raw = q * (price - basis_ps)
        disallowed = 0.0
        if wash_on and raw < 0:
            loss_ps = -raw / q
            need = q
            # Replacement: another lot of the same ETF bought within 30 days, not sold
            # before this sale. Its shares must still be held after the loss sale.
            for rep in eng.lots_by[lot.ticker]:
                rk = id(rep)
                if rep is lot or repl_left[rk] <= 1e-9:
                    continue
                if abs((rep.purchased - day).days) > WASH_DAYS:
                    continue
                if first_sell[rk] <= day:
                    continue
                use = min(need, repl_left[rk])
                repl_left[rk] -= use
                amount = loss_ps * use
                adjust[rk] += amount
                buy_day[rk] = min(buy_day[rk], buy_day[k])  # holding period tacks
                disallowed += amount
                need -= use
                if need <= 1e-9:
                    break
            wash_total += disallowed
        gains.append((day, raw + disallowed, is_long_term(buy_day[k], day)))

    short_rate = FEDERAL_ORDINARY + NIIT + state_rate
    long_rate = FEDERAL_LTCG + NIIT + state_rate
    div_q, div_o = defaultdict(float), defaultdict(float)
    for day, t, dollars in eng.divs:
        (div_o if t in ORDINARY_DIVIDEND else div_q)[day.year] += dollars

    tax_by_day: dict[pd.Timestamp, float] = {}
    carry_st = carry_lt = 0.0
    for year in sorted(set(dates.year)):
        rows = [g for g in gains if g[0].year == year]
        st = sum(g for _, g, long in rows if not long) + carry_st
        lt = sum(g for _, g, long in rows if long) + carry_lt
        # Different terms net against each other first. Any loss left over carries forward.
        if st < 0 < lt:
            offset = min(-st, lt)
            st, lt = st + offset, lt - offset
        elif lt < 0 < st:
            offset = min(-lt, st)
            st, lt = st - offset, lt + offset
        cap_tax = max(st, 0) * short_rate + max(lt, 0) * long_rate
        div_tax = div_q[year] * long_rate + div_o[year] * short_rate
        carry_st, carry_lt = min(st, 0), min(lt, 0)
        pay_day = dates[dates.year == year][-1]
        tax_by_day[pay_day] = tax_by_day.get(pay_day, 0.0) + cap_tax + div_tax
    return tax_by_day, wash_total


def run_taxed(adj: pd.DataFrame, yld: pd.DataFrame, dates: pd.DatetimeIndex, make_step: Callable,
              state_rate: float, wash_on: bool, max_iter: int = 10) -> tuple[pd.Series, float, float, Engine]:
    """Simulate with each year's tax paid out of the portfolio on its pay day.

    The tax depends on the sales, and the sales depend on the tax withdrawn, so this
    repeats the run until each pay day's tax changes by less than one dollar.
    `make_step` must return a fresh step each call, because some steps keep state.
    Returns (equity after tax, total tax, wash-sale losses disallowed, engine).
    """
    taxes: dict = {}
    for _ in range(max_iter):
        eng = simulate(adj, yld, dates, make_step(), taxes)
        new_taxes, wash = settle_taxes(eng, dates, state_rate, wash_on)
        keys = set(taxes) | set(new_taxes)
        if all(abs(taxes.get(k, 0.0) - new_taxes.get(k, 0.0)) < 1.0 for k in keys):
            break
        taxes = new_taxes
    return pd.Series(eng.equity, index=dates), sum(new_taxes.values()), wash, eng


def max_drawdown(equity: pd.Series) -> float:
    return float((equity / equity.cummax() - 1).min())


def state_machine(enter: pd.Series, leave: pd.Series) -> pd.Series:
    """Hold after `enter` is True, drop after `leave` is True, otherwise keep the state."""
    on = False
    out = []
    for e, lv in zip(enter.values, leave.values):
        if on and lv:
            on = False
        elif not on and e:
            on = True
        out.append(on)
    return pd.Series(out, index=enter.index)


def trailing_stop_on(tqqq: pd.Series, qqq: pd.Series, sma: pd.Series, drop: float = 0.30) -> pd.Series:
    """Hold TQQQ. Sell after a 30% fall from the peak since buying. Re-enter when QQQ is above its 200-day SMA."""
    hold, peak = True, None
    out = []
    for p, q, m in zip(tqqq.values, qqq.values, sma.values):
        if hold:
            peak = p if peak is None else max(peak, p)
            if p < peak * (1 - drop):
                hold = False
        elif q > m:  # NaN compares False, so no re-entry during the warm-up
            hold, peak = True, p
        out.append(hold)
    return pd.Series(out, index=tqqq.index)


def rsi(s: pd.Series, n: int = 14) -> pd.Series:
    diff = s.diff()
    up = diff.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    down = (-diff.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / down)


@dataclass
class Strategy:
    letter: str
    label: str  # short English name for the chart
    name: str  # Chinese name for the table
    group: str
    rule: str  # the rule in words, written to the rules file
    step: Callable


def timing_step(ticker: str, on: pd.Series) -> Callable:
    """Hold `ticker` while `on` is True. Enter with all cash, exit to all cash."""
    def step(eng: Engine, day: pd.Timestamp) -> None:
        if on.loc[day] and eng.shares[ticker] <= 1e-9:
            eng.buy_all(day, ticker)
        elif not on.loc[day] and eng.shares[ticker] > 1e-9:
            eng.sell_all(day, ticker)
    return step


def dca_step(days: set, amount: float, ticker: str) -> Callable:
    """Buy `amount` on each day in `days`, funded from the 100k pool. Unspent cash stays idle."""
    def step(eng: Engine, day: pd.Timestamp) -> None:
        if day in days and eng.cash >= amount:
            eng.buy(day, ticker, amount)
    return step


def rebal_step(days: set, weights_fn: Callable) -> Callable:
    def step(eng: Engine, day: pd.Timestamp) -> None:
        if day in days:
            eng.rebalance(day, weights_fn(day))
    return step


def grid_step(initial: float = 50_000.0, pct: float = 0.10, unit: float = 10_000.0) -> Callable:
    """Start with `initial` in TQQQ. Buy `unit` after each 10% fall, sell `unit` after each 10% rise, from the last trade price."""
    state = {"ref": None}

    def step(eng: Engine, day: pd.Timestamp) -> None:
        p = eng.price(day, "TQQQ")
        if state["ref"] is None:
            eng.buy(day, "TQQQ", initial)
            state["ref"] = p
        elif p <= state["ref"] * (1 - pct) and eng.cash >= unit:
            eng.buy(day, "TQQQ", unit)
            state["ref"] = p
        elif p >= state["ref"] * (1 + pct) and eng.shares["TQQQ"] > 1e-9:
            eng.sell(day, "TQQQ", unit / p)
            state["ref"] = p
    return step


def add_on_dip_step(initial_frac: float = 0.5, drop: float = 0.10, add_frac: float = 0.25) -> Callable:
    """Buy TQQQ with 50% of cash. After each 10% fall from the last buy, add 25% of the remaining cash."""
    state = {"last": None}

    def step(eng: Engine, day: pd.Timestamp) -> None:
        p = eng.price(day, "TQQQ")
        if state["last"] is None:
            eng.buy(day, "TQQQ", eng.cash * initial_frac)
            state["last"] = p
        elif p <= state["last"] * (1 - drop) and eng.cash > 1:
            eng.buy(day, "TQQQ", eng.cash * add_frac)
            state["last"] = p
    return step


def build_strategies(adj: pd.DataFrame, dates: pd.DatetimeIndex) -> list[Strategy]:
    start = dates[0]
    # First day SCHD has a price. Its buy-and-hold waits for this day if the entry is earlier.
    schd_day = adj["SCHD"].loc[dates].dropna().index[0]
    qqq, tqqq, tlt = adj["QQQ"], adj["TQQQ"], adj["TLT"]

    def on(s: pd.Series) -> pd.Series:
        return s.loc[dates]

    always = pd.Series(True, index=dates)
    sma200 = qqq.rolling(200).mean()

    # Moving-average signals on QQQ. The state is computed from full history, so a
    # strategy that has been running since before START is in the right state on START.
    sig_100_225 = on(qqq.rolling(100).mean() > qqq.rolling(225).mean())
    sig_50_200 = on(qqq.rolling(50).mean() > qqq.rolling(200).mean())
    sig_5_20 = on(qqq.rolling(5).mean() > qqq.rolling(20).mean())
    sig_20_50 = on(qqq.rolling(20).mean() > qqq.rolling(50).mean())
    sig_20_200 = on(qqq.rolling(20).mean() > qqq.rolling(200).mean())
    sig_sma225 = on(qqq > qqq.rolling(225).mean())
    sig_sma210 = on(qqq > qqq.rolling(210).mean())

    macd = qqq.ewm(span=12, adjust=False).mean() - qqq.ewm(span=26, adjust=False).mean()
    sig_macd = on(macd > macd.ewm(span=9, adjust=False).mean())

    # Turtle breakout: enter above the prior 20-day high, exit below the prior 10-day low.
    sig_turtle = on(state_machine(
        qqq > qqq.rolling(20).max().shift(1),
        qqq < qqq.rolling(10).min().shift(1),
    ))

    rsi14 = rsi(qqq)
    sig_rsi = on(state_machine(rsi14 < 30, rsi14 > 55))

    mid = qqq.rolling(20).mean()
    lower = mid - 2 * qqq.rolling(20).std()
    sig_boll = on(state_machine(qqq < lower, qqq > mid))

    sig_trail = trailing_stop_on(on(tqqq), on(qqq), on(sma200))

    # Calendar sets. Dates come from the trading calendar, so holidays are handled.
    month_firsts = set(pd.Series(dates).groupby(dates.to_period("M")).first()) - {start}
    month_lasts = set(pd.Series(dates).groupby(dates.to_period("M")).last())
    jan_days = set(pd.Series(dates).groupby(dates.year).first()) | {start}
    targets = pd.date_range(start, dates[-1], freq="14D")[1:]
    pos = dates.searchsorted(targets)
    biweekly = set(dates[pos[pos < len(dates)]])

    ret_q = qqq.pct_change(252)
    ret_t = tlt.pct_change(252)
    sec_ret = adj[SECTORS].pct_change(126)

    def dual_weights(day):
        rq, rt = ret_q.get(day), ret_t.get(day)
        if rq is None or pd.isna(rq):
            return {}
        return {"QQQ": 1.0} if rq > 0 and rq > rt else {"TLT": 1.0}

    def sector_weights(day):
        top = sec_ret.loc[day].dropna().nlargest(3)
        return {t: 1 / 3 for t in top.index} if len(top) == 3 else {}

    all_weather = {"SPY": 0.30, "TLT": 0.40, "IEF": 0.15, "GLD": 0.075, "DBC": 0.075}
    permanent = {"SPY": 0.25, "TLT": 0.25, "GLD": 0.25}  # the remaining 25% is cash
    sixty_forty = {"QQQ": 0.60, "TLT": 0.40}

    return [
        Strategy("A", "QQQ buy & hold", "QQQ all-in hold", "benchmark",
                 "Buy QQQ with all 100k on START, hold to the end.",
                 timing_step("QQQ", always)),
        Strategy("B", "TQQQ buy & hold", "TQQQ all-in hold", "benchmark",
                 "Buy TQQQ with all 100k on START, hold to the end.",
                 timing_step("TQQQ", always)),
        Strategy("C", "QQQ monthly DCA 1500", "QQQ monthly DCA 1500", "DCA",
                 "On the first trading day of each month, buy 1500 of QQQ from the 100k pool. Unspent cash is idle.",
                 dca_step(month_firsts, MONTHLY, "QQQ")),
        Strategy("D", "QQQ biweekly DCA 1000", "QQQ biweekly DCA 1000", "DCA",
                 "Every 14 days from START, buy 1000 of QQQ from the 100k pool. Stops when cash runs out (about 100 buys).",
                 dca_step(biweekly, BIWEEKLY, "QQQ")),
        Strategy("E", "SMA 225 single, TQQQ", "SMA 225 single line → TQQQ", "moving average",
                 "Signal: QQQ close above its 225-day SMA: all-in TQQQ. Below: all cash.",
                 timing_step("TQQQ", sig_sma225)),
        Strategy("F", "SMA 50/200 cross, TQQQ", "SMA 50/200 golden/death cross → TQQQ", "moving average",
                 "Signal: 50-day SMA vs 200-day SMA of QQQ. Golden cross (50 above 200): all-in TQQQ. Death cross: all cash.",
                 timing_step("TQQQ", sig_50_200)),
        Strategy("G", "SMA 100/225 cross, TQQQ", "SMA 100/225 golden/death cross → TQQQ", "moving average",
                 "Signal: 100-day SMA of QQQ vs 225-day SMA. Golden cross (100 above 225): all-in TQQQ. Death cross: all cash.",
                 timing_step("TQQQ", sig_100_225)),
        Strategy("H", "SMA 5/20 cross, TQQQ", "SMA 5/20 golden/death cross → TQQQ", "moving average",
                 "Signal: 5-day SMA of QQQ vs 20-day SMA. Golden cross (5 above 20): all-in TQQQ. Death cross: all cash.",
                 timing_step("TQQQ", sig_5_20)),
        Strategy("I", "SMA 20/50 cross, TQQQ", "SMA 20/50 golden/death cross → TQQQ", "moving average",
                 "Signal: 20-day SMA of QQQ vs 50-day SMA. Golden cross (20 above 50): all-in TQQQ. Death cross: all cash.",
                 timing_step("TQQQ", sig_20_50)),
        Strategy("J", "SMA 20/200 cross, TQQQ", "SMA 20/200 golden/death cross → TQQQ", "moving average",
                 "Signal: 20-day SMA of QQQ vs 200-day SMA. Golden cross (20 above 200): all-in TQQQ. Death cross: all cash.",
                 timing_step("TQQQ", sig_20_200)),
        Strategy("K", "10-month SMA trend, QQQ", "10-month SMA (210 days) → QQQ", "moving average",
                 "Signal: QQQ close above its 210-day SMA (about 10 months): all-in QQQ. Below: all cash. Faber 2007 style.",
                 timing_step("QQQ", sig_sma210)),
        Strategy("L", "MACD 12/26/9, TQQQ", "MACD golden/death cross → TQQQ", "indicator",
                 "Signal: MACD line (EMA12 − EMA26 of QQQ) vs its 9-day EMA. Above: all-in TQQQ. Below: all cash.",
                 timing_step("TQQQ", sig_macd)),
        Strategy("M", "Turtle 20/10 breakout, TQQQ", "Turtle breakout 20/10 → TQQQ", "indicator",
                 "Enter TQQQ when QQQ closes above its prior 20-day high. Exit to cash when QQQ closes below its prior 10-day low.",
                 timing_step("TQQQ", sig_turtle)),
        Strategy("N", "RSI(14) 30/55, TQQQ", "RSI(14) oversold 30 in / 55 out → TQQQ", "indicator",
                 "Enter TQQQ when QQQ RSI(14) falls below 30. Exit to cash when RSI rises above 55.",
                 timing_step("TQQQ", sig_rsi)),
        Strategy("O", "Bollinger 20,2σ, TQQQ", "Bollinger 20,2σ mean reversion → TQQQ", "indicator",
                 "Enter TQQQ when QQQ closes below the lower band (20-day SMA − 2 std). Exit to cash when it closes above the 20-day SMA.",
                 timing_step("TQQQ", sig_boll)),
        Strategy("P", "Dual momentum QQQ/TLT", "Dual momentum QQQ/TLT (month-end rebalance)", "allocation",
                 "Month-end: if QQQ 12-month return is above zero and above TLT's, hold QQQ 100%. Otherwise hold TLT 100%.",
                 rebal_step(month_lasts, dual_weights)),
        Strategy("Q", "All Weather", "All Weather 30/40/15/7.5/7.5 (annual rebalance)", "allocation",
                 "SPY 30%, TLT 40%, IEF 15%, GLD 7.5%, DBC 7.5%. Set on START, rebalanced each January.",
                 rebal_step(jan_days, lambda d: all_weather)),
        Strategy("R", "Permanent Portfolio", "Permanent Portfolio 25/25/25/25 (annual rebalance)", "allocation",
                 "SPY 25%, TLT 25%, GLD 25%, cash 25%. Set on START, rebalanced each January.",
                 rebal_step(jan_days, lambda d: permanent)),
        Strategy("S", "60/40 QQQ/TLT", "Stock/bond 60/40 QQQ/TLT (annual rebalance)", "allocation",
                 "QQQ 60%, TLT 40%. Set on START, rebalanced each January.",
                 rebal_step(jan_days, lambda d: sixty_forty)),
        Strategy("T", "Sector rotation top 3", "Sector rotation, top 3 by 6-month momentum (month-end)", "rotation",
                 "Month-end: rank 11 sector ETFs by 6-month return, hold the top 3 equally weighted.",
                 rebal_step(month_lasts, sector_weights)),
        Strategy("U", "SCHD buy & hold", "High-dividend SCHD hold", "income",
                 "Buy SCHD with all 100k on START, hold to the end.",
                 rebal_step({schd_day}, lambda d: {"SCHD": 1.0})),
        Strategy("V", "Trailing stop 30%, TQQQ", "Trailing stop 30%, re-enter when QQQ is above its 200-day SMA (TQQQ)", "risk control",
                 "Hold TQQQ. Sell all after a 30% fall from the peak since buying. Re-enter TQQQ when QQQ closes above its 200-day SMA.",
                 timing_step("TQQQ", sig_trail)),
        Strategy("W", "Grid TQQQ", "Grid trading TQQQ (10% steps, 10k per cell)", "risk control",
                 "Start with 50k in TQQQ. Each 10% fall from the last trade price buys 10k. Each 10% rise sells 10k.",
                 grid_step()),
        Strategy("X", "Add on 10% dips, TQQQ", "Add on dips TQQQ (add 25% of remaining cash per 10% fall)", "risk control",
                 "Start by buying TQQQ with 50% of cash. Each 10% fall from the last buy adds 25% of the remaining cash. Never sells.",
                 add_on_dip_step()),
    ]


def metrics(letter: str, name: str, scenario: str, equity: pd.Series, trades: int,
            total_tax: float, wash: float) -> dict:
    final = float(equity.iloc[-1])
    return {
        "letter": letter,
        "plan": name,
        "scenario": scenario,
        "final_value": round(final, 2),
        "profit": round(final - CAPITAL, 2),
        "return_pct": round((final / CAPITAL - 1) * 100, 1),
        "max_drawdown_pct": round(max_drawdown(equity) * 100, 1),
        "trades": trades,
        "total_tax": round(total_tax, 2),
        "wash_loss_disallowed": round(wash, 2),
    }


def write_rules(strategies: list[Strategy], path: Path) -> None:
    lines = ["| Letter | Strategy | Group | Rule |", "|---|---|---|---|"]
    for s in strategies:
        lines.append(f"| {s.letter} | {s.name} | {s.group} | {s.rule} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_chart(strategies: list[Strategy], curves: dict, ideal: dict, final_tax: dict, entry: str, path: Path) -> None:
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 14), gridspec_kw={"height_ratios": [3, 2]})
    colors = plt.cm.gist_rainbow(np.linspace(0, 0.95, len(strategies)))  # one distinct color per letter
    for s, color in zip(strategies, colors):
        eq = curves[s.letter]
        ax1.plot(eq.index, eq.values, lw=1.4, color=color, label=f"{s.letter} {s.label}")
    ax1.axhline(CAPITAL, color="grey", ls="--", lw=1)
    ax1.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"${v/1000:,.0f}k"))
    ax1.set_title(f"After-tax equity curves (federal + CA tax) from {entry}, 100k each")
    ax1.grid(alpha=0.3)
    ax1.legend(fontsize=7, ncol=3, loc="upper left", frameon=False)

    x = np.arange(len(strategies))
    w = 0.4
    ax2.bar(x - w / 2, [ideal[s.letter] for s in strategies], w, label="ideal (no tax)")
    ax2.bar(x + w / 2, [final_tax[s.letter] for s in strategies], w, label="after federal + CA tax")
    ax2.axhline(CAPITAL, color="grey", ls="--", lw=1)
    ax2.set_xticks(x)
    ax2.set_xticklabels([s.letter for s in strategies])
    ax2.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"${v/1000:,.0f}k"))
    ax2.set_title("Final value by strategy")
    ax2.grid(alpha=0.3, axis="y")
    ax2.legend(fontsize=9, frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def make_static_chart(equity: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(11, 6.2), dpi=120)
    for col in equity.columns:
        ax.plot(equity.index, equity[col], lw=1.8, label=col)
    ax.axhline(CAPITAL, color="grey", ls="--", lw=1)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"${v/1000:,.0f}k"))
    # Static chart uses the ideal curves only. Taxes are in the table.
    ax.set_title("Equity curves from 2021-11-22 (100k start, ideal, no tax)")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left", fontsize=9, frameon=False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def make_animation(equity: pd.DataFrame, path: Path) -> None:
    colors = dict(zip(equity.columns, plt.cm.tab10.colors))
    fig, ax = plt.subplots(figsize=(11, 6.2), dpi=110)
    dates = equity.index
    lines = {}
    for col in equity.columns:
        (line,) = ax.plot([], [], lw=2.2, color=colors[col], label=col)
        lines[col] = line
    ax.axhline(CAPITAL, color="grey", ls="--", lw=1, label="Starting 100k")
    ax.set_xlim(dates[0], dates[-1])
    lo = min(equity.min().min(), CAPITAL) * 0.9
    hi = equity.max().max() * 1.08
    ax.set_ylim(lo, hi)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"${v/1000:,.0f}k"))
    ax.set_title("Starting at the 2021-11-22 QQQ peak with 100k each (ideal, no tax)")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left", fontsize=9, frameon=False)
    date_text = ax.text(0.99, 0.03, "", transform=ax.transAxes, ha="right", fontsize=11)

    # One frame per 3 trading days keeps the GIF small and smooth. The last date
    # is always included so the animation ends on the final value.
    frame_idx = list(range(0, len(dates), 3)) + [len(dates) - 1]

    def update(k: int):
        i = frame_idx[k]
        for col, line in lines.items():
            line.set_data(dates[: i + 1], equity[col].values[: i + 1])
        date_text.set_text(f"{dates[i]:%Y-%m-%d}   " + "   ".join(
            f"{col.split()[0]}: ${equity[col].iloc[i]/1000:,.1f}k" for col in equity.columns
        ))
        return [*lines.values(), date_text]

    anim = FuncAnimation(fig, update, frames=len(frame_idx), interval=50, blit=False)
    anim.save(path, writer=PillowWriter(fps=20))
    plt.close(fig)


def scenario_slug(name: str) -> str:
    return name.replace("+", "_").replace(" ", "_")


def save_peak_outputs(strategies: list[Strategy], ideal_curves: dict, taxed_curves: dict) -> None:
    """Curves CSVs for every scenario, plus the static chart and animation of the six peak plans."""
    names = {s.letter: f"{s.letter} {s.label}" for s in strategies}
    for scenario, by_letter in [("ideal", ideal_curves), *taxed_curves.items()]:
        df = pd.DataFrame({names[k]: v for k, v in by_letter.items()})
        df.round(2).to_csv(OUT_DIR / f"equity_curves_{scenario_slug(scenario)}.csv")
    six = pd.DataFrame({names[k]: ideal_curves[k] for k in PEAK_LETTERS})
    make_static_chart(six, OUT_DIR / "equity_static.png")
    make_animation(six, OUT_DIR / "equity_animation.gif")


PEAK_ENTRY = "2021-11-22"
PEAK_LETTERS = ["A", "B", "C", "D", "E", "G"]  # the six plans of the former peak script


# Entry dates for the two peak scenarios. Both run to the same end date.
ENTRY_SCENARIOS = [
    ("2010-02-11 low (QQQ 43.67, TQQQ 0.22)", "2010-02-11"),
    ("2010-04-26 high (QQQ 50.41, TQQQ 0.33)", "2010-04-26"),
    ("2010-07-01 low (QQQ 42.59, TQQQ 0.19)", "2010-07-01"),
    ("2011-02-16 high (QQQ 58.88, TQQQ 0.48)", "2011-02-16"),
    ("2012-04-03 high (QQQ 68.23, TQQQ 0.64)", "2012-04-03"),
    ("2012-06-04 low (QQQ 60.87, TQQQ 0.45)", "2012-06-04"),
    ("2012-09-19 high (QQQ 70.40, TQQQ 0.68)", "2012-09-19"),
    ("2012-11-16 low (QQQ 62.30, TQQQ 0.47)", "2012-11-16"),
    ("2013-05-22 high (QQQ 73.62, TQQQ 0.77)", "2013-05-22"),
    ("2013-06-24 low (QQQ 69.73, TQQQ 0.65)", "2013-06-24"),
    ("2014-03-07 high (QQQ 90.53, TQQQ 1.41)", "2014-03-07"),
    ("2014-04-15 low (QQQ 85.05, TQQQ 1.16)", "2014-04-15"),
    ("2014-09-19 high (QQQ 99.98, TQQQ 1.87)", "2014-09-19"),
    ("2014-10-15 low (QQQ 92.37, TQQQ 1.46)", "2014-10-15"),
    ("2015-07-20 high (QQQ 113.98, TQQQ 2.65)", "2015-07-20"),
    ("2015-08-24 low (QQQ 98.46, TQQQ 1.69)", "2015-08-24"),
    ("2018-10-01 high (QQQ 186.17, TQQQ 8.94)", "2018-10-01"),
    ("2018-12-24 low (QQQ 143.50, TQQQ 3.80)", "2018-12-24"),
    ("2020-02-19 high (QQQ 236.98, TQQQ 14.76)", "2020-02-19"),
    ("2020-03-23 low (QQQ 170.46, TQQQ 4.45)", "2020-03-23"),
    ("2021-11-22 high (QQQ 399.30, TQQQ 42.75)", "2021-11-22"),
    ("2022-10-13 low (QQQ 268.82, TQQQ 9.65)", "2022-10-13"),
    ("2023-07-19 high (QQQ 385.65, TQQQ 23.16)", "2023-07-19"),
    ("2023-10-26 low (QQQ 343.66, TQQQ 15.43)", "2023-10-26"),
    ("2024-03-21 high (QQQ 445.87, TQQQ 31.25)", "2024-03-21"),
    ("2024-04-19 low (QQQ 414.65, TQQQ 24.74)", "2024-04-19"),
    ("2024-07-10 high (QQQ 502.96, TQQQ 42.47)", "2024-07-10"),
    ("2024-08-05 low (QQQ 435.37, TQQQ 26.81)", "2024-08-05"),
    ("2025-02-19 high (QQQ 539.52, TQQQ 45.20)", "2025-02-19"),
    ("2025-04-07 low (QQQ 423.69, TQQQ 20.62)", "2025-04-07"),
    ("2025-08-01 low (QQQ 553.88, TQQQ 41.46)", "2025-08-01"),
    ("2025-10-29 high (QQQ 635.77, TQQQ 60.31)", "2025-10-29"),
    ("2025-11-21 low (QQQ 590.07, TQQQ 47.48)", "2025-11-21"),
    ("2026-01-28 high (QQQ 633.22, TQQQ 57.06)", "2026-01-28"),
    ("2026-03-30 low (QQQ 558.28, TQQQ 37.89)", "2026-03-30"),
    ("2026-06-03 high (QQQ 744.21, TQQQ 86.56)", "2026-06-03"),
    ("2026-06-09 low (QQQ 707.83, TQQQ 73.72)", "2026-06-09"),
    ("2026-07-29 low (QQQ 661.73, TQQQ 57.75)", "2026-07-29"),
    ("2026-08-17 high (QQQ 729.87, TQQQ 76.40)", "2026-08-17"),
    ("2026-09-16 low (QQQ 704.72, TQQQ 67.93)", "2026-09-16"),
    ("2026-10-16 high (QQQ 709.80, TQQQ 68.21)", "2026-10-16"),
    ("2026-10-23 high (QQQ 704.40, TQQQ 66.29)", "2026-10-23"),
]


def fresh_step(adj: pd.DataFrame, dates: pd.DatetimeIndex, letter: str) -> Callable:
    """A new step for one strategy. Steps can keep state, so each run needs its own."""
    return next(s.step for s in build_strategies(adj, dates) if s.letter == letter)


def run_entry(adj: pd.DataFrame, yld: pd.DataFrame, label: str, entry: str) -> pd.DataFrame:
    dates = adj.index[adj.index >= entry]
    strategies = build_strategies(adj, dates)

    rows = []
    ideal: dict[str, float] = {}
    ideal_curves: dict[str, pd.Series] = {}
    # scenario name -> letter -> after-tax equity curve
    taxed_curves: dict[str, dict[str, pd.Series]] = {name: {} for name, _, _ in TAX_SCENARIOS}
    for s in strategies:
        eng = simulate(adj, yld, dates, s.step)
        equity = pd.Series(eng.equity, index=dates)
        ideal[s.letter] = float(equity.iloc[-1])
        ideal_curves[s.letter] = equity
        rows.append(metrics(s.letter, s.name, "ideal", equity, eng.trades, 0.0, 0.0))
        for scenario, state_rate, wash_on in TAX_SCENARIOS:
            taxed, total_tax, wash, taxed_eng = run_taxed(
                adj, yld, dates, lambda letter=s.letter: fresh_step(adj, dates, letter), state_rate, wash_on)
            rows.append(metrics(s.letter, s.name, scenario, taxed, taxed_eng.trades, total_tax, wash))
            taxed_curves[scenario][s.letter] = taxed

    summary = pd.DataFrame(rows)
    summary.insert(0, "entry", label)
    print(f"\n=== {label}  start {entry}  end {dates[-1]:%Y-%m-%d} ===")
    print(summary.to_string(index=False))

    summary.to_csv(OUT_DIR / f"strategies_summary_{label}.csv", index=False)
    curves = taxed_curves["federal+CA"]
    final_tax = {letter: float(eq.iloc[-1]) for letter, eq in curves.items()}
    make_chart(strategies, curves, ideal, final_tax, entry, OUT_DIR / f"strategies_chart_{label}.png")
    if label == ENTRY_SCENARIOS[0][0]:
        write_rules(strategies, OUT_DIR / "strategies_rules.md")
    if entry == PEAK_ENTRY:
        save_peak_outputs(strategies, ideal_curves, taxed_curves)
    return summary


def progress_bar(done: int, total: int, width: int = 30) -> str:
    filled = int(width * done / total)
    return f"[{'#' * filled}{'-' * (width - filled)}] {done}/{total}"


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    adj, yld = load_market()
    pd.set_option("display.width", 240)
    pd.set_option("display.max_columns", 20)
    pd.set_option("display.max_rows", 200)
    total = len(ENTRY_SCENARIOS)
    print(f"Running {total} entry scenarios.", flush=True)
    frames = []
    t0 = time.perf_counter()
    for i, (label, entry) in enumerate(ENTRY_SCENARIOS, 1):
        t_group = time.perf_counter()
        frames.append(run_entry(adj, yld, label, entry))
        group_secs = time.perf_counter() - t_group
        elapsed = time.perf_counter() - t0
        eta = elapsed / i * (total - i)
        print(f"{progress_bar(i, total)}  {label}  group {group_secs:.1f}s  "
              f"elapsed {elapsed:.0f}s  remaining {eta:.0f}s", flush=True)
    pd.concat(frames, ignore_index=True).to_csv(OUT_DIR / "strategies_summary_all.csv", index=False)
    print(f"\nWrote outputs to {OUT_DIR}")


if __name__ == "__main__":
    main()
