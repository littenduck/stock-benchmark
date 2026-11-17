# Grokbot scanning

> 在本仓库里，这套代码放在 `grokbot_scanning/` 下，必须在该目录里运行，这样 `scripts/lib/common.py` 的 `BASE` 才会指向正确的根目录。例如：
>
> ```bash
> cd grokbot_scanning && python3 scripts/run.py premarket --no-ledger
> ```
>
> 不要在仓库根目录直接跑 `python3 scripts/run.py`，那会找不到 `lists.md`。


Kaiwen 的美股盯盘团队在 Grok Bot 上的运行环境快照（2026-11-17）。这是一套**新代码和新工作流**，用来把当前共享文件夹、Python 管线和六个 bot 的提示词存进仓库，不必与任何已有 `main` 分支对齐。

只盯盘，不下单。脚本和 bot 都不调用券商交易接口。分析员不给个股买卖指令、不谈仓位大小；杠杆 ETF（SPXL / TQQQ / SOXL / RAM）的操作提示只由首席策略官基于对应的 1x ETF（SPY / QQQ / SOXX / DRAM）写出。不做同业分析。

更细的流程、每只 bot 的读写信件和 Kaiwen 给首席的最新要求原文，见 [docs/WORKFLOWS.md](docs/WORKFLOWS.md)。六个 bot 的 profile 原文和当前 routine 提示词在 [prompts/](prompts/)。

## 架构

六个 Grok Bot 共用同一台电脑上的文件夹（部署时为 `/home/box/shared/stock-team/`）：

| Bot | 职责 | 定时（美东） |
|---|---|---|
| 盯盘6 首席策略官 | 跑脚本、读摘要、汇总、评级、台账、推送给 Kaiwen | 工作日 9:00 盘前、11:00 盘中、17:00 盘后；周六 0:00 周报；周一 0:00 前瞻 |
| 盯盘1 宏观面 | 脚本做不了的政策、加息概率、日历；可选 `overrides.json` | 每周一 8:30 |
| 盯盘2 基本面 | 定性：指引、行业周期、三情景估值 | 每周五 16:30 |
| 盯盘3 技术面 | 无定时。只在首席点名时深挖低周期结构 | 按需 |
| 盯盘4 期权面 | 空头、Form 4、13F、ETF 资金流、财报隐含波动 | 每周五 16:30 |
| 盯盘5 情绪面 | X / Reddit / Stocktwits / 韩国情绪 / 操纵迹象 | 每个工作日 16:30 |

日常数字（行情、技术指标、宏观读数、期权代理分、加权总分）由 `scripts/run.py` 一次算完。首席每档先跑脚本，再读约 2–3KB 的 `summary-<档>.md`，按 `format.md` 写给 Kaiwen 的简报或完整总览。

标的清单在 `lists.md`（只扫 1x ETF 和指定个股）。`X_ACCOUNTS` 和 `POSITIONS` 目前是空的；首席在 POSITIONS 留空时可以只读拉取 Robinhood 持仓，仍然不得下单。

## 目录

为了让脚本的相对路径继续成立，本仓库保持与线上一致的布局：`lists.md`、`reports/`、`data/`、`ledger.md` 与 `scripts/` 同级。

```
.
├── scripts/           # run.py 与 lib/
├── lists.md           # 标的与约束
├── format.md          # 首席总览和评级规则
├── ledger.md          # 五面评分命中率台账
├── rating-ledger.md   # 首席评级准确度台账
├── data/              # 跨日历史（iv_history.csv）
├── overview/          # 首席总览样例（持仓细节已脱敏）
├── reports/           # 脚本摘要与分析员报告样例
├── docs/WORKFLOWS.md
├── prompts/           # 六个 bot 的 profile + 当前 routine
└── README.md
```

`scripts/lib/common.py` 使用 `BASE = Path(__file__).resolve().parents[2]`（`scripts/lib/` 再向上两级），因此**不要**把 `lists.md` / `reports/` / `data/` 挪到别的子目录后再直接跑脚本。注释里写的 `/home/box/shared/stock-team` 只是线上路径说明，不是字面量硬编码。

## 依赖

- Python 3（在 Grok Bot 的电脑上验证过 3.13；3.10+ 应可运行）
- 第三方库：`pandas`、`numpy`、`requests`（线上已装；本快照记录的版本约为 pandas 3.0、numpy 2.5、requests 2.34）
- 标准库即可，无其他 pip 依赖。不需要 `yfinance`。
- 网络：Yahoo Finance（chart / options / quoteSummary）、FRED `fredgraph.csv`、CNN 恐惧与贪婪。全程只读公开 HTTP，不登录券商。

安装示例：

```bash
python3 -m pip install pandas numpy requests
```

## 如何运行脚本

先进入本目录（克隆仓库后是 `grokbot_scanning/`），再调用脚本：

```bash
cd grokbot_scanning
python3 scripts/run.py --help
python3 scripts/run.py premarket --no-ledger
```

也可以再进入 `scripts/`：

```bash
cd grokbot_scanning/scripts
python3 run.py --help
python3 run.py premarket                 # 盘前，默认美东今天
python3 run.py intraday                  # 盘中
python3 run.py postmarket --no-ledger    # 盘后，不改 ledger.md（首席线上用法）
python3 run.py postmarket                # 盘后，并更新 ledger.md
python3 run.py postmarket --date 2026-11-16
```

需要先有 `lists.md` 的 TICKERS。输出写到 `reports/<YYYY-MM-DD>/`：

- `summary-<mode>.md` / `summary-<mode>.json`
- `data/{technical,options,macro,fundamental,sentiment}-<mode>.json`

可选输入：同日的分析员 `*.md` 或 `<panel>.scores.json`、`overrides.json`。IV 历史追加到仓库根下的 `data/iv_history.csv`。已知限制（期权夜间 OI 常为 0、`--date` 回放时期权不是历史快照等）见 `scripts/README.md`。

## 在 Grok Bot 上部署

1. 把 `grokbot_scanning/` 文件夹里的内容复制到 Grok Bot 电脑上的 `/home/box/shared/stock-team/`（不要把 `grokbot_scanning` 这一层目录名一起拷进去；或先放别处，再保证 `scripts/` 与 `lists.md`、`reports/`、`data/` 的相对关系不变）。目录不存在就建：`mkdir -p /home/box/shared/stock-team/{scripts/lib,reports,data,overview}`。
2. 确认该环境已有 Python 3 和上述三个库。跑一次 `python3 scripts/run.py --help`，再视需要跑一档 `premarket` 做连通性检查。
3. 按 `lists.md` 填 TICKERS；需要时再填 `X_ACCOUNTS`、`POSITIONS`。
4. 建六个 agent，名称与 id 建议与现网一致（否则要改首席 routine 里的 SendToAgent 目标）：
   - 盯盘1 宏观面 `b52b2096-e782-4807-8775-5f0099eb0c03`
   - 盯盘2 基本面 `4d9e79b3-a1cc-423b-8abf-6c46ddbb823d`
   - 盯盘3 技术面 `33df0d45-777f-40eb-a942-bba2f8c3a967`
   - 盯盘4 期权面 `a6c1631f-ac36-4325-ac12-49588cde8791`
   - 盯盘5 情绪面 `d7872a19-30c2-43c0-a14f-99ea99a2e800`
   - 盯盘6 首席策略官 `c19daea6-4a7d-4157-b0f6-86e6f7b4e94d`
5. 把 `prompts/` 里每个文件的「Agent profile」段贴进对应 bot 的描述。注意：profile 仍是创建时的职责说明书；**真正定时执行的是文件后半的 routine 提示词**。请按其中的 cron（时区 `America/New_York`）为各 bot **自己**创建 routine（一个 bot 不能改另一个 bot 的 routine）。
6. 时间表详见 `docs/WORKFLOWS.md`。要点：首席工作日 9:00 / 11:00 / 17:00 先跑脚本；情绪面每个工作日 16:30；基本面和期权面周五 16:30；宏观面周一 8:30；技术面不建定时任务。
7. 把各 bot 对 Kaiwen 的推送规则保持为「红才主动叫人、绿且无变化不打扰」。任何 bot 都不得调用下单或改账户工具。

## 输出约定

- 脚本摘要：`reports/<日期>/summary-premarket|intraday|postmarket.md`
- 分析员报告：`reports/<日期>/{macro,fundamental,technical,options,sentiment}.md`（以及可选的 `*.scores.json`、`overrides.json`）
- 首席给 Kaiwen 的盘前/盘中一页结论：`overview/<日期>-premarket.md`、`overview/<日期>-intraday.md`
- 盘后完整总览：`overview/<日期>.md`，并覆盖 `overview/latest.md`
- 台账：`ledger.md`、`rating-ledger.md`

样例里的 `overview/` 和 `reports/` 是 2026-11-16 模拟盘后与 2026-11-17 盘前/盘中的真实输出。从 Robinhood 只读拉取的**个人持仓数量、成本、期权张数和权利金**已在样例中替换为 `（已脱敏）`。公开市场价格未改。

## 约束（必须保留）

- 只盯盘，不下单。禁止给任何下单、改单、撤单、转账或修改账户的工具。
- 分析员不给买卖指令，不谈仓位大小。
- 只有首席可以对 SPXL、TQQQ、SOXL、RAM 写操作提示，而且必须基于 1x ETF 的扫描。
- 权重和评级阈值的修改由 Kaiwen 决定，bot 只给建议。
