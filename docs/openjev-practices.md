# Putting a decision model into this backtest

## Where the decisions are

Today every strategy (A to X) is a fixed rule, and the script runs all of them from every entry date. Nothing chooses. The places where a choice exists, or is hidden in a constant:

| Decision point | Where | Today |
|---|---|---|
| Which asset to hold now (stocks, 3x, bonds, cash) | `build_strategies` signals | one hard-coded rule per strategy |
| Which strategy fits the current market | nowhere | all run, the reader compares |
| Parameters (SMA 225, RSI 30/55, stop 30%, grid 10%) | constants in `build_strategies` | fixed, partly chosen by looking at past results |
| Entry dates | `ENTRY_SCENARIOS` | past highs and lows, picked with hindsight |
| Realize a gain now or wait for long term | `Engine.sell` (FIFO) | no choice, FIFO only |

The model fits the first row: a small set of options, a few numbers as input, a typed answer. It does not fit free-form work such as forecasting prices or reading charts.

## Ten practices, scored 1 to 5 for this project

Score = value for this project, minus cost and risk. Only the 5 is built as the feature; the 4s are the plumbing that makes it trustworthy, and are built with it.

| # | Practice | Score | Why |
|---|---|---|---|
| 1 | Model picks one of a fixed list of positions each month; the answer is the next-token probability over the option words, not parsed text | **5** | Matches the model type. No parsing errors, always valid, repeatable, gives a confidence. Uses the engine's `rebalance` and tax model unchanged. **Built: strategy Y.** |
| 2 | Point-in-time features only, and no dates or tickers in the prompt | 4 | Stops look-ahead and recall of known history. Built into Y, but it is a rule for #1, not a feature. |
| 3 | Cache every decision by date and prompt hash | 4 | Backtest stays reproducible and runs in seconds after the first pass. Built into Y. |
| 4 | Keep a rule-only baseline on the same dates and compare | 4 | Without it you cannot tell what the model added. Built as Z. |
| 5 | Confidence gate: below 0.5, use the rule instead | 4 | Cheap safety against a flat, unsure answer. Built into Y. |
| 6 | Walk-forward split: judge only on dates after any prompt tuning | 4 | Needed before trusting results; not built yet because the prompt was not tuned on results. |
| 7 | Decision journal: save inputs, probabilities and the final action | 3 | Makes review possible. Built as `decisions.json` and a report section, but only a minimal form. |
| 8 | Tax-aware veto: block a sale that is a few days before a lot turns long term, or inside a wash-sale window | 3 | High value here, since tax is the main cost in the results. Needs lot data in the prompt and engine changes, so a separate piece of work. |
| 9 | Several prompt wordings vote on each decision | 3 | Reduces wording luck, but costs several times the run time (about 25 s per prompt-month on this Mac). |
| 10 | Model labels news or filings | 2 | The project has no text data. |

Left out on purpose: letting the model choose indicator parameters (score 1, it fits the past by construction) and free-text commentary on results (score 2, no effect on the numbers).

## How strategy Y works

1. `backtest_openjev.py features` writes nine numbers per decision date (distance to 200-day average, trend, drawdown, returns, volatility, RSI, bond momentum).
2. `openjev_decide.py` fills a prompt, runs the local model once, reads the probability of each of `stocks`, `leveraged`, `bonds`, `cash`, and saves the result.
3. `backtest_openjev.py run` rebalances to the chosen asset on each month-end and on the entry day, through the same engine, fills and tax as the other strategies.

Model: `openjev/OpenJev-Flash-9B-MLX-4bit`, run locally with `mlx-lm`. License is CC-BY-NC-4.0, so research use only. This is the open model from Hugging Face, not the TypeSafe JEV cloud API.
