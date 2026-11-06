# Stock Benchmark

A personal stock dashboard. It shows market indicators and followed symbols, each with a **pass** result and a **score**. Select a symbol to see its strategy tree, gate by gate and rule by rule.

## Architecture

```
stock-benchmark/
├── frontend/          pages: HTML, CSS, JS
├── backend/           Python code
│   ├── app/           web server and API (top layer)
│   ├── benchmark/     dashboard data and scoring
│   ├── backtest/      strategy backtests
│   └── shared/        helpers used by the layers above
├── data/              hand-edited YAML: strategies, symbols, indicators, rules, settings
│   └── runtime/       generated, git-ignored
├── scripts/           dev tools
├── tests/             pytest
├── docs/              documentation
└── licenses/          third-party notices
```

## Setup

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

## Run

```bash
.venv/bin/python -m uvicorn backend.app.web_server:app --port 8000
```

Open http://localhost:8000. Data refreshes in the background while the US market is open. Refresh once by hand:

```bash
.venv/bin/python -m backend.benchmark.refresh_scheduler --once
```

## Test

```bash
.venv/bin/python -m pytest tests
```

## Where things are

| To change | Edit |
|---|---|
| Followed symbols | `data/symbols/watchlist.yaml` |
| Strategies | `data/strategies/*.yaml` (see `docs/strategy.md`) |
| Rules and indicators | `data/rules/rules.yaml`, `data/indicators/indicators.yaml` (see `docs/indicator.md`) |
| Refresh interval, sidebar indicators | `data/settings/benchmark.yaml` |
| Page design | `docs/design.md` |
| JSON API | `docs/api.md` |
| Deployment | `docs/deployment.md` |
| Dev tools (icons, golden tests, one-off analysis) | `scripts/` |
| Tests | `tests/` |

Restart the server after changing any YAML file.

## Version and license

The version is in `version.txt` (`MAJOR.MINOR.PATCH`). The page header and `GET /api/v1/version` read it, so a release changes only that file. The code is MIT licensed; see `LICENSE`. Icons come from Tabler Icons (MIT, see `licenses/`); `scripts/build_icons.py` rebuilds them after `npm install`.
