"""Strategy Y: a local OpenJev model picks the position each month. Compared with rule-only baselines.

Three steps, because the model runs in a different Python (~/mlx-env) than this project:
  python3 scripts/backtest_openjev.py features         # point-in-time features -> features.csv
  ~/mlx-env/bin/python scripts/openjev_decide.py       # one cached decision per date -> decisions.json
  python3 scripts/backtest_openjev.py run              # backtest + report

Decision (once per month-end and on each entry day), one of:
  stocks (QQQ), leveraged (TQQQ), bonds (TLT), cash.
Guardrails: the model can only pick from that list. If its top probability is below
MIN_CONFIDENCE, the rule-only answer is used instead (QQQ above its 200-day SMA: stocks, else cash).
Baseline Z is that rule alone, so Y minus Z is what the model adds.

Fills, costs and tax are the same as backtest_strategies.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import backtest_strategies as bs  # noqa: E402

OUT = bs.OUT_DIR / "openjev"
FEATURES = OUT / "features.csv"
DECISIONS = OUT / "decisions.json"
MIN_CONFIDENCE = 0.5
WEIGHTS = {"stocks": {"QQQ": 1.0}, "leveraged": {"TQQQ": 1.0}, "bonds": {"TLT": 1.0}, "cash": {}}
BASELINES = ["A", "K", "P"]  # QQQ hold, 210-day SMA trend on QQQ, dual momentum QQQ/TLT
FIRST_DAY = "2010-01-01"


def decision_days(adj: pd.DataFrame) -> pd.DatetimeIndex:
    idx = adj.index[adj.index >= FIRST_DAY]
    months = pd.Series(idx).groupby(idx.to_period("M")).last()
    entries = [pd.Timestamp(e) for _, e in bs.ENTRY_SCENARIOS]
    return pd.DatetimeIndex(sorted(set(months) | set(entries)))


def export_features() -> None:
    adj, _ = bs.load_market()
    q, t = adj["QQQ"], adj["TLT"]
    ret = np.log(q).diff()
    feat = pd.DataFrame({
        "above_sma200": (q / q.rolling(200).mean() - 1) * 100,
        "sma50_vs_200": (q.rolling(50).mean() / q.rolling(200).mean() - 1) * 100,
        "drawdown_252": (q / q.rolling(252).max() - 1) * 100,
        "ret_20": q.pct_change(20) * 100,
        "ret_126": q.pct_change(126) * 100,
        "ret_252": q.pct_change(252) * 100,
        "vol_20": ret.rolling(20).std() * np.sqrt(252) * 100,
        "rsi14": bs.rsi(q),
        "bond_ret_126": t.pct_change(126) * 100,
    })
    days = [d for d in decision_days(adj) if d in feat.index]
    out = feat.loc[days].dropna()
    OUT.mkdir(parents=True, exist_ok=True)
    out.round(3).rename_axis("date").to_csv(FEATURES, date_format="%Y-%m-%d")
    print(f"wrote {len(out)} rows to {FEATURES}")


def rule_action(above_sma200: float) -> str:
    return "stocks" if above_sma200 > 0 else "cash"


def resolve(day: pd.Timestamp, decisions: dict, feats: pd.DataFrame) -> tuple[str, str]:
    """Final action for a day and where it came from: model, or rule fallback."""
    d = decisions[f"{day:%Y-%m-%d}"]
    if d["confidence"] >= MIN_CONFIDENCE:
        return d["action"], "model"
    return rule_action(feats.at[day, "above_sma200"]), "fallback"


def weights_step(days: set, pick) -> callable:
    def step(eng: bs.Engine, day: pd.Timestamp) -> None:
        if day not in days:
            return
        w = pick(day)
        if not w and all(eng.shares[t] <= 1e-9 for t in bs.TICKERS):
            return  # nothing held, nothing to sell
        eng.rebalance(day, w)
    return step


def run() -> None:
    adj, yld = bs.load_market()
    decisions = json.loads(DECISIONS.read_text())
    feats = pd.read_csv(FEATURES, index_col="date", parse_dates=True)

    def y_weights(day):
        action, _ = resolve(day, decisions, feats)
        if action == "leveraged" and pd.isna(adj.at[day, "TQQQ"]):
            action = "stocks"
        return WEIGHTS[action]

    def z_weights(day):
        return WEIGHTS[rule_action(feats.at[day, "above_sma200"])]

    rows = []
    for label, entry in bs.ENTRY_SCENARIOS:
        dates = adj.index[adj.index >= entry]
        days = {d for d in dates if f"{d:%Y-%m-%d}" in decisions}
        month_ends = set(pd.Series(dates).groupby(dates.to_period("M")).last()) | {dates[0]}
        days &= month_ends
        makers = {
            "Y": lambda: weights_step(days, y_weights),
            "Z": lambda: weights_step(days, z_weights),
            **{k: (lambda k=k: bs.fresh_step(adj, dates, k)) for k in BASELINES},
        }
        for letter, make in makers.items():
            eng = bs.simulate(adj, yld, dates, make())
            rows.append(bs.metrics(letter, letter, "ideal", pd.Series(eng.equity, index=dates), eng.trades, 0.0, 0.0) | {"entry": label})
            taxed, tax, wash, teng = bs.run_taxed(adj, yld, dates, make, bs.CA_TOP_RATE, True)
            rows.append(bs.metrics(letter, letter, "federal+CA", taxed, teng.trades, tax, wash) | {"entry": label})
        print(f"done {label}", flush=True)

    summary = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    summary.to_csv(OUT / "summary.csv", index=False)
    write_report(summary, decisions, feats)


def write_report(summary: pd.DataFrame, decisions: dict, feats: pd.DataFrame) -> None:
    names = {"Y": "Y  OpenJev monthly pick", "Z": "Z  rule only (QQQ vs SMA200, else cash)",
             "A": "A  QQQ buy & hold", "K": "K  SMA210 trend, QQQ", "P": "P  dual momentum QQQ/TLT"}
    lines = ["# OpenJev decisions: results\n"]
    for scen in ["federal+CA", "ideal"]:
        s = summary[summary.scenario == scen]
        piv = s.pivot(index="entry", columns="letter", values="return_pct")
        dd = s.pivot(index="entry", columns="letter", values="max_drawdown_pct")
        lines += [f"## {scen}, {len(piv)} entries\n",
                  "| strategy | mean return % | median return % | mean max DD % | worst DD % |", "|---|---|---|---|---|"]
        for k in ["Y", "Z", "A", "K", "P"]:
            lines.append(f"| {names[k]} | {piv[k].mean():.0f} | {piv[k].median():.0f} | {dd[k].mean():.1f} | {dd[k].min():.1f} |")
        lines.append(f"\nY beats Z in {(piv.Y > piv.Z).sum()} of {len(piv)} entries, beats A in {(piv.Y > piv.A).sum()}, "
                     f"has a smaller max drawdown than A in {(dd.Y > dd.A).sum()}.\n")

    d = pd.DataFrame(decisions).T
    d.index = pd.to_datetime(d.index)
    d = d[d.index.isin(feats.index)]
    final = [resolve(day, decisions, feats) for day in d.index]
    d["final"] = [a for a, _ in final]
    d["source"] = [s for _, s in final]
    d["rule"] = [rule_action(feats.at[day, "above_sma200"]) for day in d.index]
    me = d[d.index.is_month_end | True]
    lines += ["## What the model decided\n", f"{len(d)} decisions (month-ends plus entry days).\n",
              "| action | count | share |", "|---|---|---|"]
    for a, n in d.final.value_counts().items():
        lines.append(f"| {a} | {n} | {n / len(d):.0%} |")
    lines.append(f"\n- Mean top-option probability: {d.confidence.astype(float).mean():.2f}. "
                 f"Fell back to the rule (confidence below {MIN_CONFIDENCE}): {(d.source == 'fallback').sum()}.")
    lines.append(f"- Mean probability mass on the four option words: {d.option_mass.astype(float).mean():.2f} "
                 "(low means the model wanted to say something else).")
    lines.append(f"- Agrees with the SMA200 rule: {(d.final == d.rule).mean():.0%}.")
    lines.append(f"- Position changes: {(d.final != d.final.shift()).sum() - 1}, over {len(d)} decisions.\n")
    lines += ["### Calls in stress periods\n", "| date | action | confidence | vs 200d | drawdown | vol |", "|---|---|---|---|---|---|"]
    for lo, hi in [("2011-07-01", "2011-12-31"), ("2018-10-01", "2019-01-31"), ("2020-02-01", "2020-05-31"),
                   ("2022-01-01", "2022-12-31"), ("2025-03-01", "2025-05-31")]:
        for day in d.loc[lo:hi].index:
            f = feats.loc[day]
            lines.append(f"| {day:%Y-%m-%d} | {d.at[day, 'final']} | {float(d.at[day, 'confidence']):.2f} | "
                         f"{f.above_sma200:+.1f}% | {f.drawdown_252:.1f}% | {f.vol_20:.0f}% |")
    lines += ["\n## Caveats\n",
              "- The 42 entries overlap heavily, so they are not 42 independent tests.",
              "- Features and thresholds were set before looking at results, but the whole period is in-sample for this project.",
              "- Prompts hold no dates or tickers, but a 9B model may still know typical market history.",
              "- Decisions are cached, so reruns give identical results. A different model file or prompt gives different ones."]
    (OUT / "report.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {OUT / 'report.md'}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"features": export_features, "run": run}.get(cmd, lambda: sys.exit(__doc__))()
