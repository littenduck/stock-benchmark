"""Fetch daily OHLCV from Yahoo Finance, compute indicators, and write a Robinhood-style chart page.

Outputs (in backtest_output/):
  ../data/raw/<SYMBOL>_<interval>.csv   1m, 1h and 1d OHLCV, compact CSV (see save_raw)
  chart.html              interactive candlestick page (TradingView lightweight-charts)
  chart_<SYMBOL>.png      static copy of the last year, for the Markdown report

Prices: Open/High/Low/Close are split-adjusted but NOT dividend-adjusted, which is what
Robinhood and TradingView show. (The backtests use Adj Close, a total-return price.)

Run:  python3 scripts/make_chart.py [SYMBOL ...]      default: QQQ TQQQ SOXX SOXL
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import yfinance as yf  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "backtest_output"
RAW_DIR = ROOT / "data" / "raw"
INTERVAL_LIST = {"1m": {"period": "7d"}, "1h": {"period": "730d"}, "1d": {"start": "2000-01-01"}}
DEFAULT_SYMBOLS = ["QQQ", "TQQQ", "SOXX", "SOXL"]
TEMPLATE_PATH = Path(__file__).resolve().parent / "chart_template.html"
CSS_PATH = ROOT / "static" / "base.css"
ICONS_PATH = ROOT / "static" / "icons.svg"
VERSION_PATH = ROOT / "VERSION"
UP, DOWN = "#00C805", "#FF5000"  # Robinhood green and red
# Installed by `npm install` from package.json (lightweight-charts, pinned to 5.0.0).
LIB_PATH = Path(__file__).resolve().parent.parent / "node_modules/lightweight-charts/dist/lightweight-charts.standalone.production.js"


def fetch(symbol: str, interval: str) -> pd.DataFrame:
    """Regular-session OHLCV in New York time, split-adjusted but not dividend-adjusted."""
    raw = yf.download(symbol, interval=interval, auto_adjust=False, prepost=False, progress=False, **INTERVAL_LIST[interval])
    raw.columns = raw.columns.get_level_values(0)
    df = raw[["Open", "High", "Low", "Close", "Volume"]].dropna()
    df.index = pd.to_datetime(df.index)
    if df.index.tz is not None:
        df.index = df.index.tz_convert("America/New_York").tz_localize(None)
    df.index.name = "Date"
    return df


def save_raw(symbol: str, interval: str, df: pd.DataFrame) -> Path:
    """Compact CSV: 4-decimal prices, whole-number volume, no seconds or time zone."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out = df.round(4)
    out["Volume"] = out["Volume"].astype("int64")
    date_format = "%Y-%m-%d" if interval == "1d" else "%Y-%m-%d %H:%M"
    path = RAW_DIR / f"{symbol}_{interval}.csv"
    out.to_csv(path, float_format="%.4f", date_format=date_format)
    return path


def wilder(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def indicators(df: pd.DataFrame) -> pd.DataFrame:
    c, h, l = df["Close"], df["High"], df["Low"]
    out = pd.DataFrame(index=df.index)
    for n in (20, 50, 200):
        out[f"sma{n}"] = c.rolling(n).mean()
    for n in (12, 26):
        out[f"ema{n}"] = c.ewm(span=n, adjust=False).mean()
    out["macd"] = out["ema12"] - out["ema26"]
    out["signal"] = out["macd"].ewm(span=9, adjust=False).mean()
    out["hist"] = out["macd"] - out["signal"]
    # ADX (Wilder, 14): trend strength from smoothed directional movement.
    up, down = h.diff(), -l.diff()
    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = wilder(tr, 14)
    out["plus_di"] = 100 * wilder(pd.Series(plus_dm, index=df.index), 14) / atr
    out["minus_di"] = 100 * wilder(pd.Series(minus_dm, index=df.index), 14) / atr
    dx = 100 * (out["plus_di"] - out["minus_di"]).abs() / (out["plus_di"] + out["minus_di"])
    out["adx"] = wilder(dx, 14)
    return out


def time_list(index: pd.DatetimeIndex, interval: str) -> list:
    if interval == "1d":
        return list(index.strftime("%Y-%m-%d"))
    # New York wall-clock time stored as UTC seconds, so the chart axis shows exchange time.
    return [int(t) for t in index.asi8 // 10**9]


def series(times: list, values: pd.Series) -> list:
    return [{"time": t, "value": round(float(v), 4)} for t, v in zip(times, values) if pd.notna(v)]


def payload(df: pd.DataFrame, ind: pd.DataFrame, interval: str) -> dict:
    times = time_list(df.index, interval)
    candles = [
        {"time": t, "open": round(o, 4), "high": round(h, 4), "low": round(l, 4), "close": round(c, 4)}
        for t, o, h, l, c in zip(times, df.Open, df.High, df.Low, df.Close)
    ]
    volume = [
        {"time": t, "value": int(v), "color": (UP if c >= o else DOWN) + "66"}
        for t, v, o, c in zip(times, df.Volume, df.Open, df.Close)
    ]
    data = {"candles": candles, "volume": volume}
    for col in ind.columns:
        data[col] = series(times, ind[col])
    data["hist"] = [
        {"time": t, "value": round(float(v), 4), "color": UP if v >= 0 else DOWN}
        for t, v in zip(times, ind["hist"]) if pd.notna(v)
    ]
    return data


def png(symbol: str, df: pd.DataFrame, ind: pd.DataFrame, path: Path, days: int = 250) -> None:
    d, i = df.iloc[-days:], ind.iloc[-days:]
    x = np.arange(len(d))
    fig, (ax, am, ad) = plt.subplots(3, 1, figsize=(11, 8), sharex=True,
                                     gridspec_kw={"height_ratios": [3, 1, 1]})
    colors = np.where(d.Close >= d.Open, UP, DOWN)
    ax.vlines(x, d.Low, d.High, color=colors, linewidth=0.8)
    ax.bar(x, d.Close - d.Open, bottom=d.Open, color=colors, width=0.7)
    for col, color in (("sma20", "#F5A623"), ("sma50", "#4A90E2"), ("sma200", "#9013FE")):
        ax.plot(x, i[col], color=color, linewidth=1.2, label=col.upper())
    ax.legend(loc="upper left", frameon=False, ncol=3)
    ax.set_title(f"{symbol}  {d.Close.iloc[-1]:,.2f}  ({d.Close.iloc[-1] / d.Close.iloc[0] - 1:+.1%} over {days} days)",
                 loc="left")
    am.plot(x, i.macd, color="#4A90E2", linewidth=1, label="MACD")
    am.plot(x, i.signal, color="#F5A623", linewidth=1, label="Signal")
    am.bar(x, i["hist"], color=np.where(i["hist"] >= 0, UP, DOWN), width=0.7)
    am.legend(loc="upper left", frameon=False, ncol=2)
    ad.plot(x, i.adx, color="#222222", linewidth=1.2, label="ADX 14")
    ad.plot(x, i.plus_di, color=UP, linewidth=0.8, label="+DI")
    ad.plot(x, i.minus_di, color=DOWN, linewidth=0.8, label="-DI")
    ad.axhline(25, color="#999999", linewidth=0.6, linestyle="--")
    ad.legend(loc="upper left", frameon=False, ncol=3)
    ticks = np.linspace(0, len(d) - 1, 6).astype(int)
    ad.set_xticks(ticks)
    ad.set_xticklabels([d.index[t].strftime("%Y-%m-%d") for t in ticks])
    for a in (ax, am, ad):
        a.grid(alpha=0.2)
        for side in ("top", "right"):
            a.spines[side].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)




def main() -> None:
    symbols = sys.argv[1:] or DEFAULT_SYMBOLS
    OUT_DIR.mkdir(exist_ok=True)
    data = {}
    for s in symbols:
        frames = {}
        for interval in INTERVAL_LIST:
            df = fetch(s, interval)
            save_raw(s, interval, df)
            frames[interval] = df
            print(f"{s} {interval}: {len(df)} bars, {df.index[0]} to {df.index[-1]}")
        daily = frames["1d"]
        ind = indicators(daily)
        data[s] = {"spark": [round(float(c), 4) for c in daily.Close.iloc[-60:]]}
        for interval, df in frames.items():
            data[s][interval] = payload(df, indicators(df), interval)
        png(s, daily, ind, OUT_DIR / f"chart_{s}.png")
    lib = LIB_PATH.read_text(encoding="utf-8")
    if "</script" in lib.lower():
        sys.exit(f"{LIB_PATH} contains '</script', so it cannot be inlined.")
    html = (TEMPLATE_PATH.read_text(encoding="utf-8")
            .replace("__CSS__", CSS_PATH.read_text(encoding="utf-8"))
            .replace("__ICONS__", ICONS_PATH.read_text(encoding="utf-8"))
            .replace("__VERSION__", VERSION_PATH.read_text(encoding="utf-8").strip())
            .replace("__LIB__", lib)
            .replace("__DATA__", json.dumps(data, separators=(",", ":"))))
    (OUT_DIR / "chart.html").write_text(html, encoding="utf-8")
    print(f"wrote {OUT_DIR / 'chart.html'}")


if __name__ == "__main__":
    main()
