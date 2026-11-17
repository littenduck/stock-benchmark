"""Fundamental numbers from Yahoo quoteSummary. Qualitative judgment (guidance, cycle, scenarios) stays with AI."""
import datetime as dt
from .common import yahoo_json, raw, gap, ETFS

MODS = "calendarEvents,summaryDetail,defaultKeyStatistics,financialData,earningsTrend,recommendationTrend"

def analyze(sym, run_date):
    if sym in ETFS:
        return {"ticker": sym, "ok": False, "etf": True, "score": None, "earnings_date": None,
                "alert": "绿", "reasons": []}
    d = yahoo_json(f"/v10/finance/quoteSummary/{sym}", {"modules": MODS})
    try:
        r = d["quoteSummary"]["result"][0]
    except Exception:
        gap(f"{sym}: 基本面 quoteSummary 无数据")
        return {"ticker": sym, "ok": False, "score": None, "earnings_date": None, "alert": "绿", "reasons": []}
    ed = None
    try:
        ts = r["calendarEvents"]["earnings"]["earningsDate"][0]["raw"]
        ed = dt.datetime.fromtimestamp(ts, dt.timezone(dt.timedelta(hours=-5))).date()
    except Exception:
        pass
    trend = {t.get("period"): t for t in (r.get("earningsTrend", {}) or {}).get("trend", [])}
    def rev(p):
        t = trend.get(p, {}); cur, ago = raw(t, "epsTrend", "current"), raw(t, "epsTrend", "30daysAgo")
        return (cur / ago - 1) * 100 if cur and ago and ago > 0 else None
    def ud(p):
        t = trend.get(p, {}); return raw(t, "epsRevisions", "upLast30days"), raw(t, "epsRevisions", "downLast30days")
    r0q, r0y, r1y = rev("0q"), rev("0y"), rev("+1y")
    up, dn = ud("0y")
    fin = r.get("financialData", {})
    out = {"ticker": sym, "ok": True, "earnings_date": str(ed) if ed else None,
           "trailing_pe": raw(r, "summaryDetail", "trailingPE"), "forward_pe": raw(r, "summaryDetail", "forwardPE"),
           "peg": raw(r, "defaultKeyStatistics", "pegRatio"), "ps": raw(r, "summaryDetail", "priceToSalesTrailing12Months"),
           "market_cap": raw(r, "summaryDetail", "marketCap"),
           "rev_growth": raw(fin, "revenueGrowth"), "eps_growth": raw(fin, "earningsGrowth"),
           "gross_margin": raw(fin, "grossMargins"), "target_mean": raw(fin, "targetMeanPrice"),
           "rec_mean": raw(fin, "recommendationMean"), "n_analysts": raw(fin, "numberOfAnalystOpinions"),
           "eps_rev30_0q_pct": r0q, "eps_rev30_0y_pct": r0y, "eps_rev30_1y_pct": r1y,
           "eps_up30_0y": up, "eps_down30_0y": dn}
    # script score: estimate-revision direction only (fallback when no fresh AI fundamental report)
    votes = [x for x in (r0y, r1y) if x is not None]
    if votes:
        avg = sum(votes) / len(votes)
        out["score"] = 1 if avg > 3 else -1 if avg < -3 else 0
    else:
        out["score"] = None
    out["confidence"] = "低"
    out["alert"], out["reasons"] = "绿", []
    if ed and 0 <= (ed - run_date).days <= 7:
        out["alert"], out["reasons"] = "黄", [f"财报{ed:%m-%d}"]
    out = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in out.items()}
    out["_ed"] = ed
    return out
