"""Build one markdown report with a table per entry scenario from the saved summary CSV."""
from pathlib import Path

import pandas as pd

OUT_DIR = Path(__file__).resolve().parent.parent / "backtest_output"


def scenario_table(df: pd.DataFrame) -> str:
    ideal = df[df.scenario == "ideal"].set_index("letter")
    tax = df[df.scenario == "federal+CA"].set_index("letter")
    lines = [
        "| Letter | Strategy | Ideal value | Ideal return | After-tax value | After-tax return | Tax paid | Ideal max drawdown | Trades |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for letter in ideal.index:
        i, t = ideal.loc[letter], tax.loc[letter]
        lines.append(
            f"| {letter} | {i.plan} | {i.final_value:,.0f} | {i.return_pct:+.1f}% "
            f"| {t.final_value:,.0f} | {t.return_pct:+.1f}% | {t.total_tax:,.0f} "
            f"| {i.max_drawdown_pct:.1f}% | {i.trades} |"
        )
    return "\n".join(lines)


def main() -> None:
    all_df = pd.read_csv(OUT_DIR / "strategies_summary_all.csv")
    parts = ["# Backtest report: all scenarios", "",
             "One table per entry. After-tax means federal plus California tax, with the wash-sale rule applied. No slippage.", ""]
    charts = sorted(OUT_DIR.glob("chart_*.png"))
    if charts:
        parts += ["## Price charts", "", "Last year of daily candles with SMA, MACD and ADX. Interactive version: `chart.html` (run `scripts/make_chart.py`).", ""]
        parts += [f"![{p.stem[6:]}]({p.name})" for p in charts] + [""]
    for entry in all_df["entry"].drop_duplicates():
        parts += [f"## {entry}", "", scenario_table(all_df[all_df.entry == entry]), ""]
    (OUT_DIR / "strategies_report.md").write_text("\n".join(parts), encoding="utf-8")

    # Overview matrix: after-tax return for every strategy in every scenario.
    tax = all_df[all_df.scenario == "federal+CA"].copy()
    tax["scenario"] = tax["entry"].str.extract(r"^(\d{4}-\d{2}-\d{2})")[0]
    matrix = tax.pivot_table(index=["letter", "plan"], columns="scenario", values="return_pct", aggfunc="first")
    matrix.to_csv(OUT_DIR / "strategies_after_tax_matrix.csv")
    print(matrix.to_string())


if __name__ == "__main__":
    main()
