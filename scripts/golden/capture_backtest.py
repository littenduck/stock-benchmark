"""Capture the strategy backtest outputs with fixed prices, so the result does not change with Yahoo.

Usage:
    .venv/bin/python scripts/golden/capture_backtest.py record     # once: download and store the prices
    .venv/bin/python scripts/golden/capture_backtest.py replay --label p0

record stores every yfinance.download result in ~/stock-benchmark-golden/fixtures/prices/.
replay runs the strategy backtest with those stored prices and writes the CSV and chart files to
~/stock-benchmark-golden/<label>/backtest/. To keep the run short, only the first GOLDEN_ENTRY_COUNT
entry dates are run; the same count is used for every label, so the comparison is fair.
"""
import argparse
import hashlib
import os
import pickle
import shutil
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GOLDEN_ROOT = os.path.expanduser("~/stock-benchmark-golden")
PRICE_DIRECTORY = os.path.join(GOLDEN_ROOT, "fixtures", "prices")
GOLDEN_ENTRY_COUNT = 3


def price_key(args: tuple, kwargs: dict) -> str:
    return hashlib.sha256(repr((args, sorted(kwargs.items()))).encode("utf8")).hexdigest()[:24]


def install_record_or_replay(mode: str) -> None:
    import yfinance

    real_download = yfinance.download
    os.makedirs(PRICE_DIRECTORY, exist_ok=True)

    def recording_download(*args, **kwargs):
        path = os.path.join(PRICE_DIRECTORY, price_key(args, kwargs) + ".pkl")
        if mode == "record":
            data = real_download(*args, **kwargs)
            with open(path, "wb") as price_file:
                pickle.dump(data, price_file)
            return data
        if not os.path.exists(path):
            raise FileNotFoundError("no recorded prices for this download; run record first: " + path)
        with open(path, "rb") as price_file:
            return pickle.load(price_file)

    yfinance.download = recording_download


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["record", "replay"])
    parser.add_argument("--label", default="p0")
    args = parser.parse_args()

    install_record_or_replay(args.mode)
    sys.path.insert(0, PROJECT_ROOT)
    from backend.backtest import backtest_strategies as bs

    bs.ENTRY_SCENARIOS = bs.ENTRY_SCENARIOS[:GOLDEN_ENTRY_COUNT]
    output = os.path.join(GOLDEN_ROOT, args.label, "backtest")
    shutil.rmtree(output, ignore_errors=True)
    os.makedirs(output)
    bs.OUT_DIR = __import__("pathlib").Path(output)
    bs.main()
    print("backtest outputs in", output)


if __name__ == "__main__":
    main()
