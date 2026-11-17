"""Chief aggregation: weights, hard rules, change detection, red alerts, ledger."""
import json, re, datetime as dt
from .common import REPORTS, BASE, ND, trading_days_between

W = {"macro": 0.20, "fundamental": 0.25, "technical": 0.25, "options": 0.20, "sentiment": 0.10}
CN = {"macro": "宏", "fundamental": "基", "technical": "技", "options": "期", "sentiment": "情"}
FULL = {"macro": "宏观面", "fundamental": "基本面", "technical": "技术面", "options": "期权面", "sentiment": "情绪面"}
MODE_ORDER = {"premarket": 0, "intraday": 1, "postmarket": 2}
RANK = {"绿": 0, "黄": 1, "红": 2, None: 0}

def aggregate(panels, risk_off, earnings_soon):
    """panels: {panel: {score, confidence, stale}} -> (short_total, mid_total, weights_used)"""
    w_used, num = {}, 0.0
    for p, base in W.items():
        r = panels.get(p) or {}
        if r.get("score") is None or r.get("stale"):
            continue
        w = base * (0.5 if r.get("confidence") == "低" else 1.0)
        if p == "technical" and earnings_soon:
            w *= 0.5
        w_used[p] = w
    tw = sum(w_used.values())
    if not tw:
        return None, None, {}
    total = sum(panels[p]["score"] * w for p, w in w_used.items()) / tw
    others = {p: w for p, w in w_used.items() if p != "sentiment"}
    if others:
        o = sum(panels[p]["score"] * w for p, w in others.items()) / sum(others.values())
        if o > 0 and total < 0: total = 0.0
        if o < 0 and total > 0: total = 0.0
    if risk_off:
        total = min(total, 0.0)
    total = max(-2.0, min(2.0, total))
    mids = [panels[p]["score"] for p in ("macro", "fundamental")
            if (panels.get(p) or {}).get("score") is not None and not panels[p].get("stale")]
    mid = round(sum(mids) / len(mids), 1) if mids else None
    return round(total + 1e-9, 1), mid, {p: round(w / tw, 3) for p, w in w_used.items()}

def previous_summary(run_date, mode):
    best = None
    for f in REPORTS.glob("*/summary-*.json"):
        m = re.match(r"summary-(\w+)\.json", f.name)
        if not m or m.group(1) not in MODE_ORDER:
            continue
        key = (f.parent.name, MODE_ORDER[m.group(1)])
        if key < (str(run_date), MODE_ORDER[mode]) and (best is None or key > best[0]):
            best = (key, f)
    if not best:
        return None
    try:
        return json.loads(best[1].read_text())
    except Exception:
        return None

def changes(cur, prev):
    """Per ticker list of change strings + red flag."""
    out = {}
    pt = (prev or {}).get("tickers", {})
    for t, c in cur.items():
        p = pt.get(t)
        ch, red = [], []
        if not p:
            out[t] = (["首次"], red); continue
        for k in ("macro", "fundamental", "technical", "options", "sentiment"):
            a, b = (p.get("scores") or {}).get(k), (c.get("scores") or {}).get(k)
            if a is not None and b is not None and a != b:
                ch.append(f"{CN[k]}{a:+d}→{b:+d}")
                if abs(b - a) >= 2: red.append(f"{CN[k]}评分变{b - a:+d}档")
        if p.get("total") is not None and c.get("total") is not None and abs(c["total"] - p["total"]) >= 0.3:
            ch.append(f"总{p['total']:+.1f}→{c['total']:+.1f}")
        if p.get("state") != c.get("state"):
            ch.append(f"状态{p.get('state')}→{c.get('state')}")
        inv = p.get("invalidation") or {}
        if inv.get("level") and c.get("close"):
            if (inv.get("dir") == "上破" and c["close"] > inv["level"]) or (inv.get("dir") == "下破" and c["close"] < inv["level"]):
                red.append(f"技术失效位{inv['dir']}{inv['level']}")
        out[t] = (ch or ["无变化"], red)
    return out

LEDGER_HDR = "日期 | 标的 | 收盘价 | 宏观 | 基本 | 技术 | 期权 | 情绪 | 总分 | 5日涨跌 | 20日涨跌"

def update_ledger(run_date, rows, closes):
    """rows: list of 11-field lists for run_date. closes: {ticker: pd.Series close indexed by date}.
    Never deletes rows; same date+ticker row is updated in place; backfills 5/20-day returns."""
    path = BASE / "ledger.md"
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else [LEDGER_HDR]
    keep, recs = [], []
    for ln in lines:
        parts = [x.strip() for x in ln.split("|")]
        if len(parts) == 11 and re.match(r"\d{4}-\d{2}-\d{2}$", parts[0]):
            recs.append(parts)
        elif ln.strip() and not ln.startswith("日期"):
            keep.append(ln)
    idx = {(r[0], r[1]): i for i, r in enumerate(recs)}
    for r in rows:
        k = (r[0], r[1])
        if k in idx:
            old = recs[idx[k]]
            r[9], r[10] = old[9], old[10]
            recs[idx[k]] = r
        else:
            idx[k] = len(recs); recs.append(r)
    filled = 0
    for r in recs:
        s = closes.get(r[1])
        if s is None:
            continue
        try:
            base_close = float(r[2])
        except ValueError:
            continue
        dates = [str(d.date()) for d in s.index]
        if r[0] not in dates:
            continue
        i = dates.index(r[0])
        for col, n in ((9, 5), (10, 20)):
            if r[col] in ("", ND) and i + n < len(s):
                r[col] = f"{(float(s.iloc[i + n]) / base_close - 1) * 100:+.2f}%"; filled += 1
            elif r[col] == "":
                r[col] = ND
    out = [LEDGER_HDR] + [" | ".join(r) for r in recs] + keep
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return len(rows), filled
