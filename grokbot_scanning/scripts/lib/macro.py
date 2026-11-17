"""Macro panel: VIX/VXN/10Y/DXY/HY OAS/CNN F&G/index vs 200DMA. Policy & Fed-path judgment stays with AI."""
import io, datetime as dt
import pandas as pd
from .common import yahoo_chart, http_get, gap, SEMIS

def last_chg(df, k=1):
    if df is None or len(df) <= k:
        return None, None
    a, b = float(df.close.iloc[-1]), float(df.close.iloc[-1 - k])
    return a, a - b

def fred(series, end_date):
    txt = http_get("https://fred.stlouisfed.org/graph/fredgraph.csv",
                   params={"id": series, "cosd": str(end_date - dt.timedelta(days=120))},
                   headers={"User-Agent": "curl/8.5.0", "Accept": "*/*"}, as_json=False, timeout=20, retries=1)
    try:
        df = pd.read_csv(io.StringIO(txt))
        df.columns = ["date", "v"]
        df["v"] = pd.to_numeric(df.v, errors="coerce")
        df["date"] = pd.to_datetime(df.date)
        df = df.dropna()
        return df[df.date <= pd.Timestamp(end_date)]
    except Exception:
        gap(f"FRED {series} 无数据")
        return None

def cnn_fg():
    d = http_get("https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
                 headers={"Referer": "https://edition.cnn.com/", "Origin": "https://edition.cnn.com"})
    try:
        f = d["fear_and_greed"]
        return {"score": round(f["score"], 1), "rating": f["rating"], "ts": f["timestamp"],
                "prev_close": round(f["previous_close"], 1), "week": round(f["previous_1_week"], 1),
                "month": round(f["previous_1_month"], 1)}
    except Exception:
        gap("CNN 恐惧贪婪无数据")
        return None

def fg_band(s):
    return None if s is None else "极度恐惧" if s < 25 else "恐惧" if s < 45 else "中性" if s <= 55 else "贪婪" if s <= 75 else "极度贪婪"

def analyze(run_date, charts, tickers):
    vix, vxn, tnx, dxy, ndx = (charts.get(k) for k in ("^VIX", "^VXN", "^TNX", "DX-Y.NYB", "^NDX"))
    m = {}
    v, dv = last_chg(vix); m["vix"] = v; m["vix_chg_pct"] = (dv / (v - dv) * 100) if v and dv is not None else None
    x, dx_ = last_chg(vxn); m["vxn"] = x; m["vxn_chg_pct"] = (dx_ / (x - dx_) * 100) if x and dx_ is not None else None
    t, dt1 = last_chg(tnx); m["tnx"] = t; m["tnx_1d_bp"] = dt1 * 100 if dt1 is not None else None
    _, dt20 = last_chg(tnx, 20); m["tnx_20d_bp"] = dt20 * 100 if dt20 is not None else None
    d0, dd20 = last_chg(dxy, 20); m["dxy"] = d0; m["dxy_20d_pct"] = dd20 / (d0 - dd20) * 100 if d0 and dd20 is not None else None
    for k in ("^VIX", "^VXN", "^TNX", "DX-Y.NYB"):
        if charts.get(k) is None:
            gap(f"{k} 无数据")
    hy = fred("BAMLH0A0HYM2", run_date)
    if hy is not None and len(hy) > 20:
        m["hy_oas"] = float(hy.v.iloc[-1]); m["hy_date"] = str(hy.date.iloc[-1].date())
        m["hy_4w_bp"] = (float(hy.v.iloc[-1]) - float(hy.v.iloc[-21])) * 100
    fg = cnn_fg(); m["fg"] = fg
    def vs200(df):
        if df is None or len(df) < 200: return None
        return (float(df.close.iloc[-1]) / float(df.close.rolling(200).mean().iloc[-1]) - 1) * 100
    m["ndx_vs200_pct"] = vs200(ndx); m["spy_vs200_pct"] = vs200(charts.get("SPY")); m["qqq_vs200_pct"] = vs200(charts.get("QQQ"))
    sx, qq = charts.get("SOXX"), charts.get("QQQ")
    if sx is not None and qq is not None and len(sx) > 22 and len(qq) > 22:
        m["soxx_vs_qqq_21d"] = ((sx.close.iloc[-1] / sx.close.iloc[-22]) - (qq.close.iloc[-1] / qq.close.iloc[-22])) * 100
    m["vxn_minus_vix"] = (x - v) if x and v else None
    m["vix_band"] = None if v is None else "低" if v < 15 else "正常" if v < 20 else "偏高" if v < 30 else "高"
    m["vxn_band"] = None if x is None else "低" if x < 18 else "正常" if x < 25 else "偏高" if x < 35 else "高"
    # risk-off: >=2 of (vol high band, HY widening fast, NDX below 200DMA). Breadth not scripted.
    ro = [m["vix_band"] == "高" or m["vxn_band"] == "高",
          (m.get("hy_4w_bp") or 0) >= 50,
          (m["ndx_vs200_pct"] is not None and m["ndx_vs200_pct"] < 0)]
    m["risk_off_hits"] = sum(ro); m["risk_off"] = sum(ro) >= 2
    # headwinds / tailwinds -> market base score
    head = sum([(t or 0) >= 4.75 or (m["tnx_20d_bp"] or 0) >= 20, (v or 0) >= 20,
                (m["dxy_20d_pct"] or 0) >= 1.5, (m.get("hy_4w_bp") or 0) >= 25])
    tail = sum([(m["tnx_20d_bp"] or 0) <= -20, v is not None and v < 15,
                (m["dxy_20d_pct"] or 0) <= -1.5, (m.get("hy_4w_bp") or 0) <= -25])
    net = tail - head
    base = -2 if (m["risk_off"] and net < 0) else -1 if net <= -2 else 1 if net >= 2 else 0
    m["head"], m["tail"], m["base_score"] = head, tail, base
    semi_extra = -1 if (m.get("soxx_vs_qqq_21d") or 0) < -5 and (m["vxn_minus_vix"] or 0) > 8 else \
                 1 if (m.get("soxx_vs_qqq_21d") or 0) > 5 and (m["vxn_minus_vix"] or 99) < 5 else 0
    reasons = []
    if (m["vix_chg_pct"] or 0) > 20 or (m["vxn_chg_pct"] or 0) > 20: reasons.append("VIX/VXN单日>20%")
    if m["vix_band"] == "高" or m["vxn_band"] == "高": reasons.append("波动率高档")
    if fg and (fg["score"] < 25 or fg["score"] > 75): reasons.append("F&G极端")
    if m["tnx_1d_bp"] is not None and abs(m["tnx_1d_bp"]) > 10: reasons.append("10Y单日>10bp")
    per = {}
    for s in tickers:
        sc = base + (semi_extra if s in SEMIS else 0)
        per[s] = {"score": max(-2, min(2, sc)), "confidence": "中", "alert": "黄" if reasons else "绿", "reasons": reasons}
    m["fg_band"] = fg_band(fg["score"]) if fg else None
    m = {k: (round(val, 2) if isinstance(val, float) else val) for k, val in m.items()}
    return m, per
