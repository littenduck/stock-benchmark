# stock-backtest

Backtests of classic stock and ETF strategies. Each strategy starts with 100k at a chosen entry date, and results are shown before and after US federal and California tax, including the 30-day wash-sale rule.

## What is in the project

| File | Purpose |
|---|---|
| `backend/backtest/backtest_strategies.py` | Main run. Runs strategies A–X from 42 entry points (historical highs and lows) on QQQ/TQQQ. Each run gives four results: ideal (no tax), federal+CA, CA without the wash-sale rule, and federal only. The 2021-11-22 entry also writes a curve chart and an animation. |
| `backend/backtest/backtest_pair.py` | Runs the same strategies (A–O and V–X) on a base/leverage pair. Modes: `soxx_soxl` (SOXX base, SOXL leverage) and `qqq_tqqq` (cross-check against the main run). Uses a 12-entry subset of the QQQ entry dates. |
| `backend/backtest/make_report.py` | Reads the main run's summary CSV and writes a Markdown report and an after-tax return matrix. |

Strategy groups: benchmarks (A, B), DCA (C, D), moving averages (E–K), indicators (L–O), allocation (P–S), sector rotation (T), high-dividend hold (U), and risk control (V–X).

For the full rules, see `data/runtime/backtest/strategies_rules.md` after a run.

### Assumptions

- Signals use the day's close and trades fill at that same close. There is no spread, slippage or commission.
- Prices are total-return prices (dividends reinvested). ETF expense ratios are already in the price.
- Tax is for US high-income investors, by calendar year:
  - Short-term gains: 37% + 3.8% NIIT, plus state tax.
  - Long-term gains: 20% + 3.8% NIIT, plus state tax.
  - Equity ETF dividends are qualified. Dividends from TLT, IEF and DBC are ordinary income.
  - Losses net within the same term and year, then across terms, then carry forward without limit. The $3,000 ordinary-income deduction is ignored.
- Each year's tax is paid on the last trading day of that year, out of the portfolio: first from cash, then by selling shares pro rata. Those sales are taxed too. Later returns therefore compound on the after-tax value.
- Market data comes from `yfinance` at run time, so results change as the data updates.

### Tax scenarios

| Scenario | Meaning |
|---|---|
| ideal | No tax. |
| federal+CA | Federal plus California tax, with the wash-sale rule. This is the main result. |
| CA no wash | Same as above with the wash-sale rule off, to show its effect. |
| fed only | Federal tax only, for states without income tax (such as TX, FL, WA). |

### Letter mapping from the removed peak-2021 script

The old peak-2021 script used different letters. Old → new: A, B and C are unchanged; old D (SMA 225) → E; old E (MA 100/225) → G; old F (biweekly DCA) → D.

## Quick start

Python 3 is required. The project was tested on Python 3.9. Node.js (with npm) is needed only for the chart page.

```bash
# 1. Install dependencies from the project root (Python packages; npm only for the chart page)
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
npm install

# 2. Main run on QQQ/TQQQ, all 42 entries (takes a while; downloads data)
.venv/bin/python -m backend.backtest strategies

# 3. Pair run on SOXX/SOXL, 12-entry subset
.venv/bin/python -m backend.backtest pair soxx_soxl

# 4. Optional: QQQ/TQQQ pair cross-check against the main run
.venv/bin/python -m backend.backtest pair qqq_tqqq

# 5. Markdown report (needs step 2)
.venv/bin/python -m backend.backtest report
```

Outputs go to `data/runtime/backtest/`:

- `strategies_report.md`: one table per entry, with ideal and after-tax results and max drawdown.
- `strategies_after_tax_matrix.csv`: strategy × entry matrix of after-tax returns.
- `strategies_summary_*.csv`: summary per entry.
- `strategies_chart_*.png`: equity curves per entry.
- `equity_curves_*.csv`, `equity_static.png`, `equity_animation.gif`: daily curves and the static chart and animation for the 2021-11-22 entry.
- `soxx_soxl/`: pair run outputs (`summary_all.csv`, one chart per entry, `rules.md`).

`make_report.py` must run after step 2, because it reads `strategies_summary_all.csv`.

## Notes

- This is a historical simulation for research only. It is not investment advice.
- Past results do not predict future results. Leveraged ETFs such as TQQQ and SOXL are heavily affected by the path they take.
- Results are in-sample. Many entry points are close together, so they are not independent. Most entries fall in a long bull market.
- The scripts need network access to Yahoo Finance.
