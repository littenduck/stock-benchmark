/* Interface text and bilingual rendering shared by every page. Rules: docs/language.md. */
const UI_TEXT = {
  switch_language: { en:'Switch to Chinese', zh:'切换到英文' },
  loading_data: { en:'Loading data…', zh:'正在获取数据…' },
  strategy: { en:'Strategy', zh:'策略' },
  market: { en:'Market', zh:'市场指标' },
  symbols: { en:'Symbols', zh:'标的' },
  rule_catalog: { en:'Rule catalog', zh:'规则目录' },
  select_symbol: { en:'Select a symbol on the left to see its strategy tree', zh:'选择左侧的标的查看策略树' },
  switch_theme: { en:'Switch light or dark mode', zh:'切换浅色或深色模式' },
  pass: { en:'Pass', zh:'通过' }, fail: { en:'Fail', zh:'未通过' }, veto: { en:'Veto', zh:'否决' },
  unknown: { en:'Unknown', zh:'未知' }, not_applicable: { en:'N/A', zh:'不适用' },
  unavailable: { en:'Unavailable', zh:'获取失败' },
  symbol_summary: { en:'{symbol}, {status}, score {score}', zh:'{symbol}，{status}，分数 {score}' },
  insufficient_data: { en:'Insufficient data', zh:'数据不足' },
  disconnected: { en:'Disconnected, retrying', zh:'连接断开，正在重试' },
  market_closed: { en:'Market closed · Last update {time}', zh:'休市 · 最后更新 {time}' },
  data_stale: { en:'Data is stale · Last update {time}', zh:'数据已过期 · 最后更新 {time}' },
  market_open: { en:'Market open · Updated {age}', zh:'开盘中 · 更新于 {age}' },
  generated_at: { en:'Data generated at {time}', zh:'数据生成于 {time}' },
  just_now: { en:'just now', zh:'刚刚' },
  minutes_ago: { en:'{count} min ago', zh:'{count} 分钟前' },
  hours_ago: { en:'{count} h ago', zh:'{count} 小时前' },
  yes: { en:'Yes', zh:'是' }, no: { en:'No', zh:'否' },
  back_to_list: { en:'↑ List', zh:'↑ 列表' },
  verdict: { en:'Verdict', zh:'结论' }, score: { en:'Score', zh:'分数' },
  missing_weight: { en:'Missing-data weight {percent}% (unknown rules are left out of the score)', zh:'数据缺失权重 {percent}%（未知规则不计入分数）' },
  about_strategy: { en:'About {name}', zh:'{name} 策略说明' },
  close: { en:'Close', zh:'关闭说明' },
  source: { en:'Source: {source}', zh:'来源：{source}' },
  see_all_rules: { en:'See all rules and how IDs work →', zh:'查看全部规则和编号说明 →' },
  open_strategy: { en:'Strategy page →', zh:'策略页面 →' },
  catalog_link: { en:'Strategies, rules, indicators', zh:'策略、规则、指标' },
  best_window: { en:'Expiration {label} days (best) · Gate score {score}', zh:'到期窗口 {label} 天（最佳） · 本层分数 {score}' },
  alternative_window: { en:'Alternative expiration {label} days · Gate score {score}', zh:'备选到期窗口 {label} 天 · 本层分数 {score}' },
  rule_details: { en:'Show all fields of {id}', zh:'查看 {id} 的全部字段' },
  open_rule: { en:'Open {id} in the rule catalog', zh:'在规则目录中查看 {id}' },
  dashboard_title: { en:'Stock Benchmark', zh:'Stock Benchmark' },
  rules_title: { en:'Rules · Stock Benchmark', zh:'规则 · Stock Benchmark' },
  back_to_dashboard: { en:'← Back to dashboard', zh:'← 返回看板' },
  rule_summary: { en:'{total} rules · {built} built · {backtest} can be backtested · {used} used by strategies', zh:'共 {total} 条规则 · 已接入 {built} 条 · 可回测 {backtest} 条 · 被策略使用 {used} 条' },
  backtest_rules: { en:'Can be backtested', zh:'可以回测的规则' },
  backtest_explanation: { en:'Backtest: a rule can be backtested when free historical data can rebuild what it would have said on a past date, using only what was known then. How far back differs by rule; rules that need your own answer or your account cannot be backtested.',
    zh:'回测：如果免费的历史数据能还原这条规则在过去某一天、只用当时已知信息会给出的结果，这条规则就可以回测。能追溯多久因规则而异；需要你本人回答或你的账户数据的规则不能回测。' },
  id_explanation: { en:'How IDs work: R- plus a three-letter category and two digits, such as R-TRD-05. Categories run from macro down to detail. Inside a category the numbers run 01, 02, 03 ... in the order shown, grouped into topics. One ID means the same rule in every strategy. A rule only says pass, fail or unknown; each strategy gives it its own weight.',
    zh:'编号规则：R- 加三个字母的分类和两位数字，如 R-TRD-05。分类从宏观排到细节。分类内的编号按显示顺序 01、02、03……依次排下去，并按主题分组。同一个编号在所有策略里是同一条规则。一条规则只回答通过、不通过或未知；权重由每个策略自己决定。' },
  gap_explanation: { en:'A measure with several lines, such as the VIX, is split into one rule per line (VIX at least 12, at least 15, below 25 ...). A strategy lists the lines it wants, each with its own weight, so crossing one more line adds weight. The other lines of a measure sit right under its main rule, indented, and share the indicator text.',
    zh:'有多条分界线的指标（如 VIX）被拆成一线一条规则（VIX 不低于 12、不低于 15、低于 25 ……）。策略自己挑要用的线，并给每条线单独的权重，所以越过的线越多，得到的权重越多。同一指标的其他线紧挨在主规则下面，缩进显示，共用同一份指标说明。' },
  status_label: { en:'Status', zh:'状态' },
  show: { en:'Show', zh:'显示' },
  indicator_lines: { en:'Lines of {id}', zh:'{id} 的各档' },
  all_rules: { en:'All rules', zh:'全部规则' },
  used_rules: { en:'Used by a strategy', zh:'已被策略使用的规则' },
  built_rules: { en:'Built (the dashboard computes them)', zh:'已接入（看板在计算）的规则' },
  not_used: { en:'Not used', zh:'未被使用' },
  loading_rules: { en:'Loading rules…', zh:'正在读取规则…' },
  rules_failed: { en:'Could not load rules. Check that the server is running.', zh:'读取规则失败，请确认服务正在运行。' },
  nav_dashboard: { en:'Dashboard', zh:'看板' }, nav_strategies: { en:'Strategies', zh:'策略' }, nav_rules: { en:'Rules', zh:'规则' }, nav_indicators: { en:'Indicators', zh:'指标' },
  strategies_title: { en:'Strategies · Stock Benchmark', zh:'策略 · Stock Benchmark' }, indicators_title: { en:'Indicators · Stock Benchmark', zh:'指标 · Stock Benchmark' },
  strategy_title: { en:'Strategy · Stock Benchmark', zh:'策略 · Stock Benchmark' },
  strategies_heading: { en:'Strategies', zh:'策略' }, indicators_heading: { en:'Indicator catalog', zh:'指标目录' },
  strategy_summary: { en:'{count} strategies', zh:'共 {count} 个策略' },
  strategy_facts: { en:'{gates} gates · {rules} rules · {veto} veto', zh:'{gates} 个关卡 · {rules} 条规则 · {veto} 条否决' },
  indicator_summary: { en:'{total} indicators · {built} built · {backtest} can be backtested · {bar} on the market bar', zh:'共 {total} 个指标 · 已接入 {built} 个 · 可回测 {backtest} 个 · 大盘栏 {bar} 个' },
  all_indicators: { en:'All indicators', zh:'全部指标' }, built_indicators: { en:'Built (the dashboard computes them)', zh:'已接入（看板在计算）的指标' },
  backtest_indicators: { en:'Can be backtested', zh:'可以回测的指标' },
  loading_indicators: { en:'Loading indicators…', zh:'正在读取指标…' }, indicators_failed: { en:'Could not load indicators. Check that the server is running.', zh:'读取指标失败，请确认服务正在运行。' },
  loading_strategies: { en:'Loading strategies…', zh:'正在读取策略…' }, strategies_failed: { en:'Could not load strategies. Check that the server is running.', zh:'读取策略失败，请确认服务正在运行。' },
  how_to_read: { en:'How to read this page', zh:'怎么读这个页面' }, all_strategies: { en:'← All strategies', zh:'← 全部策略' },
  open_in_dashboard: { en:'Open in the dashboard →', zh:'在看板中打开 →' }, source_label: { en:'Source', zh:'来源' },
  weight: { en:'W{weight}', zh:'权重 {weight}' }, veto_flag: { en:'Veto', zh:'否决' }, not_built: { en:'Not built', zh:'未接入' },
  scoring_title: { en:'How the score works', zh:'分数怎么算' },
  scoring_text: { en:'Each rule that passes adds its weight; each rule that fails adds nothing; unknown rules are left out. The score is the passed weight as a share of the weight of the rules that passed or failed. A veto rule that fails makes the whole result a fail, whatever the score. When more than {ratio}% of the weight is unknown, the dashboard greys the score as data insufficient. The gates are checked in order; the contract gate is checked once per expiration window and the best window wins.',
    zh:'通过的规则加上它的权重，不通过的规则不加分，未知的规则不计入。分数等于通过的权重占（通过加不通过）规则总权重的比例。一票否决的规则不通过时，不管分数多少，结果都是不通过。未知权重超过 {ratio}% 时，看板把分数置灰，提示数据不足。关卡按顺序检查；合约关卡对每个到期窗口各检查一次，取最好的窗口。' },
  used_by_label: { en:'Used by', zh:'使用它的策略' }, tested_by_label: { en:'Tested by', zh:'测试它的规则' }, on_market_bar: { en:'on the market bar', zh:'在大盘栏显示' },
  line_label: { en:'Line', zh:'分界线' },
  also_known_as: { en:'Older ids', zh:'旧编号' },
  built: { en:'Built', zh:'已接入' },
  built_explanation: { en:'the dashboard already computes it', zh:'看板已经在计算' },
  todo: { en:'To do', zh:'待实现' },
  todo_explanation: { en:'the data is free and easy to get, the code is not written yet', zh:'数据免费、容易取得，代码还没写' },
  no_data: { en:'No data', zh:'暂无数据' },
  no_data_explanation: { en:'no stable free data, or a manual rule; it shows unknown and is left out of the score', zh:'没有稳定的免费数据，或是手填规则；显示未知，不计入分数' },
  api_fetch: { en:'auto fetch', zh:'自动抓取' },
  scrape: { en:'scrape', zh:'复杂抓取' },
  computed: { en:'computed', zh:'计算获得' },
  ai_search: { en:'AI search', zh:'AI 采集' },
  manual: { en:'manual', zh:'手填' },
  terminal_title: { en:'Terminal · Stock Benchmark', zh:'终端 · Stock Benchmark' },
  terminal_unavailable: { en:'No price data for this symbol right now.', zh:'暂时取不到这个标的的价格数据。' },
  terminal_unknown: { en:'This symbol is not in the snapshot.', zh:'这个标的不在快照里。' },
  pipeline: { en:'Pipeline', zh:'流水线' },
  pipeline_scout: { en:'Scout', zh:'Scout' },
  pipeline_filter: { en:'Filter', zh:'Filter' },
  pipeline_analyst: { en:'Analyst', zh:'Analyst' },
  pipeline_executor: { en:'Executor', zh:'Executor' },
  pipeline_logger: { en:'Logger', zh:'Logger' },
  scout_value: { en:'{count} daily bars to {date}', zh:'{count} 根日线，截至 {date}' },
  filter_above: { en:'Above SMA200', zh:'在 SMA200 上方' },
  filter_below: { en:'Below SMA200', zh:'在 SMA200 下方' },
  filter_none: { en:'Not enough history', zh:'历史不足' },
  analyst_value: { en:'Score {score}', zh:'分数 {score}' },
  executor_buy: { en:'Buy', zh:'可以' },
  executor_wait: { en:'Wait', zh:'观望' },
  executor_no: { en:'No', zh:'不行' },
  logger_value: { en:'{count} recent events', zh:'{count} 条最近事件' },
  range_3m: { en:'3 months', zh:'3 个月' },
  range_6m: { en:'6 months', zh:'6 个月' },
  range_1y: { en:'1 year', zh:'1 年' },
  toggle_smc: { en:'SMC', zh:'SMC 结构' },
  toggle_bollinger: { en:'Bollinger', zh:'布林带' },
  toggle_sma: { en:'SMA', zh:'均线' },
  toggle_rsi: { en:'RSI', zh:'RSI' },
  toggle_macd: { en:'MACD', zh:'MACD' },
  toggle_volume: { en:'Volume', zh:'成交量' },
  chart_price: { en:'Price', zh:'价格' },
  chart_rsi: { en:'RSI(14)', zh:'RSI(14)' },
  chart_macd: { en:'MACD (12, 26, 9)', zh:'MACD（12, 26, 9）' },
  chart_volume: { en:'Volume', zh:'成交量' },
  ohlc_line: { en:'{date}  O {open}  H {high}  L {low}  C {close}  V {volume}', zh:'{date}  开 {open}  高 {high}  低 {low}  收 {close}  量 {volume}' },
  light_green: { en:'Green', zh:'绿' },
  light_yellow: { en:'Yellow', zh:'黄' },
  light_red: { en:'Red', zh:'红' },
  light_grey: { en:'Loss', zh:'亏损' },
  light_white: { en:'No single match', zh:'无单一对应' },
  light_none: { en:'Not available', zh:'暂无数据' },
  light_counts: { en:'{green} green · {yellow} yellow · {red} red', zh:'绿 {green} · 黄 {yellow} · 红 {red}' },
  counted_note: { en:'Counted in the tally: PE, RSI, MACD, %B, SMA20, SMA50, volume.', zh:'计入汇总：PE、RSI、MACD、%B、SMA20、SMA50、量能。' },
  dip_breakdown: { en:'Score breakdown', zh:'分数拆解' },
  strategies_heading: { en:'Strategies', zh:'策略' },
  events_heading: { en:'Recent events', zh:'最近事件' },
  no_events: { en:'No signal changes in the last year.', zh:'过去一年没有信号变化。' },
  not_applicable_short: { en:'N/A', zh:'不适用' },
  score_points: { en:'{points} pts', zh:'{points} 分' },
  change_up: { en:'up {value}%', zh:'涨 {value}%' },
  change_down: { en:'down {value}%', zh:'跌 {value}%' },
  price_as_of: { en:'Last bar {date}', zh:'最后一根 K 线 {date}' },
  generated_label: { en:'Snapshot {time}', zh:'快照 {time}' },
};
const LANGUAGE_STORAGE_KEY = 'stock-benchmark-language';
let activeLanguage = 'en', hasStoredLanguageChoice = false;

const languageEscape = text => String(text ?? '').replace(/[&<>"]/g, character => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;' })[character]);
const languageFill = (localizedText, values = {}) => Object.fromEntries(['en', 'zh'].map(code =>
  [code, localizedText[code].replace(/\{(\w+)\}/g, (match, name) => values[name] ?? match)]));
const languageLocalize = (key, values) => languageFill(UI_TEXT[key], values);
const languageText = (key, values) => languageLocalize(key, values)[activeLanguage];
const languageGetActive = () => activeLanguage;

function languageInitialize(defaultLanguage) {
  let storedChoice = null;
  try { storedChoice = localStorage.getItem(LANGUAGE_STORAGE_KEY); } catch (error) { /* storage blocked: use the default */ }
  hasStoredLanguageChoice = storedChoice === 'en' || storedChoice === 'zh';
  activeLanguage = hasStoredLanguageChoice ? storedChoice : (defaultLanguage === 'zh' ? 'zh' : 'en');
  languageApplyDocument();
}
function languageApplyServerDefault(defaultLanguage, onChange) {
  if (!hasStoredLanguageChoice && (defaultLanguage === 'zh' ? 'zh' : 'en') !== activeLanguage) { activeLanguage = defaultLanguage; languageApplyDocument(); onChange(); }
}
function languageApply(languageCode, onChange) {
  activeLanguage = languageCode; hasStoredLanguageChoice = true;
  try { localStorage.setItem(LANGUAGE_STORAGE_KEY, languageCode); } catch (error) { /* storage blocked: lasts this visit only */ }
  languageApplyDocument();
  onChange();
}
function languageApplyDocument() {
  document.documentElement.lang = activeLanguage === 'zh' ? 'zh-Hans' : 'en';
  if (document.body.dataset.titleKey) document.title = languageText(document.body.dataset.titleKey);
  const languageButton = document.getElementById('language-button');
  if (languageButton) { languageButton.setAttribute('aria-label', languageText('switch_language')); languageButton.title = languageText('switch_language'); }
}
/* Each language stands alone: Chinese mode shows only the Chinese text, English mode only the English. Names (rule_name, indicator_name) stay English. */
/* A rule_name or indicator_name, escaped, with a place to break after each underscore so a long name wraps instead of overflowing. */
function languageRenderName(name) {
  return languageEscape(name).replace(/_/g, '_<wbr>');
}
function languageRenderText(localizedText) {
  return languageEscape(localizedText[activeLanguage]);
}
function languageRenderParagraphs(localizedText) {
  const split = text => text.split(/\n\s*\n/).map(paragraph => paragraph.trim()).filter(Boolean);
  return split(localizedText[activeLanguage]).map(paragraph => `<p>${languageEscape(paragraph)}</p>`).join('');
}
function languageBindSwitch(onChange) {
  document.getElementById('language-button').onclick = () => languageApply(activeLanguage === 'zh' ? 'en' : 'zh', onChange);
  languageApplyDocument();
}
