#!/usr/bin/env python3
"""盯盘团队数据管线：一次抓完所有数据、算完所有分数，写 data/*.json + summary-<mode>.md/json + ledger。
用法: python3 run.py premarket|intraday|postmarket [--date YYYY-MM-DD]
只读公开行情接口（Yahoo / FRED / CNN），不调用任何券商或交易接口。"""
import argparse, datetime as dt, json, sys, time, traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import common as C
from lib import technical, options, macro, fundamental, sentiment, ai_reports, chief

LEV = {"SPY": "SPXL", "QQQ": "TQQQ", "SOXX": "SOXL", "DRAM": "RAM"}

def safe(fn, *a, label="", **k):
    try:
        return fn(*a, **k)
    except Exception as e:
        C.gap(f"{label}: 计算失败 {type(e).__name__}")
        traceback.print_exc(file=sys.stderr)
        return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["premarket", "intraday", "postmarket"])
    ap.add_argument("--date", help="美东日期 YYYY-MM-DD，默认今天")
    ap.add_argument("--no-ledger", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    run_date = dt.date.fromisoformat(a.date) if a.date else dt.date.today()
    tickers = C.parse_lists()
    if not tickers:
        print("lists.md 的 TICKERS 为空，停止。"); return 2
    out_dir = C.REPORTS / str(run_date); data_dir = out_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # ---------- fetch all charts in parallel
    syms = list(dict.fromkeys(tickers + ["^VIX", "^VXN", "^TNX", "DX-Y.NYB", "^NDX", "SPY", "QQQ", "SOXX"]))
    with ThreadPoolExecutor(10) as ex:
        charts = dict(zip(syms, ex.map(lambda s: safe(C.yahoo_chart, s, run_date, label=s), syms)))
        funds = dict(zip(tickers, ex.map(lambda s: safe(fundamental.analyze, s, run_date, label=f"{s}基本面"), tickers)))
    pre = {}
    if a.mode == "premarket":       # latest pre-market print vs last close
        def prem(s):
            d = C.http_get(f"https://query1.finance.yahoo.com/v8/finance/chart/{s}",
                           params={"range": "1d", "interval": "5m", "includePrePost": "true"})
            try:
                cl = [x for x in d["chart"]["result"][0]["indicators"]["quote"][0]["close"] if x]
                return cl[-1] if cl else None
            except Exception:
                return None
        with ThreadPoolExecutor(10) as ex:
            pre = dict(zip(tickers, ex.map(prem, tickers)))
    vixdf = charts.get("^VIX")
    vix_close = float(vixdf.close.iloc[-1]) if vixdf is not None else None

    tech = {s: safe(technical.analyze, s, charts.get(s), vix_close, a.mode, label=f"{s}技术面") or
            {"ticker": s, "ok": False, "score": None, "alert": "黄", "reasons": ["无数据"]} for s in tickers}
    m, macro_per = safe(macro.analyze, run_date, charts, tickers, label="宏观") or ({}, {})
    hist = options.load_hist()
    def opt(s):
        ed = (funds.get(s) or {}).get("_ed")
        return safe(options.analyze, s, run_date, tech.get(s), ed, hist, label=f"{s}期权")
    with ThreadPoolExecutor(6) as ex:
        opts = dict(zip(tickers, ex.map(opt, tickers)))
    if (dt.date.today() - run_date).days <= 3:           # only record IV for current runs
        safe(options.save_hist, hist, label="IV历史")
    else:
        C.gap("期权链为实时快照，历史日期回放时期权数据不对应该日")
    sent = {s: sentiment.analyze(s, tech.get(s), m.get("fg")) for s in tickers}

    # ---------- AI reports (fundamental / sentiment carry-forward; others for comparison)
    ai = {}
    for p in ("macro", "fundamental", "technical", "options", "sentiment"):
        d, rec = ai_reports.latest(p, run_date, tickers)
        ai[p] = {"date": str(d) if d else None, "age_td": C.trading_days_between(d, run_date) if d else None, "scores": rec}
    ov_path = out_dir / "overrides.json"
    overrides = json.loads(ov_path.read_text()) if ov_path.exists() else {}

    def pick(panel, s, script_rec):
        A = ai[panel]; r = (A["scores"] or {}).get(s)
        valid = {"fundamental": 5, "sentiment": 1}.get(panel)  # trading days (7 calendar ≈ 5 td)
        if panel in overrides and s in overrides[panel]:
            return {"score": overrides[panel][s], "confidence": "中", "src": "AI覆盖", "alert": None, "reasons": []}
        if valid is not None and r and A["age_td"] is not None and A["age_td"] <= valid:
            return {"score": r.get("score"), "confidence": r.get("confidence") or "中", "src": f"AI{A['date'][5:]}",
                    "alert": r.get("alert"), "reasons": [f"{chief.CN[panel]}AI{r.get('alert')}"] if r.get("alert") in ("黄", "红") else []}
        if script_rec and script_rec.get("score") is not None:
            return {"score": script_rec["score"], "confidence": script_rec.get("confidence", "中"), "src": "脚本",
                    "alert": script_rec.get("alert"), "reasons": script_rec.get("reasons", [])}
        if r and valid is not None:
            return {"score": r.get("score"), "stale": True, "src": f"AI{A['date'][5:]}过期", "alert": None, "reasons": []}
        return {"score": None, "src": C.ND, "alert": None, "reasons": []}

    cur = {}
    for s in tickers:
        T, F, O = tech[s], funds.get(s) or {}, opts.get(s) or {}
        panels = {"macro": pick("macro", s, macro_per.get(s)), "fundamental": pick("fundamental", s, F),
                  "technical": pick("technical", s, T), "options": pick("options", s, O),
                  "sentiment": pick("sentiment", s, sent[s])}
        ed = F.get("_ed")
        td = C.trading_days_between(run_date, ed) if ed else None
        e_soon = td is not None and 0 <= td <= 5
        total, mid, wts = chief.aggregate(panels, m.get("risk_off"), e_soon)
        alert = max((p.get("alert") for p in panels.values()), key=lambda c: chief.RANK.get(c, 0)) or "绿"
        price = pre.get(s) if a.mode == "premarket" and pre.get(s) else T.get("close")
        cur[s] = {"close": T.get("close"), "price": price, "chg_pct": T.get("chg_pct"),
                  "scores": {k: v.get("score") for k, v in panels.items()},
                  "src": {k: v.get("src") for k, v in panels.items()},
                  "stale": [k for k, v in panels.items() if v.get("stale")],
                  "total": total, "mid": mid, "weights": wts, "state": T.get("state"), "bull": T.get("bull_count"),
                  "alert": alert, "reasons": {chief.CN[k]: v["reasons"] for k, v in panels.items() if v.get("reasons")},
                  "earnings": str(ed) if e_soon else None,
                  "support": [x["p"] for x in (T.get("support") or [])[:2]],
                  "resistance": [x["p"] for x in (T.get("resistance") or [])[:2]],
                  "opt_levels": {"max_pain": O.get("max_pain"), "sigma1": O.get("sigma1_monthly"),
                                 "call_wall": (O.get("top_call_oi") or [[None]])[0][0], "put_wall": (O.get("top_put_oi") or [[None]])[0][0]},
                  "invalidation": T.get("invalidation"), "_panels": panels}
    prev = chief.previous_summary(run_date, a.mode)
    chg = chief.changes(cur, prev)
    for s in tickers:
        cur[s]["changes"], cur[s]["red"] = chg[s]
        cur[s]["red"] = cur[s]["red"] + [f"{chief.FULL[k]}AI报告红" for k, v in cur[s]["_panels"].items() if v.get("alert") == "红"]
        del cur[s]["_panels"]
        prev_red = set(((prev or {}).get("tickers", {}).get(s) or {}).get("red") or [])
        cur[s]["red_new"] = [r for r in cur[s]["red"] if r not in prev_red]
        cur[s]["alert"] = "红" if cur[s]["red"] else ("黄" if cur[s]["alert"] == "红" else cur[s]["alert"])

    # ---------- write data jsons
    strip = lambda d: {k: v for k, v in d.items() if not k.startswith("_")} if isinstance(d, dict) else d
    C.save_json(data_dir / f"technical-{a.mode}.json", tech)
    C.save_json(data_dir / f"options-{a.mode}.json", opts)
    C.save_json(data_dir / f"macro-{a.mode}.json", {"market": m, "per_ticker": macro_per})
    C.save_json(data_dir / f"fundamental-{a.mode}.json", {k: strip(v) for k, v in funds.items()})
    C.save_json(data_dir / f"sentiment-{a.mode}.json", sent)
    summ = {"date": str(run_date), "mode": a.mode, "generated": dt.datetime.now().strftime("%Y-%m-%d %H:%M ET"),
            "market": {k: m.get(k) for k in ("vix", "vix_chg_pct", "vix_band", "vxn", "vxn_band", "vxn_minus_vix", "tnx",
                       "tnx_1d_bp", "dxy", "dxy_20d_pct", "hy_oas", "hy_date", "hy_4w_bp", "fg", "fg_band",
                       "ndx_vs200_pct", "risk_off", "risk_off_hits", "soxx_vs_qqq_21d")},
            "ai_reports": {p: {"date": v["date"], "age_td": v["age_td"], "scores": v["scores"]} for p, v in ai.items()},
            "previous": f"{prev['date']} {prev['mode']}" if prev else None,
            "tickers": cur, "gaps": C.GAPS, "leverage_map": LEV}
    # ---------- ledger (postmarket only)
    if a.mode == "postmarket" and not a.no_ledger:
        rows = []
        for s in tickers:
            c = cur[s]; sc = c["scores"]
            f = lambda k: C.ND if sc.get(k) is None or k in c["stale"] else f"{sc[k]:+d}"
            rows.append([str(run_date), s, C.fnum(c["close"]), f("macro"), f("fundamental"), f("technical"),
                         f("options"), f("sentiment"), C.ND if c["total"] is None else f"{c['total']:+.1f}", C.ND, C.ND])
        closes = {s: charts[s].close for s in tickers if charts.get(s) is not None}
        summ["ledger"] = dict(zip(("added_or_updated", "backfilled"), chief.update_ledger(run_date, rows, closes)))
    summ["runtime_s"] = round(time.time() - t0, 1)
    C.save_json(out_dir / f"summary-{a.mode}.json", summ)
    md = render(summ, tickers)
    (out_dir / f"summary-{a.mode}.md").write_text(md, encoding="utf-8")
    print(md)
    print(f"\n[run.py] {a.mode} {run_date} 用时 {summ['runtime_s']}s，摘要 {len(md.encode())} 字节 -> {out_dir}", file=sys.stderr)
    return 0

MODE_CN = {"premarket": "盘前", "intraday": "盘中", "postmarket": "盘后"}

def render(S, tickers):
    f = C.fnum; m = S["market"]; T = S["tickers"]
    L = [f"# 盯盘摘要 {S['date']} {MODE_CN[S['mode']]}（脚本，{S['generated'][11:]}）"]
    reds = [s for s in tickers if T[s]["alert"] == "红"]
    L.append("## 🔴红色警报")
    L += [f"- {s}: {'；'.join(T[s]['red'])}" + ("" if T[s].get("red_new") else "（延续上期，非新增）") for s in reds] or ["- 无"]
    fg = m.get("fg") or {}
    pct = lambda x: f"{x:+.1f}%" if isinstance(x, (int, float)) else C.ND
    L.append("## 市场")
    L.append(f"VIX {f(m.get('vix'))}({pct(m.get('vix_chg_pct'))},{m.get('vix_band') or C.ND}) VXN {f(m.get('vxn'))}({m.get('vxn_band') or C.ND}) "
             f"差{f(m.get('vxn_minus_vix'))} | 10Y {f(m.get('tnx'))}% DXY {f(m.get('dxy'))} | HY {f(m.get('hy_oas'))}%({(m.get('hy_date') or '')[5:]}) "
             f"| F&G {fg.get('score', C.ND)} {m.get('fg_band') or ''} | NDX距200日{pct(m.get('ndx_vs200_pct'))} | 避险:{'是' if m.get('risk_off') else '否'}({m.get('risk_off_hits')}/3)")
    L.append("## 标的（宏/基/技/期/情→短线总分[中线]）")
    order = reds + [s for s in tickers if s not in reds]
    for s in order:
        t = T[s]; sc = t["scores"]
        g = lambda k: "—" if sc.get(k) is None or k in t["stale"] else f"{sc[k]:+d}"
        px = f(t["price"]) + (f"({pct(t['chg_pct'])})" if S["mode"] != "premarket" else f"(昨收{f(t['close'])})")
        tot = "—" if t["total"] is None else f"{t['total']:+.1f}"
        mid = "—" if t["mid"] is None else f"{t['mid']:+.1f}"
        e = f" ⚠财报{t['earnings'][5:]}" if t["earnings"] else ""
        sup = "/".join(f(x) for x in t["support"]) or C.ND
        res = "/".join(f(x) for x in t["resistance"]) or C.ND
        o = t["opt_levels"]; sg = o.get("sigma1")
        opt = f" 1σ{f(sg[0],0)}-{f(sg[1],0)}" if sg else ""
        L.append(f"- **{s}** {px}{e} | {g('macro')}/{g('fundamental')}/{g('technical')}/{g('options')}/{g('sentiment')}→{tot}[{mid}] "
                 f"{t['alert']} | {t['state']}{t['bull']}/6 | S{sup} R{res}{opt} | {'，'.join(t['changes'])}")
    def rs(s):
        seen = []
        for v in T[s]["reasons"].values():
            for r in v:
                if r not in seen: seen.append(r)
        return ",".join(seen)
    yel = [f"{s}:{rs(s)}" for s in order if T[s]["reasons"] and T[s]["alert"] != "绿"]
    if yel:
        L.append("## 黄色原因\n" + "；".join(yel))
    srcs = {k: sorted({T[s]['src'][k] for s in tickers}) for k in ("fundamental", "sentiment")}
    L.append(f"## 说明\n基本面来源:{','.join(srcs['fundamental'])}；情绪面:{','.join(srcs['sentiment'])}；期权分为脚本PCR代理(低置信)。"
             f"上期:{S['previous'] or '无'}。杠杆映射 SPY→SPXL QQQ→TQQQ SOXX→SOXL DRAM→RAM（操作提示由首席AI写）。")
    if S["gaps"]:
        grp = {}
        for g_ in S["gaps"]:
            k, _, msg = g_.partition(": ")
            if msg and k.isupper() and len(k) <= 6:
                grp.setdefault(msg, []).append(k)
            else:
                grp.setdefault(g_, [])
        items = [(f"{','.join(v)}: {k}" if v else k) for k, v in grp.items()]
        L.append("## 数据缺口\n" + "；".join(items[:6]) + (f" 等{len(items)}类，详见json" if len(items) > 6 else ""))
    return "\n".join(L) + "\n"

if __name__ == "__main__":
    sys.exit(main())
