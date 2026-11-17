"""Sentiment numeric proxies only. X / Reddit / Stocktwits reading stays with the AI sentiment bot."""
def analyze(sym, tech, fg):
    vr = (tech or {}).get("vol_ratio"); chg = (tech or {}).get("chg_pct")
    s = fg["score"] if fg else None
    score, reasons = 0, []
    if s is not None and vr and chg is not None:
        if s <= 20 and vr >= 2 and chg < 0:
            score = 1; reasons.append("疑似投降")
        elif s >= 80 and vr >= 2 and chg > 0:
            score = -1; reasons.append("疑似过热")
    if vr and vr >= 3:
        reasons.append(f"量比{vr:.1f}x")
    return {"ticker": sym, "ok": s is not None or vr is not None, "fg": s, "vol_ratio": vr,
            "score": score, "confidence": "低", "alert": "黄" if reasons else "绿", "reasons": reasons}
