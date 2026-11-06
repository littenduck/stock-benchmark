"""Ask a local OpenJev model for a monthly position decision, and cache every answer.

Run with the MLX environment, not the project Python:
    ~/mlx-env/bin/python scripts/openjev_decide.py

Input : data/runtime/backtest/openjev/features.csv  (written by `python -m backend.backtest openjev features`)
Output: data/runtime/backtest/openjev/decisions.json (resumable; a date already in the file is skipped)

The model never writes free text. The prompt ends right where the answer starts, and the
four option words are scored by next-token probability. So the answer is always one of the
four options, there is nothing to parse, and the same prompt always gives the same answer.
The prompt has no dates and no tickers, so the model cannot recall what happened next.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import mlx.core as mx
from mlx_lm import load

from backend.shared import project_paths

OUTPUT_DIRECTORY = Path(project_paths.RUNTIME_DIRECTORY) / "backtest" / "openjev"
FEATURES = OUTPUT_DIRECTORY / "features.csv"
DECISIONS = OUTPUT_DIRECTORY / "decisions.json"
MODEL = Path.home() / "models" / "OpenJev-Flash-9B-MLX-4bit"
OPTIONS = ["stocks", "leveraged", "bonds", "cash"]

PROMPT = """You manage one account that holds exactly one position for the next month.
Options:
- stocks: a broad large-cap growth stock index fund
- leveraged: the same fund with 3x daily leverage (large losses in choppy or falling markets)
- bonds: a long-term government bond fund
- cash: no market risk

Facts as of today's close (percent unless noted):
- stock fund vs its 200-day average: {above_sma200:+.1f}
- 50-day average vs 200-day average: {sma50_vs_200:+.1f}
- fall from the 1-year high: {drawdown_252:.1f}
- return over 20 days: {ret_20:+.1f}
- return over 126 days: {ret_126:+.1f}
- return over 252 days: {ret_252:+.1f}
- volatility over 20 days, annualized: {vol_20:.1f}
- RSI(14), 0 to 100: {rsi14:.0f}
- bond fund return over 126 days: {bond_ret_126:+.1f}

Reply with exactly one lowercase word from: stocks, leveraged, bonds, cash."""


def option_tokens(tok) -> list[int]:
    ids = [tok.encode(w, add_special_tokens=False)[0] for w in OPTIONS]
    if len(set(ids)) != len(ids):
        sys.exit(f"option words share a first token: {ids}")
    return ids


def main() -> None:
    rows = list(csv.DictReader(open(FEATURES)))
    done = json.loads(DECISIONS.read_text()) if DECISIONS.exists() else {}
    todo = [r for r in rows if r["date"] not in done]
    print(f"{len(rows)} dates, {len(done)} cached, {len(todo)} to ask", flush=True)
    if not todo:
        return

    model, tok = load(str(MODEL))
    ids = option_tokens(tok)
    for i, row in enumerate(todo, 1):
        text = PROMPT.format(**{k: float(v) for k, v in row.items() if k != "date"})
        chat = tok.apply_chat_template([{"role": "user", "content": text}],
                                       add_generation_prompt=True, tokenize=False, enable_thinking=False)
        logits = model(mx.array(tok.encode(chat, add_special_tokens=False))[None])[0, -1, :]
        logp = logits - mx.logsumexp(logits)
        opt_logp = [float(logp[t]) for t in ids]
        mass = sum(mx.exp(mx.array(opt_logp)).tolist())  # probability the model put on the four words
        probs = [float(p) / mass for p in mx.exp(mx.array(opt_logp)).tolist()]
        best = max(range(len(OPTIONS)), key=probs.__getitem__)
        done[row["date"]] = {
            "action": OPTIONS[best],
            "confidence": round(probs[best], 4),
            "probs": {w: round(p, 4) for w, p in zip(OPTIONS, probs)},
            "option_mass": round(mass, 4),
            "prompt_sha": hashlib.sha1(text.encode()).hexdigest()[:10],
        }
        if i % 10 == 0 or i == len(todo):
            DECISIONS.write_text(json.dumps(done, indent=1, sort_keys=True))
            print(f"{i}/{len(todo)}  {row['date']}  {OPTIONS[best]}  {probs[best]:.2f}  mass {mass:.2f}", flush=True)


if __name__ == "__main__":
    main()
