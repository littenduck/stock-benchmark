"""Where the project's folders are. Every other module takes its paths from here."""
import os

PROJECT_DIRECTORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIRECTORY = os.path.join(PROJECT_DIRECTORY, "frontend")
DATA_DIRECTORY = os.path.join(PROJECT_DIRECTORY, "data")
RUNTIME_DIRECTORY = os.path.join(DATA_DIRECTORY, "runtime")  # generated: downloads, snapshot, logs, caches

SETTINGS_FILE_PATH = os.path.join(DATA_DIRECTORY, "settings", "benchmark.yaml")
WATCHLIST_FILE_PATH = os.path.join(DATA_DIRECTORY, "symbols", "watchlist.yaml")
INDICATOR_FILE_PATH = os.path.join(DATA_DIRECTORY, "indicators", "indicators.yaml")
RULE_FILE_PATH = os.path.join(DATA_DIRECTORY, "rules", "rules.yaml")
BENCHMARK_STRATEGY_DIRECTORY = os.path.join(DATA_DIRECTORY, "strategies")

SNAPSHOT_FILE_PATH = os.path.join(RUNTIME_DIRECTORY, "latest_snapshot.json")
CACHE_DIRECTORY = os.path.join(RUNTIME_DIRECTORY, "cache")
LOG_FILE_PATH = os.path.join(RUNTIME_DIRECTORY, "logs", "stock-benchmark.log")
VERSION_FILE_PATH = os.path.join(PROJECT_DIRECTORY, "version.txt")

if not os.path.isfile(VERSION_FILE_PATH):
    raise SystemExit("project root not found from " + __file__ + ": no version.txt at " + PROJECT_DIRECTORY)
