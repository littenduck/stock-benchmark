"""Run a backtest command: python -m backend.backtest <command> [arguments]

  strategies       every strategy over every entry date (backtest_strategies)
  pair soxx_soxl   a base and leverage pair; or qqq_tqqq (backtest_pair)
  report           Markdown report from the strategies summary (make_report)
  chart [SYMBOL]   price charts and the chart page (make_chart)
  openjev features | run   OpenJev feature export and run (backtest_openjev)
  openjev-decide   OpenJev model decisions through MLX (openjev_decide)
"""
import importlib
import sys

COMMAND_MODULE_BY_NAME = {
    "strategies": "backend.backtest.backtest_strategies",
    "pair": "backend.backtest.backtest_pair",
    "report": "backend.backtest.make_report",
    "chart": "backend.backtest.make_chart",
    "openjev": "backend.backtest.backtest_openjev",
    "openjev-decide": "backend.backtest.openjev_decide",
}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMAND_MODULE_BY_NAME:
        sys.exit(__doc__)
    command = sys.argv[1]
    # Each script reads its own arguments from sys.argv[1:], so drop the command name.
    sys.argv = [sys.argv[0]] + sys.argv[2:]
    importlib.import_module(COMMAND_MODULE_BY_NAME[command]).main()


if __name__ == "__main__":
    main()
