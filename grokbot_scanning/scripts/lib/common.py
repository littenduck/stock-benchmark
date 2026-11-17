"""Shared helpers: paths, ticker list, HTTP with graceful failure, Yahoo access."""
import json, re, time, datetime as dt, threading
from pathlib import Path
import requests
import pandas as pd

BASE = Path(__file__).resolve().parents[2]          # /home/box/shared/stock-team
REPORTS = BASE / "reports"
DATA_ROOT = BASE / "data"                            # cross-day history (IV etc.)
ND = "无数据"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
NY = "America/New_York"
ETFS = {"SPY", "QQQ", "SOXX", "DRAM"}
SEMIS = {"SOXX", "DRAM", "SNDK", "MU", "MRVL", "NVDA"}

GAPS = []                     # human readable data gaps collected during a run
_gl = threading.Lock()
def gap(msg):
    with _gl:
        if msg not in GAPS:
            GAPS.append(msg)

def parse_lists():
    """Return ticker list from lists.md TICKERS section (first token of '- XXX' lines)."""
    txt = (BASE / "lists.md").read_text(encoding="utf-8")
    m = re.search(r"^## TICKERS.*?$(.*?)(?=^## )", txt, re.S | re.M)
    out = []
    for line in (m.group(1) if m else "").splitlines():
        mm = re.match(r"\s*-\s*([A-Z][A-Z0-9.\-]*)", line)
        if mm and mm.group(1) not in out:
            out.append(mm.group(1))
    return out

_sess = requests.Session()
_sess.headers.update({"User-Agent": UA, "Accept": "application/json,text/plain,*/*",
                      "Accept-Language": "en-US,en;q=0.9"})

def http_get(url, params=None, timeout=15, retries=2, headers=None, as_json=True, session=None):
    s = session or _sess
    for i in range(retries + 1):
        try:
            r = s.get(url, params=params, timeout=timeout, headers=headers)
            if r.status_code == 200:
                return r.json() if as_json else r.text
            if r.status_code in (401, 403, 404, 418):
                break
        except Exception:
            pass
        time.sleep(0.6 * (i + 1))
    return None

# ---------- Yahoo ----------
_crumb = {"v": None}
_cl = threading.Lock()
def yahoo_crumb():
    with _cl:
        if _crumb["v"] is None:
            try:
                _sess.get("https://fc.yahoo.com", timeout=10)
                r = _sess.get("https://query2.finance.yahoo.com/v1/test/getcrumb", timeout=10)
                _crumb["v"] = r.text.strip() if r.status_code == 200 and len(r.text) < 40 else ""
            except Exception:
                _crumb["v"] = ""
        return _crumb["v"]

def yahoo_chart(symbol, end_date, days=760, interval="1d", prepost=False):
    """OHLCV DataFrame indexed by NY date (Timestamp normalized), truncated to <= end_date."""
    end = dt.datetime.combine(end_date + dt.timedelta(days=1), dt.time(23, 59))
    p2 = int(end.timestamp())
    p1 = int((end - dt.timedelta(days=days)).timestamp())
    d = http_get(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
                 params={"period1": p1, "period2": p2, "interval": interval,
                         "includePrePost": str(prepost).lower(), "events": "div,splits"})
    try:
        res = d["chart"]["result"][0]
        q = res["indicators"]["quote"][0]
        idx = pd.to_datetime(res["timestamp"], unit="s", utc=True).tz_convert(NY)
        df = pd.DataFrame({k: q[k] for k in ("open", "high", "low", "close", "volume")}, index=idx)
        df = df.dropna(subset=["close"])
        if interval == "1d":
            df.index = df.index.normalize().tz_localize(None)
            df = df[~df.index.duplicated(keep="last")]
            df = df[df.index <= pd.Timestamp(end_date)]
        df.attrs["meta"] = res.get("meta", {})
        return df if len(df) else None
    except Exception:
        gap(f"{symbol}: Yahoo K线获取失败")
        return None

def yahoo_json(path, params=None):
    params = dict(params or {})
    c = yahoo_crumb()
    if c:
        params["crumb"] = c
    return http_get("https://query2.finance.yahoo.com" + path, params=params)

def fnum(x, nd=2):
    if x is None:
        return ND
    try:
        if isinstance(x, float) and (x != x):
            return ND
        return f"{x:.{nd}f}"
    except Exception:
        return ND

def raw(d, *keys):
    """Walk Yahoo quoteSummary dict and return .raw value or None."""
    try:
        for k in keys:
            d = d[k]
        if isinstance(d, dict):
            return d.get("raw")
        return d
    except Exception:
        return None

def save_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1, default=str), encoding="utf-8")

def trading_days_between(a, b):
    """Number of weekdays after a up to and including b (holidays ignored)."""
    if a is None or b is None:
        return None
    return int(pd.bdate_range(a + dt.timedelta(days=1), b).size) if b > a else -int(pd.bdate_range(b + dt.timedelta(days=1), a).size)
