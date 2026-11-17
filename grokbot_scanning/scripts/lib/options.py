"""Options panel from Yahoo option chains (live snapshot at fetch time).
Score = net positioning direction from put/call ratios only (volatility level not scored)."""
import csv, math, datetime as dt
import numpy as np
from .common import yahoo_json, gap, DATA_ROOT, trading_days_between

IVH = DATA_ROOT / "iv_history.csv"

def third_friday(d):
    f = dt.date(d.year, d.month, 15)
    return f + dt.timedelta(days=(4 - f.weekday()) % 7)

def chain(sym, exp=None):
    d = yahoo_json(f"/v7/finance/options/{sym}", {"date": exp} if exp else None)
    try:
        return d["optionChain"]["result"][0]
    except Exception:
        return None

def _bs(S, K, T, r, v, call):
    if v <= 0 or T <= 0:
        return max(0.0, (S - K) if call else (K - S))
    d1 = (math.log(S / K) + (r + v * v / 2) * T) / (v * math.sqrt(T)); d2 = d1 - v * math.sqrt(T)
    N = lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2)))
    return S * N(d1) - K * math.exp(-r * T) * N(d2) if call else K * math.exp(-r * T) * N(-d2) - S * N(-d1)

def bs_iv(price, S, K, T, call, r=0.04):
    """Implied vol by bisection; None if price outside no-arbitrage bounds."""
    if not price or price <= 0 or T <= 0:
        return None
    lo, hi = 0.01, 5.0
    if price < _bs(S, K, T, r, lo, call) or price > _bs(S, K, T, r, hi, call):
        return None
    for _ in range(60):
        mid = (lo + hi) / 2
        if _bs(S, K, T, r, mid, call) > price: hi = mid
        else: lo = mid
    return (lo + hi) / 2

def iv_at(rows, k, S=None, T=None, call=True):
    """IV of strike nearest k: Yahoo IV when sane (bid>0, 3%..500%), else Black-Scholes from mid/last price."""
    r = [x for x in rows if x.get("strike")]
    if not r:
        return None
    best = min(r, key=lambda x: abs(x["strike"] - k))
    yiv = best.get("impliedVolatility") or 0
    if (best.get("bid") or 0) > 0 and 0.03 < yiv < 5:
        return yiv
    if S and T:
        b, a = best.get("bid") or 0, best.get("ask") or 0
        px = (b + a) / 2 if b > 0 and a > 0 else best.get("lastPrice")
        return bs_iv(px, S, best["strike"], T, call)
    return None

def max_pain(calls, puts):
    ks = sorted({x["strike"] for x in calls + puts})
    if not ks:
        return None
    best, bv = None, None
    for s in ks:
        v = sum(max(0, s - c["strike"]) * c.get("openInterest", 0) for c in calls) + \
            sum(max(0, p["strike"] - s) * p.get("openInterest", 0) for p in puts)
        if bv is None or v < bv:
            best, bv = s, v
    return best

def load_hist():
    h = {}
    if IVH.exists():
        for row in csv.DictReader(IVH.open()):
            try:
                h.setdefault(row["ticker"], {})[row["date"]] = float(row["atm_iv"])
            except Exception:
                pass
    return h

def save_hist(h):
    IVH.parent.mkdir(parents=True, exist_ok=True)
    with IVH.open("w", newline="") as f:
        w = csv.writer(f); w.writerow(["date", "ticker", "atm_iv"])
        for t in sorted(h):
            for d in sorted(h[t]):
                w.writerow([d, t, f"{h[t][d]:.4f}"])

def analyze(sym, run_date, tech, earnings_date, hist):
    base = chain(sym)
    if not base or not base.get("expirationDates"):
        gap(f"{sym}: 期权链无数据")
        return {"ticker": sym, "ok": False, "score": None, "alert": "绿", "reasons": []}
    q = base.get("quote", {})
    spot = q.get("regularMarketPrice") or (tech or {}).get("close")
    exps = [dt.datetime.utcfromtimestamp(e).date() for e in base["expirationDates"]]
    exps_f = [e for e in exps if e >= run_date]
    if not exps_f:
        return {"ticker": sym, "ok": False, "score": None, "alert": "绿", "reasons": []}
    near = exps_f[0]
    monthly = next((e for e in exps_f if e == third_friday(e) and (e - run_date).days >= 3),
                   next((e for e in exps_f if (e - run_date).days >= 7), exps_f[-1]))
    def get(e):
        if e == exps[0]:
            return base["options"][0]
        c = chain(sym, int(dt.datetime(e.year, e.month, e.day, tzinfo=dt.timezone.utc).timestamp()))
        return c["options"][0] if c and c.get("options") else None
    on, om = get(near), get(monthly) if monthly != near else None
    om = om or on
    if not om:
        gap(f"{sym}: 月度期权链无数据")
        return {"ticker": sym, "ok": False, "score": None, "alert": "绿", "reasons": []}
    calls, puts = om.get("calls", []), om.get("puts", [])
    T = max((monthly - run_date).days, 1) / 365
    ivc, ivp = iv_at(calls, spot, spot, T, True), iv_at(puts, spot, spot, T, False)
    atm = float(np.mean([x for x in (ivc, ivp) if x])) if (ivc or ivp) else None
    if atm is None:
        gap(f"{sym}: 平值IV无数据")
    skew = None
    p95, c105 = iv_at(puts, spot * 0.95, spot, T, False), iv_at(calls, spot * 1.05, spot, T, True)
    if p95 and c105:
        skew = (p95 - c105) * 100
    both = [on] + ([om] if om is not on else [])
    cv = sum(x.get("volume", 0) or 0 for o in both for x in o.get("calls", []))
    pv = sum(x.get("volume", 0) or 0 for o in both for x in o.get("puts", []))
    coi = sum(x.get("openInterest", 0) or 0 for o in both for x in o.get("calls", []))
    poi = sum(x.get("openInterest", 0) or 0 for o in both for x in o.get("puts", []))
    pcr_v = pv / cv if cv else None
    near_k = lambda rows: [x for x in rows if 0.7 * spot <= x["strike"] <= 1.3 * spot]
    calls_n, puts_n = near_k(calls), near_k(puts)
    # Yahoo often reports OI=0 outside market hours -> treat OI as missing when implausibly small
    m_oi = sum(x.get("openInterest", 0) or 0 for x in calls_n + puts_n)
    m_vol = sum(x.get("volume", 0) or 0 for x in calls_n + puts_n)
    oi_ok = m_oi > 0.5 * m_vol and m_oi > 1000
    if not oi_ok:
        gap(f"{sym}: Yahoo持仓量(OI)异常/为0，PCR(OI)、最大痛点、持仓墙无数据")
    pcr_oi = poi / coi if coi and oi_ok else None
    top_c = sorted(calls_n, key=lambda x: x.get("openInterest", 0) or 0, reverse=True)[:2] if oi_ok else []
    top_p = sorted(puts_n, key=lambda x: x.get("openInterest", 0) or 0, reverse=True)[:2] if oi_ok else []
    mp = max_pain(calls_n, puts_n) if oi_ok else None
    days = max((monthly - run_date).days, 1)
    sigma = spot * atm * math.sqrt(days / 365) if atm else None
    unusual = []
    for o in ([om] if oi_ok else []):
        for side in ("calls", "puts"):
            for x in o.get(side, []):
                v, oi = x.get("volume", 0) or 0, x.get("openInterest", 0) or 0
                prem = v * (x.get("lastPrice") or 0) * 100
                if oi > 0 and v > 5 * oi and prem >= 1e6:
                    unusual.append((x.get("contractSymbol"), v, oi))
    unusual = sorted(unusual, key=lambda z: -z[1])[:3]
    # IV history / rank
    th = hist.setdefault(sym, {})
    prev_iv = None
    prior = sorted(d for d in th if d < str(run_date))
    if prior:
        prev_iv = th[prior[-1]]
    if atm:
        th[str(run_date)] = float(atm)
    vals = [th[d] for d in sorted(th) if d <= str(run_date)][-252:]
    ivr = ((atm - min(vals)) / (max(vals) - min(vals)) * 100) if atm and len(vals) >= 20 and max(vals) > min(vals) else None
    iv_chg = ((atm / prev_iv - 1) * 100) if atm and prev_iv else None
    # score: net positioning direction (PCR volume + PCR OI)
    votes = 0
    if pcr_v is not None:
        votes += 1 if pcr_v < 0.7 else -1 if pcr_v > 1.2 else 0
    if pcr_oi is not None:
        votes += 1 if pcr_oi < 0.7 else -1 if pcr_oi > 1.3 else 0
    score = int(np.sign(votes)) if pcr_v is not None or pcr_oi is not None else None
    reasons = []
    td = trading_days_between(run_date, earnings_date) if earnings_date else None
    if td is not None and 0 <= td <= 5:
        reasons.append(f"财报{earnings_date:%m-%d}")
    if iv_chg is not None and abs(iv_chg) > 10:
        reasons.append(f"IV{iv_chg:+.0f}%")
    if unusual:
        reasons.append("异常大单")
    hv20 = (tech or {}).get("hv20")
    r2 = lambda x, n=2: None if x is None else round(float(x), n)
    return {
        "ticker": sym, "ok": True, "snapshot": "抓取时实时期权链", "spot": r2(spot),
        "near_expiry": str(near), "monthly_expiry": str(monthly),
        "oi_ok": oi_ok, "atm_iv_pct": r2(atm * 100 if atm else None, 1), "iv_rank": r2(ivr, 0), "iv_hist_n": len(vals),
        "iv_day_chg_pct": r2(iv_chg, 1), "hv20": hv20, "iv_minus_hv20": r2(atm * 100 - hv20, 1) if atm and hv20 else None,
        "skew_95p_105c_volpts": r2(skew, 1),
        "pcr_vol": r2(pcr_v), "pcr_oi": r2(pcr_oi), "call_vol": cv, "put_vol": pv, "call_oi": coi, "put_oi": poi,
        "top_call_oi": [(x["strike"], x.get("openInterest")) for x in top_c],
        "top_put_oi": [(x["strike"], x.get("openInterest")) for x in top_p],
        "max_pain": mp, "sigma1_monthly": [r2(spot - sigma), r2(spot + sigma)] if sigma else None,
        "unusual": unusual, "earnings_date": str(earnings_date) if earnings_date else None,
        "score": score, "confidence": "低", "alert": "黄" if reasons else "绿", "reasons": reasons,
    }
