"""Technical panel: indicators, six-signal state, simple SMC, levels, alerts, score.
Rules mirror 盯盘3 技术面 prompt (see README)."""
import numpy as np, pandas as pd
from .common import ND

def wilder(s, n):
    return s.ewm(alpha=1 / n, adjust=False).mean()

def rsi(c, n=14):
    d = c.diff()
    up, dn = wilder(d.clip(lower=0), n), wilder(-d.clip(upper=0), n)
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))

def atr_adx(df, n=14):
    h, l, c = df.high, df.low, df.close
    pc = c.shift()
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    atr = wilder(tr, n)
    upm, dnm = h.diff(), -l.diff()
    pdm = np.where((upm > dnm) & (upm > 0), upm, 0.0)
    ndm = np.where((dnm > upm) & (dnm > 0), dnm, 0.0)
    pdi = 100 * wilder(pd.Series(pdm, index=df.index), n) / atr
    ndi = 100 * wilder(pd.Series(ndm, index=df.index), n) / atr
    dx = 100 * (pdi - ndi).abs() / (pdi + ndi).replace(0, np.nan)
    return atr, wilder(dx, n), pdi, ndi

def swings(df, k=3):
    """Swing highs/lows: bar high/low strictly beyond k bars on each side. Returns lists of (i, price)."""
    H, L = df.high.values, df.low.values
    sh, sl = [], []
    for i in range(k, len(df) - k):
        if H[i] > H[i - k:i].max() and H[i] > H[i + 1:i + k + 1].max():
            sh.append((i, H[i]))
        if L[i] < L[i - k:i].min() and L[i] < L[i + 1:i + k + 1].min():
            sl.append((i, L[i]))
    return sh, sl

def structure(df, sh, sl, k=3):
    """BOS/CHoCH by close crossing the latest confirmed swing level. Returns (events, bias)."""
    C = df.close.values
    ev, bias = [], None
    last_h = last_l = None
    hi_ptr = lo_ptr = 0
    broken_h = broken_l = None
    for i in range(len(df)):
        while hi_ptr < len(sh) and sh[hi_ptr][0] + k <= i:
            last_h = sh[hi_ptr]; hi_ptr += 1
        while lo_ptr < len(sl) and sl[lo_ptr][0] + k <= i:
            last_l = sl[lo_ptr]; lo_ptr += 1
        if last_h and broken_h != last_h[0] and C[i] > last_h[1]:
            ev.append(("CHoCH↑" if bias == "down" else "BOS↑", i, last_h[1])); bias = "up"; broken_h = last_h[0]
        if last_l and broken_l != last_l[0] and C[i] < last_l[1]:
            ev.append(("CHoCH↓" if bias == "up" else "BOS↓", i, last_l[1])); bias = "down"; broken_l = last_l[0]
    return ev, bias

def fvgs(df, lookback=126):
    """Unfilled daily FVGs within lookback. Returns (bull_list, bear_list) of (lo, hi, date)."""
    H, L, n = df.high.values, df.low.values, len(df)
    bull, bear = [], []
    for i in range(max(2, n - lookback), n):
        if L[i] > H[i - 2]:
            lo, hi = H[i - 2], L[i]
            fut = L[i + 1:]
            if fut.size == 0 or fut.min() > lo:
                hi2 = min(hi, fut.min()) if fut.size else hi
                bull.append((lo, hi2, df.index[i].date()))
        if H[i] < L[i - 2]:
            lo, hi = H[i], L[i - 2]
            fut = H[i + 1:]
            if fut.size == 0 or fut.max() < hi:
                lo2 = max(lo, fut.max()) if fut.size else lo
                bear.append((lo2, hi, df.index[i].date()))
    return bull, bear

def seq(points):
    """'up' if last 3 points strictly rising, 'down' if falling, else None."""
    p = [x[1] for x in points[-3:]]
    if len(p) < 3:
        return None
    if p[0] < p[1] < p[2]:
        return "up"
    if p[0] > p[1] > p[2]:
        return "down"
    return None

def analyze(sym, df, vix_close, mode="postmarket"):
    if df is None or len(df) < 30:
        return {"ticker": sym, "ok": False, "score": None, "alert": "黄", "reasons": ["K线不足"]}
    c = df.close
    n = len(df)
    last, prev = float(c.iloc[-1]), float(c.iloc[-2])
    ma = {w: (c.rolling(w).mean() if n >= w else pd.Series(np.nan, index=c.index)) for w in (20, 50, 200)}
    m20, m50, m200 = (float(ma[w].iloc[-1]) if n >= w else None for w in (20, 50, 200))
    slope = {w: (float(ma[w].iloc[-1] / ma[w].iloc[-11] - 1) * 100 if n >= w + 10 else None) for w in (20, 50, 200)}
    ema12, ema26 = c.ewm(span=12, adjust=False).mean(), c.ewm(span=26, adjust=False).mean()
    dif = ema12 - ema26; sig = dif.ewm(span=9, adjust=False).mean(); hist = dif - sig
    r = rsi(c)
    atr, adx, pdi, ndi = atr_adx(df)
    sd = c.rolling(20).std(ddof=0)
    bbu, bbl = ma[20] + 2 * sd, ma[20] - 2 * sd
    vol = df.volume
    vr = float(vol.iloc[-1] / vol.iloc[-21:-1].mean()) if n > 21 and vol.iloc[-21:-1].mean() > 0 else None
    A, ADX, PDI, NDI = float(atr.iloc[-1]), float(adx.iloc[-1]), float(pdi.iloc[-1]), float(ndi.iloc[-1])
    sh, sl = swings(df)
    ev, bias = structure(df, sh, sl)
    bull_fvg, bear_fvg = fvgs(df)
    # previous day / previous complete week
    pdh, pdl = float(df.high.iloc[-2]), float(df.low.iloc[-2])
    wk = df.resample("W-FRI").agg({"high": "max", "low": "min", "close": "last"})
    cur_week = df.index[-1].to_period("W-FRI")
    wk_prev = wk[wk.index.to_period("W-FRI") < cur_week]
    pwh, pwl = (float(wk_prev.high.iloc[-1]), float(wk_prev.low.iloc[-1])) if len(wk_prev) else (None, None)
    hi_t, lo_t = float(df.high.iloc[-1]), float(df.low.iloc[-1])
    y = df.iloc[-252:]
    h52, l52 = float(y.high.max()), float(y.low.min())
    # ---- six signals
    if m200 is not None:
        ma_bull = last > m50 and last > m200 and m50 > m200
        death = m50 < m200
    elif m50 is not None:
        ma_bull, death = last > m50, False
    else:
        ma_bull, death = False, False
    sigs = {"MA": ma_bull, "MACD": float(hist.iloc[-1]) > 0, "RSI": float(r.iloc[-1]) > 50,
            "DI": PDI > NDI, "BB": last > m20 if m20 else False,
            "VIX": (vix_close is not None and vix_close < 20)}
    nb = sum(bool(v) for v in sigs.values())
    if nb <= 2 or death:
        state = "B"
    elif nb == 3:
        state = "过渡"
    else:
        state = "A标准" if ADX >= 25 else "A谨慎"
    # ---- score (indicator part only; SMC only refines unless indicators mixed)
    hs, ls = seq(sh), seq(sl)
    struct_dir = "down" if (hs == "down" or ls == "down") and not (hs == "up" or ls == "up") else \
                 "up" if (hs == "up" or ls == "up") and not (hs == "down" or ls == "down") else None
    bear_ev = sum([not ma_bull, float(hist.iloc[-1]) < 0, ADX >= 25 and NDI > PDI, struct_dir == "down"])
    bull_ev = sum([ma_bull, float(hist.iloc[-1]) > 0, ADX >= 25 and PDI > NDI, struct_dir == "up"])
    if state == "B":
        score = -1
        if ADX >= 25 and NDI > PDI and bear_ev >= 3:
            score = -2
        elif nb == 2 and bias == "up":
            score = 0            # indicators weak but SMC bias up -> mixed
    elif state == "过渡":
        score = 0
    else:
        score = 1
        if ADX >= 25 and PDI > NDI and bull_ev >= 3:
            score = 2
        elif bias == "down":
            score = 0
    conf = "中"
    if (bias == "up" and score < 0) or (bias == "down" and score > 0) or (score == 0 and nb == 2 and bias == "up"):
        conf = "低"
    if n < 200:
        conf = "低"
    # ---- intraday conditions -> yellow
    reasons = []
    for w, mv in ((50, m50), (200, m200)):
        if mv is not None and n > w + 1:
            pm = float(ma[w].iloc[-2])
            if (prev - pm) * (last - mv) < 0:
                reasons.append(f"穿MA{w}")
    chg = (last / prev - 1) * 100
    if abs(chg) > 5: reasons.append(f"日内{chg:+.1f}%")
    if vr and vr > 2: reasons.append(f"量比{vr:.1f}x")
    if hi_t > pdh: reasons.append("扫前日高")
    if lo_t < pdl: reasons.append("扫前日低")
    if pwh and hi_t > pwh: reasons.append("扫前周高")
    if pwl and lo_t < pwl: reasons.append("扫前周低")
    alert = "黄" if reasons else "绿"
    # ---- levels
    cand = [(m20, "MA20"), (m50, "MA50"), (m200, "MA200"), (float(bbu.iloc[-1]), "布林上"),
            (float(bbl.iloc[-1]), "布林下"), (pdh, "前日高"), (pdl, "前日低"), (pwh, "前周高"),
            (pwl, "前周低"), (h52, "52周高"), (l52, "52周低")]
    cand += [(p, "摆动高") for _, p in sh[-8:]] + [(p, "摆动低") for _, p in sl[-8:]]
    cand += [(lo, "FVG空") for lo, hi, d in bear_fvg] + [(hi, "FVG多") for lo, hi, d in bull_fvg]
    cand = [(float(p), t) for p, t in cand if p is not None and p == p]
    def ladder(side):
        pts = sorted([x for x in cand if (x[0] < last if side == "S" else x[0] > last)],
                     key=lambda x: abs(x[0] - last))
        out = []
        for p, t in pts:
            if out and abs(p - out[-1]["p"]) <= 0.3 * A:
                out[-1]["src"].append(t); out[-1]["共振"] = True
                continue
            out.append({"p": round(p, 2), "src": [t], "共振": False})
            if len(out) >= 4: break
        return out
    sup, res = ladder("S"), ladder("R")
    last_sh = sh[-1][1] if sh else None
    last_sl = sl[-1][1] if sl else None
    if score < 0:
        inval = m50 if (m50 and m50 > last) else last_sh
        inval_dir = "上破"
    elif score > 0:
        inval = m50 if (m50 and m50 < last) else last_sl
        inval_dir = "下破"
    else:
        inval, inval_dir = None, None
    wk_full = wk_prev.close
    weekly = {"close": float(wk_full.iloc[-1]) if len(wk_full) else None,
              "ma10w": float(wk_full.rolling(10).mean().iloc[-1]) if len(wk_full) >= 10 else None,
              "ma40w": float(wk_full.rolling(40).mean().iloc[-1]) if len(wk_full) >= 40 else None}
    lv = lambda x: None if x is None else round(float(x), 2)
    return {
        "ticker": sym, "ok": True, "date": str(df.index[-1].date()), "bars": n,
        "bar_closed": mode == "postmarket" or mode == "premarket",
        "close": round(last, 2), "prev_close": round(prev, 2), "chg_pct": round(chg, 2),
        "ma20": lv(m20), "ma50": lv(m50), "ma200": lv(m200),
        "slope10_pct": {k: (round(v, 2) if v is not None else None) for k, v in slope.items()},
        "macd": {"dif": round(float(dif.iloc[-1]), 3), "signal": round(float(sig.iloc[-1]), 3),
                 "hist": round(float(hist.iloc[-1]), 3), "hist6": [round(float(x), 2) for x in hist.iloc[-6:]]},
        "rsi14": round(float(r.iloc[-1]), 1), "adx14": round(ADX, 1), "pdi": round(PDI, 1), "ndi": round(NDI, 1),
        "atr14": round(A, 2), "atr_pct": round(A / last * 100, 2),
        "bb": {"upper": lv(bbu.iloc[-1]), "lower": lv(bbl.iloc[-1]),
               "pctb": round(float((last - bbl.iloc[-1]) / (bbu.iloc[-1] - bbl.iloc[-1])), 2) if n >= 20 else None},
        "vol_ratio": round(vr, 2) if vr else None,
        "six_signals": sigs, "bull_count": nb, "state": state, "death_cross": bool(death),
        "swing_highs": [(str(df.index[i].date()), round(p, 2)) for i, p in sh[-3:]],
        "swing_lows": [(str(df.index[i].date()), round(p, 2)) for i, p in sl[-3:]],
        "hh_seq": hs, "ll_seq": ls, "smc_bias": bias,
        "smc_events": [(t, str(df.index[i].date()), round(p, 2)) for t, i, p in ev[-3:]],
        "fvg_bull": [(round(a, 2), round(b, 2), str(d)) for a, b, d in bull_fvg[-3:]],
        "fvg_bear": [(round(a, 2), round(b, 2), str(d)) for a, b, d in bear_fvg[-3:]],
        "pdh": lv(pdh), "pdl": lv(pdl), "pwh": lv(pwh), "pwl": lv(pwl), "h52": lv(h52), "l52": lv(l52),
        "support": sup, "resistance": res,
        "invalidation": {"level": lv(inval), "dir": inval_dir},
        "weekly": weekly,
        "ret20_pct": round((last / float(c.iloc[-21]) - 1) * 100, 2) if n > 21 else None,
        "ret60_pct": round((last / float(c.iloc[-61]) - 1) * 100, 2) if n > 61 else None,
        "hv20": round(float(np.log(c).diff().iloc[-20:].std() * np.sqrt(252) * 100), 1) if n > 21 else None,
        "hv60": round(float(np.log(c).diff().iloc[-60:].std() * np.sqrt(252) * 100), 1) if n > 61 else None,
        "score": score, "confidence": conf, "alert": alert, "reasons": reasons,
    }
