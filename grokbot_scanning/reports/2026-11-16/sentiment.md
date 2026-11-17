# 情绪面报告 · 2026-11-16（美东）· 盯盘5 情绪面分析员

> 本文件为**模拟测试**：按「盘后 16:30」档职责强制完整扫描（未做跳过判断）。实际执行时间为 2026-11-17 凌晨（美东），数据窗口为最近交易日 2026-11-16 及其后至扫描时刻。
> 只写情绪面；不含价格技术面、财报估值、期权策略、宏观指标。帖子是观点，传闻标"未证实"。判断类语句以"判断："开头。

## 总览

| 标的 | 评分 | 警报 | 置信度 | X 提及量倍数（11/16 vs 7日均） | X 多空比（有效样本） | 一句话 |
|---|---|---|---|---|---|---|
| SPY | 0 | 🟢 绿 | 中 | 1.04x | 17:20（48） | 散户调查偏悲观、社媒偏多，分歧未达极端 |
| QQQ | 0 | 🟢 绿 | 中 | 1.22x | 11:16（50） | "进入回调"叙事主导，偏空但无恐慌放量 |
| SOXX | 0 | 🟢 绿 | 中 | 1.14x | 7:21（50，含噪音） | 半导体明显偏空，"连 Leopold 都撤了"式叙事出现，但无投降性放量 |
| DRAM | 0 | 🟢 绿 | 低 | 1.52x | 8:13（47，多为存储泛讨论） | 存储 ETF 讨论量小，焦点在 Leopold 13F 与韩国外资抛售 |
| SNDK | 0 | 🟢 绿 | 中 | 1.13x | 10:9（35，已剔除15条刷屏） | 多空打平；13F"大佬清仓"与"最低估"并存，11/19 拆股前 |
| MU | 0 | 🟢 绿 | 中 | 1.29x | 11:12（46） | 13F 分化叙事（Leopold 清仓 vs Tepper 头号持仓），情绪中性偏谨慎 |
| MRVL | 0 | 🟡 黄 | 中 | 1.07x | 7:5（37，已剔除10条） | 讨论冷清，但出现 WhatsApp 拉群+复制粘贴帖，疑似操纵 |
| NVDA | 0 | 🟡 黄 | 中 | 0.80x | 14:15（48） | 今晚财报前多空严重分歧：Stocktwits"极度看多" vs Reddit/期权散户偏空 |
| RKLB | 0 | 🟢 绿 | 中 | 0.95x | 7:1（44，已剔除4条） | 第100次 Electron 发射带来正面叙事，讨论量平稳 |
| SPCX | 0 | 🟢 绿 | 中 | 1.05x | 11:7（49） | SpaceX（Nasdaq: SPCX）13F 机构加仓叙事偏多，未见过热 |

- **事件触发检查**：10 个标的 X 提及量均**未超过 7 日均值 3 倍**（最高 DRAM 1.52x）。本档使用的黄色触发条件：①提及量≥3x；②社媒平台出现"极度看多/极度看空"读数；③疑似操纵或未证实传闻成批扩散；④24 小时内本标的有重大情绪事件。NVDA 命中②③④，MRVL 命中③ → 黄色。无红色。
- **韩国模块（存储/半导体）**：韩国情绪 **悲观**；与美国方向**一致（偏空）**，但韩国更悲观（外资连续大额抛售，KOSPI 11/17 跌破 5000）。
- **全市场散户调查**：AAII（截至 11/11 当周）看多 30.8% / 看空 51.4%；NAAIM 72.90（11/13，较前周 78.62 下降）。
- **重点 X 账号**：lists.md 中 X_ACCOUNTS **清单为空**，本次按标的全站搜索。

---

## 盘后 16:30（模拟测试）

### 0. 方法与口径（自检用）

- **X 数据**：x 连接器 `get_posts_counts_recent`（日粒度）+ `search_posts_all`（每标的 2 次 × 25 条：①72 小时相关度排序，start 2026-11-14 07:45 UTC；②11/16 00:00 ET 之后按时间排序）。抓取时间 2026-11-17 02:40–02:44 ET。
  - X API 不接受 `$` 符号（连接器提示"$ was removed"），所以用关键词：SPY=`SPY (stocks OR market OR calls OR puts OR ETF)`；QQQ=`QQQ`；SOXX=`SOXX`；DRAM=`DRAM (ETF OR Roundhill)`；SNDK=`SNDK OR Sandisk`；MU=`Micron`；MRVL=`MRVL OR Marvell`；NVDA=`NVDA OR Nvidia`；RKLB=`RKLB OR "Rocket Lab"`；SPCX=`SPCX OR "SpaceX stock" OR "SpaceX shares"`，均排除转推。
  - **提及量倍数** = 2026-11-16 UTC 自然日（即 11/15 19:00–11/16 19:00 ET）帖数 ÷（7 天窗口总帖数/7）。7 天窗口为 2026-11-10 07:40 UTC 至 2026-11-17 07:40 UTC。
  - **多空比**：两次搜索合并去重后，先剔除刷屏/拉群/复制粘贴帖（单独列入"疑似操纵"），再按关键词规则分类；"中性"包含纯新闻、无方向帖和噪音。属于自动规则分类，不是逐条人工判读。
- **Reddit**：reddit.com 直连返回 403，改用 StonkHub 聚合页（Reddit 7 日提及与分类，二手数据），抓取时间约 02:44 ET。
- **Stocktwits**：各标的页面的情绪分数和消息量标签，抓取时间约 02:43 ET（页面上同时有两个读数，下文只引用首个展示值）。
- **AAII / NAAIM / 媒体 / 韩国新闻**：WebSearch/WebFetch，来源见各条链接。

### 1. SPY

- **标的**：SPDR S&P 500 ETF（1x）
- **数据时间**：X 2026-11-16 至 2026-11-17 02:44 ET；Stocktwits 11-17 ~02:43 ET；AAII 截至 11-11 当周；NAAIM 11-13
- **评分**：0　**上次评分**：无上次记录　**变化原因**：首份报告
- **置信度**：中　**适用期限**：短线
- **一句话结论**：散户调查明显偏悲观（AAII 看空 51.4%），社媒平台却偏多（Stocktwits Bullish 63），分歧没到极端，也没有投降迹象。
- **提及量**：11/16 共 2,302 帖，7 日均 2,215 帖/日 → **1.04x**（X counts）
- **多空比**：X 17 多 : 20 空（有效样本 48，中性 11）；Reddit（StonkHub，7 日 386 条提及）看多 28.2% / 中性 50.3% / 看空 21.5%；Stocktwits 63 "Bullish"，消息量 normal
- **主流叙事前 3**：①英伟达领导层危机拖累指数、"AI 交易回撤"；②"是熊市陷阱，会有圣诞反弹"与"趋势转空"互相对立；③大机构上调年底/2027 目标（摩根士丹利 8,700）与"崩盘预言"并存
- **极端信号**：AAII 看空 51.4%，连续 40 周高于历史均值 31.5%（官方注明 unusually high）。属于调查端的极端读数，但社媒端未同步。
- **疑似操纵**：未发现
- **证据**：
  1. AAII 截至 11/11：看多 30.8%、中性 17.8%、看空 51.4%，多空差 −20.6pp —— https://www.aaii.com/sentimentsurvey/sent_results （11-12 发布）
  2. NAAIM 暴露指数 72.90，前周 78.62，"近两个月最低，谨慎但不看空" —— https://www.isabelnet.com/investor-sentiment-naaim-exposure-index-and-sp-500/ （11-13，二手转述；NAAIM 官网实时数据需订阅）
  3. "this REEKS of a bear trap. Santa rally…"（多头观点）—— https://x.com/gg_rawb/status/2122594339180458084 （11-17 02:35 ET）
  4. "we might be seeing a trend reversal to the bearish side for SPY"（空头观点）—— https://x.com/ettty_19/status/2122562711326495226 （11-17 00:29 ET）
  5. 摩根士丹利 S&P 目标 8,700，"抛售是买入机会"（转述）—— https://x.com/JohnnyNorthstar/status/2122349828134871113 （11-16 10:23 ET，赞 0）
- **关键价位（社媒提及）**：SPY 740 / 734 / 742 / 745（https://x.com/PrimeTimeOpt/status/2122576903274139784 ；https://x.com/FregosoCapital/status/2122594932758323613 ）；SPX 7,400 / 7,450 / 7,350（https://x.com/Conservative_Dh/status/2122566774449148137 ）。各来自单一账号，算不上"反复提及"。
- **失效条件**：AAII 看空回落到 40% 以下，或社媒转为一致看空、且 SPY 提及量 ≥3x（会转向投降判断）
- **未来 7 天事件**：11/17 盘后 NVDA 财报；11/18 FOMC 会议纪要；11/19 Anthropic IPO（报道称周四上市）；11/19 AAII 新一期
- **数据缺口**：Reddit 为聚合站二手数据；关键词"SPY"会混入"spy（间谍）"类噪音帖
- **警报级别**：🟢 绿

### 2. QQQ

- **标的**：Invesco QQQ Trust（1x）
- **数据时间**：X 2026-11-14 至 11-17 02:44 ET；Stocktwits/StonkHub 11-17 ~02:44 ET
- **评分**：0　**上次评分**：无上次记录　**变化原因**：首份报告
- **置信度**：中　**适用期限**：短线
- **一句话结论**：社媒以"纳指进入回调、跌破 200 日线"为主线，偏空，但讨论量只有 1.22x，没有恐慌性放量。
- **提及量**：11/16 共 6,851 帖，7 日均 5,635 → **1.22x**
- **多空比**：X 11 多 : 16 空（有效 50，中性 23）；Reddit（7 日 205 条）看多 35.1% / 中性 39.0% / 看空 25.9%；Stocktwits 63 "Bullish"，消息量 normal
- **主流叙事前 3**：①"纳指回调/双顶/Stage 4"；②"指数强是假象，权重股撑场"；③做空兴趣升高（二手，未证实）
- **极端信号**：未见
- **疑似操纵**：未发现
- **证据**：
  1. "Nasdaq 100 $QQQ – weekly Stage Analysis… Currently in early Stage 4"，赞 105 / 浏览 13,102 —— https://x.com/stageanalysis/status/2121571348610678840 （11-14 06:50 ET）
  2. "Everyone who has bought tech in the last 6 months is bagholding…"（空头观点）—— https://x.com/WitnessDecline/status/2122589913346682934 （11-17 02:17 ET）
  3. "QQQ short interest… about 11% of shares outstanding, the highest since 2023"（转述 Kobeissi/JPM，**未证实**）—— https://x.com/0xlunasterling/status/2121989644396949679 （11-15 10:32 ET）
  4. "Best time to buy the dips might be NOW"（多头观点）—— https://x.com/ClosedLoopSys/status/2122588643449819577 （11-17 02:12 ET）
  5. Reddit 7 日 205 条提及，WSB 参与人数比上周 −51%（69 人 vs 140 人）—— https://stonkhub.io/stocks/QQQ （~02:44 ET）
- **关键价位（社媒提及）**：635（https://x.com/equitydd/status/2122591524454388219 ）；单一账号提及，不算反复。
- **失效条件**：QQQ 提及量 ≥3x 且出现集中"清仓/认输"帖，或 Stocktwits 转为极端读数
- **未来 7 天事件**：NVDA 财报（11/17 盘后）；FOMC 纪要（11/18）；Anthropic IPO（11/19）
- **数据缺口**：做空兴趣数据只有二手转述
- **警报级别**：🟢 绿

### 3. SOXX

- **标的**：iShares Semiconductor ETF（1x）
- **数据时间**：X 2026-11-14 至 11-17 02:44 ET；Stocktwits/StonkHub 11-17 ~02:44 ET
- **评分**：0　**上次评分**：无上次记录　**变化原因**：首份报告
- **置信度**：中（按时间排序的样本混入了不少体育"semis"噪音，已计入中性）
- **适用期限**：短线
- **一句话结论**：半导体板块情绪明显偏空，也出现了"还有谁没撤"式的认输叙事，但提及量只有 1.14x，没有投降性放量，暂不加分。
- **提及量**：11/16 共 732 帖，7 日均 640 → **1.14x**
- **多空比**：X 7 多 : 21 空（有效 50，中性 22，含噪音）；Reddit（7 日 35 条）看多 34.3% / 中性 20.0% / 看空 45.7%；Stocktwits 30 "Bearish"，消息量 normal
- **主流叙事前 3**：①"连 Leopold 都退出半导体了，还有谁在？"（13F 叙事）；②BIS 远程访问芯片新规叠加 NVDA 财报前避险；③Burry 空头押注"正在兑现"
- **极端信号**：Stocktwits 30（Bearish，未到"Extremely Bearish"）；认输式叙事出现（证据 1）。判断：属于偏空，还不是极端看空加投降，所以评分维持 0。
- **疑似操纵**：未发现
- **证据**：
  1. "So even Leopold has exited the Semis trade. I wonder if there is anyone left in the trade?"，赞 28 / 浏览 4,506（作者 30 万粉）—— https://x.com/AndreasSteno/status/2122591019355283920 （11-17 02:21 ET）
  2. Gavin Baker 的 Atreides 13F："bought puts on chip stocks and sold 57% of his Micron"，赞 707 / 浏览 166,336 —— https://x.com/burrytracker/status/2122448846106370414 （11-16 16:56 ET；13F 为 9/30 快照，未独立核实）
  3. Peter Thiel 的 Thiel Macro 三季度买入 1.61 亿美元 SOXX（多头叙事），浏览 38,583 —— https://x.com/WOLF_Financial/status/2122439880303112649 （11-16 16:21 ET）
  4. "I don't think this is a dip to buy… Sitting this one out." —— https://x.com/ccccyyyccyy/status/2122592209036009479 （11-17 02:26 ET）
  5. Stocktwits SOXX 情绪 30（Bearish）、消息量 normal —— https://stocktwits.com/symbol/SOXX （~02:43 ET）
- **关键价位（社媒提及）**：无
- **失效条件**：NVDA 财报后半导体讨论转为一致看多，或提及量 ≥3x 且出现集中认输帖（后者会转 +1 评估）
- **未来 7 天事件**：NVDA 财报（11/17 盘后）；APEC（11/18–19）期间中美可能接触（报道称"可能"）；FOMC 纪要（11/18）
- **数据缺口**：关键词"semis"噪音大；X 不支持 `$SOXX` cashtag 精确检索
- **警报级别**：🟢 绿（判断：偏空情绪需要盯 NVDA 财报后的变化）

### 4. DRAM

- **标的**：Roundhill Memory ETF（Cboe BZX: DRAM，2026-04-02 成立，主动管理）。**跟踪对象**：全球存储芯片公司，直接持股加总收益互换。截至 2026-09-30 官方前十大：美光 26.45%、三星 24.80%、SK 海力士 22.50%、长鑫 CXMT 5.06%、希捷 4.76%、闪迪 4.72%、西数 3.63%、铠侠 3.24%、南亚科 2.48%、华邦 1.15%；地区上韩国 47.30%、美国 39.56%（https://www.roundhillinvestments.com/assets/pdfs/dram_factsheet.pdf ）。另据 stockanalysis 11/16 持仓页，三星直接持股 19.51%、海力士 15.22%，美光主要通过互换持有（https://stockanalysis.com/etf/dram/holdings/ ）。
- **数据时间**：X 2026-11-14 至 11-17 02:44 ET；Stocktwits ~02:43 ET
- **评分**：0　**上次评分**：无上次记录　**变化原因**：首份报告
- **置信度**：低（ETF 专属讨论少，按时间排序样本多为存储行业泛讨论）
- **适用期限**：短线
- **一句话结论**：DRAM 本身讨论量小但升到 1.52x，话题集中在 Leopold 13F（清掉美光/闪迪正股，保留 DRAM 看涨期权）和韩国外资抛售三星、海力士。
- **提及量**：11/16 共 71 帖，7 日均 47 → **1.52x**（基数小）
- **多空比**：X 8 多 : 13 空（有效 47，中性 26）；Reddit 无数据（StonkHub 无 DRAM 页）；Stocktwits 46 "Neutral"，消息量 low
- **主流叙事前 3**：①Leopold 13F：清掉美光/闪迪正股，持有 DRAM 看涨期权（约 1.40 亿美元名义）；②KOSPI 定价"2027 年存储放缓" vs TrendForce 称 Q4 DRAM/HBM 价格仍涨；③海力士"订单排满到 2029，客户才是风险方"
- **极端信号**：未见
- **疑似操纵**：未发现
- **证据**：
  1. LeopoldTracker：Leopold 卖出全部闪迪、美光正股（超 110 亿美元），持有 Roundhill Memory ETF 看涨期权 8.9%，赞 1,731 / 浏览 604,593 —— https://x.com/LeopoldTracker_/status/2122445240762056948 （11-16 16:42 ET；13F 为 9/30 快照）
  2. "KOSPI is pricing a 2027 memory slowdown… TrendForce has Q4 DRAM/HBM prices +10–20% Q/Q"（观点，TrendForce 数据**未独立核实**）—— https://x.com/dolphinR123/status/2122592409758605329 （11-17 02:27 ET）
  3. 媒体转述："The Roundhill Memory ETF (DRAM) tumbled 7%"（11/16 盘中）—— https://x.com/videoneonr/status/2122379177504780407 （11-16 12:20 ET）
  4. 一笔 21.56 万美元 DRAM 11/20 到期看涨期权大单，"delusional or genius?"（只作情绪证据，不做期权分析）—— https://x.com/Financhle/status/2122351158266339742 （11-16 10:28 ET）
  5. Stocktwits DRAM 46（Neutral）、消息量 low —— https://stocktwits.com/symbol/DRAM （~02:43 ET）
- **关键价位（社媒提及）**：无
- **失效条件**：韩国外资转为净买入三星/海力士；或 DRAM 提及量 ≥3x
- **未来 7 天事件**：NVDA 财报（11/17 盘后，韩国时间 11/18 早上）对 HBM 预期的影响；Anthropic IPO（韩媒担心分流外资）；闪迪拆股（11/19 收盘后生效）
- **数据缺口**：Reddit 无数据；DRAM 专属帖子少于 20 条有效（判断：置信度只能给低）
- **警报级别**：🟢 绿

### 5. SNDK（闪迪）

- **标的**：Sandisk Corp
- **数据时间**：X 2026-11-14 至 11-17 02:39 ET；Stocktwits/StonkHub ~02:44 ET
- **评分**：0　**上次评分**：无上次记录　**变化原因**：首份报告
- **置信度**：中　**适用期限**：短线
- **一句话结论**：多空基本打平；"多位大佬 13F 清仓"与"最被低估的股票、抄底"同时存在，拆股前没看到过热。
- **提及量**：11/16 共 2,330 帖，7 日均 2,063 → **1.13x**
- **多空比**：X 10 多 : 9 空（有效 35，中性 16；剔除刷屏 15 条）；Reddit（7 日 64 条）看多 35.9% / 中性 25.0% / 看空 39.1%，WSB 参与人数比上周 −68%；Stocktwits 49 "Neutral"，消息量 normal
- **主流叙事前 3**：①13F 清仓：Leopold、Druckenmiller（据 MarketWatch 转述）、Whale Rock 减持；②"距 6 月高点 −60%~−66%，存储过剩"vs"最被低估、可大额回购"；③8 拆 1 拆股（11/19 收盘后生效）
- **极端信号**：未见
- **疑似操纵**（不计入多空比）：@ValuationLab1 在 11-14 15:24–15:27 ET 发了 12 条以上内容相同的"How to Value Sandisk… DCF Walkthrough"回复刷屏（例：https://x.com/ValuationLab1/status/2121701429803188559 ），属于推广刷屏，不带方向；另有 @mark_mtyler 的 WhatsApp 拉群帖（https://x.com/mark_mtyler/status/2122585907345883637 ）。
- **证据**：
  1. "Bought more. Most undervalued stock on the market. $SNDK made $11bn revenue in one quarter"（多头观点）—— https://x.com/_Captain_Obv/status/2122595494459478036 （11-17 02:39 ET）
  2. "The memory glut is the proof — SNDK −66% from its peak"（空头观点）—— https://x.com/qichenos/status/2122590075867550175 （11-17 02:18 ET）
  3. Druckenmiller 家族办公室三季度清仓 AMD、SNDK（转述 MarketWatch，13F 为 9/30 快照）—— https://x.com/SkepticalStud/status/2122595348350742959 （11-17 02:39 ET）
  4. Elliott 波浪"再跌一段见底"，赞 247 / 浏览 16,359 —— https://x.com/CoinvoTrading/status/2121936258155053564 （11-15 07:00 ET）
  5. "Goldman Sachs UPDATED price targets… $SNDK $2,000"，赞 378 / 浏览 60,310（多个账号复制粘贴，**未证实**）—— https://x.com/AnessHusseinAli/status/2122097814326894927 （11-15 17:42 ET）
- **关键价位（社媒提及）**：800（https://x.com/CihunSol/status/2122594969068396584 ）、696（https://x.com/hopabhik111111/status/2122589577764356468 ）。都是单一账号提及；拆股后价格会变为约 1/8。
- **失效条件**：拆股前后提及量 ≥3x 且一边倒看多（会转 −1 评估）；或出现集中割肉帖
- **未来 7 天事件**：**8 拆 1 拆股**：11/19 收盘后生效，11/20 起按拆股后价格交易（https://investor.sandisk.com/static-files/adc41ac6-9db7-4e6a-a29f-f73c1a0123e4 ）；NVDA 财报（11/17）
- **数据缺口**：Goldman 目标价帖没有找到原始出处
- **警报级别**：🟢 绿

### 6. MU（美光）

- **标的**：Micron Technology
- **数据时间**：X 2026-11-14 至 11-17 02:33 ET；Stocktwits/StonkHub ~02:44 ET
- **评分**：0　**上次评分**：无上次记录　**变化原因**：首份报告
- **置信度**：中　**适用期限**：短线
- **一句话结论**：情绪中性偏谨慎，焦点是 13F 分化（Leopold 清仓 vs Tepper 头号持仓）和 11/16 存储股集体下挫后"抄底还是再等一跌"的争论。
- **提及量**：11/16 共 1,987 帖，7 日均 1,544 → **1.29x**（查询词"Micron"）
- **多空比**：X 11 多 : 12 空（有效 46，中性 23）；Reddit（7 日 144 条）看多 45.1% / 中性 22.9% / 看空 31.9%，WSB 参与人数比上周 −63%；Stocktwits 44 "Bearish"，消息量 normal
- **主流叙事前 3**：①13F 分化：Leopold、Atreides 减持 vs Appaloosa 加仓；②"不是周期股、FUD 时买入"vs"还有一浪下跌"；③BIS 新规与 D 램 价格操纵诉讼进入本案审理（韩媒/贴文提及）
- **极端信号**：未见
- **疑似操纵**：未发现针对 MU 的；但"Weekly Recap: Nvidia CEO Jensen Huang resigns after having 3 reported affairs…"在 6 个账号间 30 分钟内逐字复制（见 NVDA 节）
- **证据**：
  1. "$MU is not a cyclical stock… You make your money on the buy when there is FUD"，赞 64 / 浏览 5,974 —— https://x.com/Tickertalk1/status/2122506150163976306 （11-16 20:44 ET）
  2. "Memory chips split the room. Aschenbrenner… sold every $MU and $SNDK share… Tepper's Appaloosa… Micron was its #1 holding, at 17.6%" —— https://x.com/buzzberg_ai/status/2122578084604109093 （11-17 01:30 ET）
  3. "COULD $MU HAVE ONE MORE PULLBACK BEFORE THE NEXT MAJOR BOTTOM?" —— https://x.com/OwenCarter0el/status/2122558965880115617 （11-17 00:14 ET）
  4. Atreides 13F：Micron 减持 57%（转述）—— https://x.com/burrytracker/status/2122448846106370414 （11-16 16:56 ET）
  5. Stocktwits MU 44（Bearish）、消息量 normal；Reddit WSB 本周 65 人 vs 上周 177 人 —— https://stocktwits.com/symbol/MU ；https://stonkhub.io/stocks/MU （~02:44 ET）
- **关键价位（社媒提及）**：664 / 622 / 591 / 542（https://x.com/MentoviaX/status/2122555499014942867 ，同一作者发了两遍）；723–765（https://x.com/MojoTricks/status/2121802187378470998 ）
- **失效条件**：Reddit/Stocktwits 同时转为极端看空并伴随提及量 ≥3x（转 +1 评估）；或 NVDA 财报后一边倒看多
- **未来 7 天事件**：NVDA 财报（11/17 盘后）；闪迪拆股（11/19）；Anthropic IPO（11/19，美光被报道为 IPO 定向买家之一，**未证实**）
- **数据缺口**：查询词"Micron"可能漏掉只写"$MU"的帖子（X 不支持 `$`）
- **警报级别**：🟢 绿

### 7. MRVL

- **标的**：Marvell Technology
- **数据时间**：X 2026-11-14 至 11-17 02:40 ET；Stocktwits/StonkHub ~02:44 ET
- **评分**：0　**上次评分**：无上次记录　**变化原因**：首份报告
- **置信度**：中（Reddit 样本只有 16 条）　**适用期限**：短线
- **一句话结论**：真实讨论冷清，中性偏多（"定制 ASIC/光互连两边都赚"），但样本里有成批 WhatsApp 拉群和复制粘贴帖，需要警惕。
- **提及量**：11/16 共 1,774 帖，7 日均 1,662 → **1.07x**
- **多空比**：X 7 多 : 5 空（有效 37，中性 25；剔除 10 条疑似操纵）；Reddit（7 日 16 条）看多 68.8% / 中性 6.3% / 看空 25.0%，WSB 只有 4 人（−89%）；Stocktwits 42 "Bearish"，消息量 low
- **主流叙事前 3**：①ASIC 与 GPU 之争中两边受益（NVLink Fusion）；②Morningstar 长期预测图表帖（叙事型）；③TD Cowen 下调评级、跌破 200 日线（新闻转发）
- **极端信号**：未见
- **疑似操纵**（单独列出，不计入多空比）：
  - WhatsApp"MRVL 持有人群"拉群帖 5 条，文案相同：@Noahhh_ppp、@LuCyXo_oXFeR、@Galaxyfanfern、@nao_kst、@yenogbra，11-16 23:55 至 11-17 00:35 ET（例：https://x.com/Noahhh_ppp/status/2122564212375621745 ）
  - "Ignore stock prices—focus on projected 4-year earnings growth… Like ❤️ + Follow + Repost"由多个低粉账号在 11-15 06:30–06:32 ET 同时发布（@eldridgedakota2、@leannatoscanog3、@Sez99W、@sanelen56566919 等；例：https://x.com/eldridgedakota2/status/2121929101355389155 ）
  - "If you're under 49, I'll say this only ONCE… 8 stocks that can still 15x: 1. $MRVL"类帖子在多个账号重复出现（https://x.com/babiru36/status/2121786545279766860 ，浏览 20,302）
- **证据**：
  1. "Marvell is the cleaner hedge: it gets paid on custom ASICs and still gets paid when NVLink Fusion wins." —— https://x.com/vietzend/status/2122590752127721819 （11-17 02:20 ET）
  2. "$MRVL: An ABC correction may be unfolding… C-wave decline may still be in progress"（空头观点）—— https://x.com/thequeennnz/status/2122579348104618092 （11-17 01:35 ET）
  3. "The Deal Behind TD Cowen's Downgrade of Marvell"（新闻转发）—— https://x.com/StockTickerZone/status/2121593160719560823 （11-14 08:16 ET）
  4. Reddit 7 日 16 条提及，看多 68.8%（样本极小）—— https://stonkhub.io/stocks/MRVL （~02:44 ET）
  5. Stocktwits MRVL 42（Bearish）、消息量 low —— https://stocktwits.com/symbol/MRVL （~02:43 ET）
- **关键价位（社媒提及）**：140–155"首次建仓区"（https://x.com/RichMargolies/status/2122044933401870630 ），单一账号
- **失效条件**：拉群/复制帖消失，同时真实讨论量恢复；或提及量 ≥3x
- **未来 7 天事件**：无本公司事件（财报 12/1，在 7 天之外）；受 NVDA 财报（11/17）影响
- **数据缺口**：Reddit 样本太小；没法确认拉群账号背后的组织方
- **警报级别**：🟡 黄（触发条件③：疑似操纵）

### 8. NVDA

- **标的**：NVIDIA Corp
- **数据时间**：X 2026-11-14 至 11-17 02:42 ET；Stocktwits ~02:43 ET；Cboe 11-16；StonkHub ~02:44 ET
- **评分**：0　**上次评分**：无上次记录　**变化原因**：首份报告
- **置信度**：中　**适用期限**：短线（财报前后）
- **一句话结论**：今晚财报前多空严重分歧：Stocktwits 显示"极度看多"（散户抄底），Reddit 和期权散户开仓却偏空；不是单边极端，所以评分维持 0，但事件风险高，记黄色。
- **提及量**：11/16 共 92,080 帖，7 日均 114,866 → **0.80x**（高峰是 11/12 的 248,741 帖，即黄仁勋辞职消息当天）
- **多空比**：X 14 多 : 15 空（有效 48，中性 19）；Reddit（7 日 2,301 条）看多 35.6% / 中性 22.5% / 看空 41.9%，WSB 1,053 人（比上周 +166%）；Stocktwits **83 "Extremely Bullish"**，消息量 high
- **主流叙事前 3**：①"第一次没有黄仁勋的财报"：Kress 代任 CEO、董事会排除回归；②领导层丑闻细节与"恢复黄仁勋"呼声（Trump 表态"不介意"、"Stand with Jensen"联署）；③BIS 远程访问新规与中国风险
- **极端信号**：Stocktwits 83 "Extremely Bullish"；Cboe 统计散户期权开仓中买 put 占 32%，今年平均 21%。两者方向相反。判断：散户内部分化，不构成单边极端。
- **疑似操纵 / 未证实传闻**（单独标出）：
  - "Weekly Recap: Nvidia CEO Jensen Huang resigns after having 3 reported affairs…"在 11-15 17:06–17:36 ET 由 6 个账号逐字发布（@MarketNews_Feed、@Geo_News_Alert_、@freebirds0、@peterkkhan、@bitcoinxalerts、@turingbitchaing；例：https://x.com/MarketNews_Feed/status/2122088921974616541 ），属于协同复制分发。辞职本身已有 SEC 8-K 和 CNBC/AP/TechCrunch 证实（https://www.sec.gov/Archives/edgar/data/1045810/000104581026000082/nvda-20261111.htm ），但"3 段婚外情"细节**未证实**。
  - "Jensen Huang linked to an alleged Chinese spy"类说法在多帖中出现，**未证实**（例：https://x.com/fogi70/status/2122572589390270688 ）。
  - "Huang 的 X 认证标被撤、简介改为 Founder"，**未证实**（https://x.com/Selina_market/status/2122595733530636519 ，作者 3 粉）。
- **证据**：
  1. Cboe：NVDA 散户开仓里买 put 占比在周四升至 32%，YTD 均值 21% —— https://www.cboe.com/insights/posts/week-of-11-16-2026-retail-turns-bearish-on-nvda-ahead-of-earnings/ （11-16）
  2. Stocktwits NVDA 情绪 83"Extremely Bullish"、消息量 high；首页多为"buying more at these levels"类帖子 —— https://stocktwits.com/symbol/NVDA （~02:43 ET）
  3. Reddit 7 日 2,301 条提及，看空 41.9% > 看多 35.6%；WSB 24h 热帖"Nvidia board is not considering bringing Jensen Huang back"▲6,604 —— https://stonkhub.io/stocks/NVDA （~02:44 ET）
  4. "I'M OFFICIALLY SCARED OF $NVDA EARNINGS TOMORROW 😩"，赞 27 / 浏览 13,670 —— https://x.com/HandOfCompound/status/2122335332771184929 （11-16 09:25 ET）
  5. "$NVDA Trump says he wouldn't mind seeing Jensen Huang reinstated"，浏览 2,738 —— https://x.com/StockTraderHub/status/2122349206828454115 （11-16 10:20 ET）
- **关键价位（社媒提及）**：158–163（https://x.com/Derek__Whitmore/status/2122558338164781151 ，同一帖在 MU/MRVL 样本里重复出现）；145 / 180（Stocktwits 用户 Nignag）；150 / 160–170（https://x.com/Molina_Jorda/status/2122592183379280081 ）
- **失效条件**：财报后 Stocktwits 与 Reddit 同向（一致看多 → 评估 −1；一致看空加认输 → 评估 +1）；提及量 ≥3x
- **未来 7 天事件**：**11/17 盘后 Q3 FY27 财报，17:00 ET 电话会**（Kress 首次以代任 CEO 身份主持）；11/18 FOMC 纪要；11/19 Anthropic IPO
- **数据缺口**：Reddit 为二手聚合；Stocktwits 只有标签，没有消息量数值
- **警报级别**：🟡 黄（触发条件②③④）

### 9. RKLB（Rocket Lab）

- **标的**：Rocket Lab
- **数据时间**：X 2026-11-14 至 11-17 02:39 ET；Stocktwits/StonkHub ~02:44 ET
- **评分**：0　**上次评分**：无上次记录　**变化原因**：首份报告
- **置信度**：中　**适用期限**：短线
- **一句话结论**：第 100 次 Electron 发射带来正面叙事，社媒偏多，但 Stocktwits 标签偏空，讨论量平稳（0.95x）。
- **提及量**：11/16 共 2,245 帖，7 日均 2,356 → **0.95x**
- **多空比**：X 7 多 : 1 空（有效 44，中性 36；剔除 4 条推广帖）；Reddit（7 日 37 条）看多 62.2% / 中性 16.2% / 看空 21.6%；Stocktwits 40 "Bearish"，消息量 normal
- **主流叙事前 3**：①Electron 第 100 次发射，"史上最快"；②ULA Vulcan 失败（40 颗 Amazon Leo 卫星损失）凸显发射运力稀缺，被视为利好；③Neutron 推迟到 2027 年，散户"要日期、要订单"
- **极端信号**：未见
- **疑似操纵**（不计入）：@pledisme 与 @banks_abanks 发相同的"As a reference, I've called… $RKLB at $16 → +844%"推广文；@StockSavage6x 与 @bull_fool25952 发相同的"aggressive bull-case targets… $RKLB $230"（例：https://x.com/pledisme/status/2122586625691533356 ；https://x.com/StockSavage6x/status/2122573032208343106 ）
- **证据**：
  1. "Feels good to be a Rocket Lab investor right now. Electron just became the fastest commercial rocket to reach 100 launches"，赞 137 / 浏览 7,368 —— https://x.com/Neil_Shares/status/2121801422278963384 （11-14 22:04 ET）
  2. "Considering the current launch constraints… $RKLB is holding up remarkably well"，赞 101 / 浏览 9,008 —— https://x.com/retail_mourinho/status/2122346114393289018 （11-16 10:08 ET）
  3. "Rocket Lab: Still A Dream Stock, Soon With Debt"（偏谨慎）—— https://x.com/SeekingAlpha/status/2121868308425449902 （11-15 02:30 ET）
  4. "$RKLB 62.01% below its all-time high"（列表帖）—— https://x.com/Mapago9/status/2122585528209936763 （11-17 02:00 ET）
  5. Stocktwits RKLB 40（Bearish）；Reddit 7 日 37 条，看多 62.2% —— https://stocktwits.com/symbol/RKLB ；https://stonkhub.io/stocks/RKLB （~02:44 ET）
- **关键价位（社媒提及）**：无（只有推广帖里的 $230 目标，已归入疑似操纵）
- **失效条件**：Neutron 测试负面消息导致集中看空；或提及量 ≥3x
- **未来 7 天事件**：没有确认的本公司事件（Neutron 一级贮箱测试据报道在 2027 年一季度，在 7 天之外）
- **数据缺口**：Stocktwits 标签与 X/Reddit 方向相反，原因无法从页面判断
- **警报级别**：🟢 绿

### 10. SPCX（SpaceX）

- **标的核实**：**SPCX = Space Exploration Technologies Corp.（SpaceX）A 类普通股**，2026-06-12 在 Nasdaq Global Select（同时在 Nasdaq Texas）上市，IPO 价 $135（https://ir.spacex.com/updates/releases-details/2026/Space-Exploration-Technologies-Corp--Announces-Pricing-of-Initial-Public-Offering/default.aspx ；https://www.nasdaqtrader.com/TraderNews.aspx?id=DTN2026-8 ）。**歧义说明**：①Nasdaq 公告称 SPCX 代码"此前曾用于另一证券"，2026-06-12 之前的 SPCX 历史数据和帖子与 SpaceX 无关；②瑞士、维也纳、华沙交易所及 Binance Futures 也有名为 SPCX 的挂牌或衍生品（Investing.com 列表），社媒上的"SPCX"可能混有这些。本报告按 Nasdaq: SPCX（SpaceX）处理。
- **数据时间**：X 2026-11-14 至 11-17 02:41 ET；Stocktwits/StonkHub ~02:44 ET
- **评分**：0　**上次评分**：无上次记录　**变化原因**：首份报告
- **置信度**：中　**适用期限**：短线
- **一句话结论**：13F"机构加仓"（英伟达持仓增至 1.305 亿股等）和星舰回收带来偏多叙事，抗跌被频繁提及，但没有过热。
- **提及量**：11/16 共 6,082 帖，7 日均 5,796 → **1.05x**
- **多空比**：X 11 多 : 7 空（有效 49，中性 31）；Reddit（7 日 106 条）看多 43.4% / 中性 23.6% / 看空 33.0%，WSB 参与人数 +23%；Stocktwits 57 "Bullish"，消息量 normal
- **主流叙事前 3**：①13F：英伟达、Appaloosa、贝莱德、ARK 加仓，Citadel、Thiel 减持；②星舰首次"捕获"上面级；③特斯拉-SpaceX 合并猜想（两边特别委员会在评估，没有达成协议）与 12/8 解禁
- **极端信号**：未见
- **疑似操纵**：未发现成批行为（个别"allin spcx, to da moon"属于个人情绪帖）
- **证据**：
  1. 英伟达 13F：持有 SpaceX 1.305 亿股（Q2 为 1.228 亿股），成为最大持仓，赞 31 / 浏览 3,612 —— https://x.com/SpaceInvestor_D/status/2122455204662571246 （11-16 17:22 ET；13F 为 9/30 快照）
  2. "Wall Street's biggest names are piling into SpaceX"，浏览 534 —— https://x.com/muskonomy/status/2122593077831331981 （11-17 02:30 ET）
  3. "Up to 797.6 million SpaceX shares… become free to sell on December 8"（解禁担忧）—— https://x.com/9to5investing/status/2122394267435860446 （11-16 13:20 ET）
  4. "Tesla and SpaceX have not merged. They haven't even agreed to merge"（辟谣类）—— https://x.com/FutureWireDaily/status/2122130291498045609 （11-15 19:51 ET）
  5. Stocktwits SPCX 57（Bullish）；Reddit 7 日 106 条 —— https://stocktwits.com/symbol/SPCX ；https://stonkhub.io/stocks/SPCX （~02:44 ET）
- **关键价位（社媒提及）**：100（https://x.com/D_4_Real/status/2122594347590021515 ）；135（IPO 价，多帖提及）
- **失效条件**：合并或解禁传闻引发一边倒情绪，提及量 ≥3x
- **未来 7 天事件**：没有确认的本公司事件。12/8 主要解禁（约 7.976 亿股）在 7 天之外，但已经是讨论焦点（https://orbiteconomics.com/spacex-lockup-schedule/ ）；合并公告据报道"可能在 12 月"，**未证实**
- **数据缺口**：代码有歧义，X 搜索可能混入其他"SPCX"挂牌的帖子
- **警报级别**：🟢 绿

---

### 韩国模块（适用 SNDK、MU、DRAM、SOXX、NVDA、MRVL）

- **数据时间**：韩国 11/16（周一）和 11/17（周二）收盘数据；X 韩语帖 2026-11-15 15:00 UTC 起
- **韩语 X 提及量**（`삼성전자 OR SK하이닉스 OR 하이닉스`）：11/16 UTC 日 853 帖，7 日均 552.7 → **1.54x**（未达 3x）
- **韩语 X 样本**：22 条（< 20 条有效方向帖，置信度低）。人工判读：偏悲观约 6 条，偏乐观 2 条（同一作者重复 1 条已合并），其余是行情播报。
- **散户（개인）与外资净买卖**（新闻有数据）：
  - 11/16 KOSPI：外资 −1 兆 3,838 亿韩元，机构 −4,512.6 亿，**个人 +1 兆 3,398.4 亿**（韩联社表 15:35 快照，https://www.yna.co.kr/view/AKR20261116128500008 ）。外资卖出第一是三星电子 6,193.6 亿，第二是 SK 海力士 2,241.8 亿（https://www.yna.co.kr/view/AKR20261116131200008?section=market-plus%2Fall ）。两只合计占外资净卖出约 60.9%（https://www.fnnews.com/news/202611161610416501 ）。
  - 11/17 KOSPI 收 4,968.48（−2.59%），2 月以来首次跌破 5000；个人 +4,218 亿，机构 +5,436 亿，外资 −1 兆 4,460 亿（首尔经济，https://www.sedaily.com/article/20115450 ，15:34）。
  - 11/17 个股（Alphapass 汇总 KRX 数据，二手）：三星电子 外资 −4,820 亿 / 机构 +1,785 亿 / **个人 +2,889 亿**；SK 海力士 外资 −4,588 亿（连续 4 日净卖出，20 日累计 −7 兆 5,505 亿）/ 机构 +1,551 亿 / **个人 −764 亿**（https://www.alphapass.kr/stock/005930/today ；https://www.alphapass.kr/stock/000660/today ）。注意：Alphapass 给出的 11/16 海力士外资数（−2,042 亿）与韩联社 15:30 快照（−2,241.8 亿）口径不同。
- **媒体口径**（韩文译为中文）：
  - 每日经济（11/16）："这周能不能打开局面"；NH 投资证券、Kiwoom 给出本周 KOSPI 区间 5200–6000 / 5200–5650；大信证券称"黄仁勋丑闻直接损害 AI 需求或供应合同的可能性有限"；新韩投资证券提醒 Anthropic IPO 可能分流外资 —— https://www.mk.co.kr/news/stock/12209596
  - 金融新闻（11/16）："'超级周'第一天外资卖了 1.4 兆，掉头的牌是什么？" —— https://www.fnnews.com/news/202611161610416501
  - 首尔经济"捡漏报告"："黄仁勋走了 GPU 也还是不够……对华规制反倒利好韩国存储" —— https://www.sedaily.com/article/20115192
  - 韩国经济、朝鲜商业：本次没有抓到 11/16 之后关于存储的专门报道，**无数据**
- **개미（韩国散户）情绪**（二手，来自新闻对讨论区的描述，非 Naver 直读）：OBC（11/06，在本窗口之前，作背景）报道三星、海力士"讨论区里有人称亏了一套公寓、没钱补仓、要删交易 App"（https://www.theonetv.kr/news/articleView.html?idxno=254691 ）；每日新闻（11/10）报道"三星跌破 19 万韩元，券商圈抄底论升温"（https://www.imaeil.com/page/view/2026111008353480750 ）。窗口内（11/16 之后）的直接描述：韩语 X 帖"以为到底了，结果地下室的门开了 🤯"（https://x.com/block_atom/status/2122495434643943738 ，11-16 20:02 ET）；"养老金比外资卖得还多……该死的养老金"（https://x.com/jonborica/status/2122497697194422634 ，11-16 20:10 ET，赞 13）。**Naver 讨论区本身无直接数据**。
- **出口数据**：11/1–10 半导体出口 166.32 亿美元，同比 +331.2%，D 램 66.7 亿美元（关税厅初值，经中央 Journal/MoneyToday 转述，11/11 发布）—— https://www.mt.co.kr/economy/2026/11/11/2026111108322848143 。注意：Newsis 标题写"同比 111.9%"，口径不同，未核清。
- **韩国情绪结论**：**悲观**。判断：外资连续大额抛售三星和海力士，KOSPI 跌破 5000，韩语社媒用"地下室""投매"等词；个人对三星持续逆势买入，但 11/17 转为净卖出海力士，抄底意愿出现分化。
- **与美国是否一致**：**方向一致（偏空）**，但韩国更悲观。美国端 SOXX、MU 偏空，NVDA 散户仍有抄底热情（Stocktwits 极度看多）；韩国端外资主导的抛售更集中。

---

### 自检

- [x] 10 个标的全覆盖，杠杆 ETF 未扫描、未评论；PEERS 未做
- [x] 每个标的包含：标的、数据时间、评分、上次评分/变化原因、置信度、适用期限、一句话结论、证据（≤5 条，带数值/链接/时间）、关键价位、失效条件、7 天事件、数据缺口、警报级别
- [x] 提及量（倍数）、多空比（含样本数）、主流叙事前 3、极端信号、疑似操纵（单列，不计入多空比）均已覆盖
- [x] 评分规则：没有标的同时满足"极端看多加提及量激增"或"极端看空加投降"，全部为 0；没有给出 ±2
- [x] 未写价格技术面、估值、期权策略、宏观指标（VIX、恐惧贪婪指数等出现在原帖里也没有引用）；社媒关键价位只按"社媒提及"列出
- [x] 传闻标注"未证实"；二手数据已注明
- [x] 所有数字来自本次抓取（X 连接器、网页），拿不到的写"无数据"
- [x] 未下单、未发帖/回复/点赞/关注、未给任何人发消息
- 已知局限：X 多空比是关键词规则分类；X 不支持 cashtag；Reddit 直连 403，用的是聚合站；Stocktwits 只有标签没有消息量数值；NAAIM 是二手转述

**实际扫描时间（美东）**：2026-11-17 02:40–02:50 ET（X 数据抓取 02:40–02:44 ET；网页与韩国数据 02:44–02:48 ET；报告写入 02:49 ET）
