/* Symbol terminal: one symbol's chart blocks, pipeline, strategy cards and recent events. Data: /api/v1/terminal/{symbol}.
   Charts are hand-drawn SVG (no chart library). Every block shares one time range and one hover index, so they stay in step. */
const TERMINAL_RANGE_BAR_COUNT = { '3m': 63, '6m': 126, '1y': 0 };
const TERMINAL_PAD = { left: 8, right: 56, top: 12, bottom: 18 };
const TERMINAL_FVG_RECENT_BARS = 60;  // unfilled gaps this recent are drawn; older or filled ones are left out
const TERMINAL_OB_RECENT_COUNT = 4;  // order blocks of the last few breaks
const TERMINAL_STRUCTURE_RECENT_COUNT = 6;  // BOS and CHoCH lines: only the latest few, or the chart is unreadable
const TERMINAL_SWEEP_RECENT_COUNT = 10;
const TERMINAL_HEIGHT = { price: 340, volume: 110, rsi: 130, macd: 150 };
const TERMINAL_STYLE = {
  up: 'fill:var(--positive)', down: 'fill:var(--negative)', text: 'font-size:12px;fill:var(--text-secondary)',
  grid: 'stroke:var(--separator);stroke-width:1', guide: 'stroke:var(--text-muted);stroke-width:1;stroke-dasharray:3 3',
};

let terminalPayload = null, terminalFailed = false, terminalLoadId = 0, terminalFrame = 0, terminalSideCardList = [];
let terminalRange = '6m', terminalHover = null;
const terminalToggle = { smc: true, bollinger: true, sma: true, volume: true, rsi: true, macd: true };
const terminalDisplayMap = {};

const terminalFinite = value => value !== null && value !== undefined && Number.isFinite(value);
const terminalFixed = (value, digits) => terminalFinite(value) ? Number(value).toFixed(digits) : languageText('not_applicable_short');
const terminalLocal = (localized) => localized[languageGetActive()];

function terminalSymbolFromPath() {
  const match = location.pathname.match(/^\/terminal\/([^/]+)$/);
  return match ? decodeURIComponent(match[1]) : '';
}

function terminalViewFor(count) {
  const wanted = TERMINAL_RANGE_BAR_COUNT[terminalRange];
  const start = wanted ? Math.max(0, count - wanted) : 0;
  return { start, end: count };
}

function terminalScaleX(view, width) {
  const plotWidth = Math.max(1, width - TERMINAL_PAD.left - TERMINAL_PAD.right);
  const step = plotWidth / (view.end - view.start);
  return { step, plotWidth, x: index => TERMINAL_PAD.left + (index - view.start + 0.5) * step };
}

function terminalScaleY(values, height) {
  const finite = values.filter(terminalFinite);
  let low = finite.length ? Math.min(...finite) : 0, high = finite.length ? Math.max(...finite) : 1;
  const span = high - low || 1;
  low -= span * 0.04; high += span * 0.04;
  const top = TERMINAL_PAD.top, bottom = height - TERMINAL_PAD.bottom;
  return { low, high, y: value => top + (high - value) / (high - low) * (bottom - top) };
}

function terminalLine(x1, y1, x2, y2, style) {
  return `<line x1="${x1.toFixed(1)}" y1="${y1.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}" style="${style}"/>`;
}

function terminalPolyline(indexList, valueList, x, y, style) {
  let d = '', pen = false;
  for (const index of indexList) {
    const value = valueList[index];
    if (!terminalFinite(value)) { pen = false; continue; }
    d += `${pen ? 'L' : 'M'}${x(index).toFixed(1)} ${y(value).toFixed(1)}`;
    pen = true;
  }
  return d ? `<path d="${d}" style="fill:none;${style}"/>` : '';
}

function terminalLabel(x, y, text, anchor = 'start') {
  return `<text x="${x.toFixed(1)}" y="${y.toFixed(1)}" text-anchor="${anchor}" style="${TERMINAL_STYLE.text}">${languageEscape(text)}</text>`;
}

function terminalRange_indexList(view) {
  const list = [];
  for (let index = view.start; index < view.end; index++) list.push(index);
  return list;
}

function terminalRightAxis(scale, width, height, ticks, format) {
  return ticks.map(tick => terminalLabel(width - TERMINAL_PAD.right + 6, scale.y(tick) + 4, format(tick))).join('');
}

function terminalDrawPrice(width, view) {
  const { ohlcv, indicators, smc } = terminalPayload;
  const height = TERMINAL_HEIGHT.price;
  const bandValues = terminalToggle.bollinger ? [...indicators.bollinger_upper.slice(view.start, view.end), ...indicators.bollinger_lower.slice(view.start, view.end)] : [];
  const scale = terminalScaleY([...ohlcv.high.slice(view.start, view.end), ...ohlcv.low.slice(view.start, view.end), ...bandValues], height);
  const axis = terminalScaleX(view, width);
  const x = axis.x, y = scale.y, indexList = terminalRange_indexList(view);
  let svg = '';
  const candle = Math.max(1, axis.step * 0.7);
  if (terminalToggle.bollinger) {
    const upper = indexList.filter(index => terminalFinite(indicators.bollinger_upper[index]));
    const lower = upper.slice().reverse().filter(index => terminalFinite(indicators.bollinger_lower[index]));
    if (upper.length && lower.length) {
      const band = upper.map(index => `${x(index).toFixed(1)} ${y(indicators.bollinger_upper[index]).toFixed(1)}`)
        .concat(lower.map(index => `${x(index).toFixed(1)} ${y(indicators.bollinger_lower[index]).toFixed(1)}`));
      svg += `<path d="M${band.join('L')}Z" style="fill:var(--fill);stroke:none"/>`;
    }
    svg += terminalPolyline(indexList, indicators.bollinger_upper, x, y, 'stroke:var(--text-muted);stroke-width:1;stroke-dasharray:3 3');
    svg += terminalPolyline(indexList, indicators.bollinger_lower, x, y, 'stroke:var(--text-muted);stroke-width:1;stroke-dasharray:3 3');
    svg += terminalPolyline(indexList, indicators.bollinger_middle, x, y, 'stroke:var(--text-muted);stroke-width:1');
  }
  if (terminalToggle.smc) svg += terminalDrawSmc(smc, x, y, view, scale, axis);
  for (const index of indexList) {
    const open = ohlcv.open[index], close = ohlcv.close[index], up = close >= open;
    const color = up ? TERMINAL_STYLE.up : TERMINAL_STYLE.down;
    svg += terminalLine(x(index), y(ohlcv.high[index]), x(index), y(ohlcv.low[index]), color.replace('fill', 'stroke') + ';stroke-width:1');
    const top = y(Math.max(open, close)), bodyHeight = Math.max(1, Math.abs(y(open) - y(close)));
    svg += `<rect x="${(x(index) - candle / 2).toFixed(1)}" y="${top.toFixed(1)}" width="${candle.toFixed(1)}" height="${bodyHeight.toFixed(1)}" style="${color}"/>`;
  }
  if (terminalToggle.sma) {
    svg += terminalPolyline(indexList, indicators.sma20, x, y, 'stroke:var(--accent);stroke-width:1.2');
    svg += terminalPolyline(indexList, indicators.sma50, x, y, 'stroke:var(--caution);stroke-width:1.2');
    svg += terminalPolyline(indexList, indicators.sma200, x, y, 'stroke:var(--text);stroke-width:1.2');
  }
  const ticks = [scale.low + (scale.high - scale.low) * 0.1, (scale.low + scale.high) / 2, scale.high - (scale.high - scale.low) * 0.1];
  svg += terminalRightAxis(scale, width, height, ticks, tick => tick.toFixed(2));
  return terminalWrap(width, height, svg);
}

function terminalDrawSmc(smc, x, y, view, scale, axis) {
  const { ohlcv } = terminalPayload;
  const lastIndex = view.end - 1;
  let svg = '';
  for (const gap of smc.fair_value_gaps) {
    if (terminalFinite(gap.mitigated_index) || gap.index < lastIndex - TERMINAL_FVG_RECENT_BARS || gap.start_index > lastIndex) continue;
    const endIndex = terminalFinite(gap.mitigated_index) ? gap.mitigated_index : lastIndex;
    const color = gap.direction === 'up' ? 'var(--positive)' : 'var(--negative)';
    svg += `<rect x="${x(gap.start_index).toFixed(1)}" y="${y(gap.high).toFixed(1)}" width="${Math.max(2, x(endIndex) - x(gap.start_index)).toFixed(1)}" height="${Math.max(1, y(gap.low) - y(gap.high)).toFixed(1)}" style="fill:${color};fill-opacity:0.14;stroke:${color};stroke-opacity:0.5;stroke-dasharray:2 2"/>`;
    svg += terminalLabel(x(gap.start_index), y(gap.high) - 3, 'FVG');
  }
  for (const block of smc.events.slice(-TERMINAL_OB_RECENT_COUNT).map(event => event.order_block).filter(Boolean)) {
    if (block.index < view.start || block.index > lastIndex) continue;
    svg += `<rect x="${x(block.index).toFixed(1)}" y="${y(block.high).toFixed(1)}" width="${Math.max(3, x(lastIndex) - x(block.index)).toFixed(1)}" height="${Math.max(1, y(block.low) - y(block.high)).toFixed(1)}" style="fill:var(--accent);fill-opacity:0.12;stroke:var(--accent);stroke-opacity:0.6"/>`;
    svg += terminalLabel(x(block.index) + 3, y(block.high) + 11, 'OB');
  }
  for (const level of smc.equal_levels) {
    if (level.second_index < view.start || level.first_index > lastIndex) continue;
    svg += terminalLine(x(level.first_index), y(level.price), x(level.second_index), y(level.price), 'stroke:var(--text-secondary);stroke-width:1;stroke-dasharray:4 3');
    svg += terminalLabel(x(level.second_index) + 3, y(level.price) - 3, level.kind);
  }
  for (const event of smc.events.slice(-TERMINAL_STRUCTURE_RECENT_COUNT)) {
    if (event.index < view.start) continue;
    const from = Math.max(event.level_index, view.start), level = y(event.price);
    svg += terminalLine(x(from), level, x(event.index), level, 'stroke:var(--text);stroke-width:1');
    svg += terminalLabel((x(from) + x(event.index)) / 2, level - 4, event.kind, 'middle');
  }
  for (const sweep of smc.sweeps.slice(-TERMINAL_SWEEP_RECENT_COUNT)) {
    if (sweep.index < view.start || sweep.index > lastIndex) continue;
    const anchor = sweep.side === 'high' ? ohlcv.high[sweep.index] : ohlcv.low[sweep.index];
    const cy = sweep.side === 'high' ? y(anchor) - 7 : y(anchor) + 7;
    svg += `<circle cx="${x(sweep.index).toFixed(1)}" cy="${cy.toFixed(1)}" r="3" style="fill:var(--text)"/>`;
  }
  return svg;
}

function terminalDrawVolume(width, view) {
  const { ohlcv, indicators } = terminalPayload;
  const height = TERMINAL_HEIGHT.volume, indexList = terminalRange_indexList(view);
  const scale = terminalScaleY([0, ...ohlcv.volume.slice(view.start, view.end), ...indicators.volume_average.slice(view.start, view.end)], height);
  const axis = terminalScaleX(view, width), x = axis.x;
  let svg = '';
  for (const index of indexList) {
    const up = ohlcv.close[index] >= ohlcv.open[index];
    const top = scale.y(ohlcv.volume[index]), base = scale.y(0);
    svg += `<rect x="${(x(index) - axis.step * 0.35).toFixed(1)}" y="${top.toFixed(1)}" width="${Math.max(1, axis.step * 0.7).toFixed(1)}" height="${Math.max(0, base - top).toFixed(1)}" style="${up ? TERMINAL_STYLE.up : TERMINAL_STYLE.down};fill-opacity:0.6"/>`;
  }
  svg += terminalPolyline(indexList, indicators.volume_average, x, scale.y, 'stroke:var(--text-secondary);stroke-width:1;stroke-dasharray:3 3');
  return terminalWrap(width, height, svg);
}

function terminalDrawRsi(width, view) {
  const { indicators } = terminalPayload;
  const height = TERMINAL_HEIGHT.rsi, indexList = terminalRange_indexList(view);
  const scale = { y: value => TERMINAL_PAD.top + (100 - value) / 100 * (height - TERMINAL_PAD.top - TERMINAL_PAD.bottom) };
  const axis = terminalScaleX(view, width), x = axis.x;
  let svg = terminalLine(TERMINAL_PAD.left, scale.y(70), width - TERMINAL_PAD.right, scale.y(70), TERMINAL_STYLE.guide)
    + terminalLine(TERMINAL_PAD.left, scale.y(30), width - TERMINAL_PAD.right, scale.y(30), TERMINAL_STYLE.guide);
  svg += terminalPolyline(indexList, indicators.rsi, x, scale.y, 'stroke:var(--accent);stroke-width:1.5');
  svg += terminalLabel(width - TERMINAL_PAD.right + 6, scale.y(70) + 4, '70') + terminalLabel(width - TERMINAL_PAD.right + 6, scale.y(30) + 4, '30');
  return terminalWrap(width, height, svg);
}

function terminalDrawMacd(width, view) {
  const { indicators } = terminalPayload;
  const height = TERMINAL_HEIGHT.macd, indexList = terminalRange_indexList(view);
  const scale = terminalScaleY([0, ...indicators.macd.slice(view.start, view.end), ...indicators.macd_signal.slice(view.start, view.end),
    ...indicators.macd_histogram.slice(view.start, view.end)], height);
  const axis = terminalScaleX(view, width), x = axis.x, zero = scale.y(0);
  let svg = terminalLine(TERMINAL_PAD.left, zero, width - TERMINAL_PAD.right, zero, TERMINAL_STYLE.grid);
  for (const index of indexList) {
    const value = indicators.macd_histogram[index];
    if (!terminalFinite(value)) continue;
    const top = Math.min(scale.y(value), zero), bar = Math.max(1, Math.abs(scale.y(value) - zero));
    svg += `<rect x="${(x(index) - axis.step * 0.35).toFixed(1)}" y="${top.toFixed(1)}" width="${Math.max(1, axis.step * 0.7).toFixed(1)}" height="${bar.toFixed(1)}" style="${value >= 0 ? TERMINAL_STYLE.up : TERMINAL_STYLE.down};fill-opacity:0.6"/>`;
  }
  svg += terminalPolyline(indexList, indicators.macd, x, scale.y, 'stroke:var(--text);stroke-width:1.2');
  svg += terminalPolyline(indexList, indicators.macd_signal, x, scale.y, 'stroke:var(--accent);stroke-width:1.2');
  return terminalWrap(width, height, svg);
}

function terminalWrap(width, height, body) {
  return `<svg viewBox="0 0 ${width} ${height}" width="${width}" height="${height}" role="img" aria-hidden="true">${body}</svg>`;
}

function terminalDrawAll() {
  if (!terminalPayload) return;
  const view = terminalViewFor(terminalPayload.ohlcv.close.length);
  const hosts = { price: 'price', volume: 'volume', rsi: 'rsi', macd: 'macd' };
  for (const key of Object.keys(hosts)) {
    const host = document.querySelector(`[data-chart="${key}"]`);
    if (!host) continue;
    const width = Math.max(280, host.clientWidth || 600);
    host.innerHTML = { price: terminalDrawPrice, volume: terminalDrawVolume, rsi: terminalDrawRsi, macd: terminalDrawMacd }[key](width, view);
    host.dataset.width = String(width);
  }
  terminalUpdateReadout();
}

function terminalIndexFromEvent(event, host) {
  const view = terminalViewFor(terminalPayload.ohlcv.close.length);
  const width = Number(host.dataset.width) || host.clientWidth;
  const plotWidth = Math.max(1, width - TERMINAL_PAD.left - TERMINAL_PAD.right);
  const fraction = (event.clientX - host.getBoundingClientRect().left - TERMINAL_PAD.left) / plotWidth;
  const index = view.start + Math.floor(fraction * (view.end - view.start));
  return Math.min(view.end - 1, Math.max(view.start, index));
}

function terminalUpdateReadout() {
  const readout = document.getElementById('price-readout');
  if (!readout || !terminalPayload) return;
  const { ohlcv, dates } = terminalPayload;
  const index = terminalHover === null ? ohlcv.close.length - 1 : terminalHover;
  readout.textContent = languageText('ohlc_line', {
    date: dates[index], open: ohlcv.open[index].toFixed(2), high: ohlcv.high[index].toFixed(2),
    low: ohlcv.low[index].toFixed(2), close: ohlcv.close[index].toFixed(2), volume: Math.round(ohlcv.volume[index]).toLocaleString('en-US'),
  });
}

const TERMINAL_LIGHT_KEY = { green:'light_green', yellow:'light_yellow', red:'light_red', grey:'light_grey', white:'light_white' };
const terminalLightWord = light => languageText(TERMINAL_LIGHT_KEY[light] || 'light_none');
const terminalLightDot = light => `<span class="light ${light || ''}" aria-hidden="true"></span>`;
const terminalVerdictWord = verdict => languageText({ buy:'executor_buy', wait:'executor_wait', no:'executor_no' }[verdict]);
const terminalVerdictColor = verdict => ({ buy:'positive', wait:'caution', no:'negative' }[verdict] || '');
const terminalPassColor = isPass => isPass === true ? 'positive' : isPass === false ? 'negative' : 'muted';

function terminalRenderPipeline(pipeline) {
  const filterWord = { green:'filter_above', red:'filter_below' }[pipeline.filter.light];
  return [
    ['pipeline_scout', languageText('scout_value', { count: pipeline.scout.bars, date: pipeline.scout.as_of })],
    ['pipeline_filter', filterWord ? languageText(filterWord) : languageText('filter_none')],
    ['pipeline_analyst', languageText('analyst_value', { score: pipeline.analyst.score })],
    ['pipeline_executor', terminalVerdictWord(pipeline.executor.verdict)],
    ['pipeline_logger', languageText('logger_value', { count: pipeline.logger.events })],
  ].map(([key, text]) => `<div class="box"><small>${languageEscape(languageText(key))}</small><p>${languageEscape(text)}</p></div>`).join('');
}

function terminalRenderDipCard(card) {
  const rows = card.explanation_list.map(item => `<div>
      <small>${languageEscape(item.name)}</small>
      <small>${terminalLightDot(item.light)}${languageEscape(terminalLightWord(item.light))}</small>
      <small>${languageEscape(item.value)}${item.points === null ? '' : ' · ' + languageEscape(languageText('score_points', { points: item.points }))}<br>${languageEscape(terminalLocal(item.text))}</small>
    </div>`).join('');
  const counts = languageText('light_counts', { green: card.counts.green, yellow: card.counts.yellow, red: card.counts.red });
  return `<div class="box">
      <h3>${languageEscape(terminalLocal(card.display_name))}</h3>
      <h2 class="${terminalVerdictColor(card.verdict)}">${card.score_percent} · ${languageEscape(terminalVerdictWord(card.verdict))}</h2>
      <small>${languageEscape(terminalLocal(card.text))}</small>
      <small>${languageEscape(counts)}</small>
      <small>${languageEscape(languageText('counted_note'))}</small>
      <p>${languageEscape(languageText('dip_breakdown'))}</p>
      <div class="breakdown">${rows}</div>
    </div>`;
}

function terminalRenderStrategyCard(card) {
  if (card.strategy_id === 'dip_buy') return terminalRenderDipCard(card);
  const score = card.not_applicable ? languageText('not_applicable_short') : terminalFixed(card.score_percent, 1);
  return `<div class="box">
      <h3>${languageEscape(terminalLocal(card.display_name))}</h3>
      <h2 class="${terminalPassColor(card.is_pass)}">${languageEscape(score)}</h2>
      <small>${languageEscape(terminalLocal(card.text))}</small>
    </div>`;
}

function terminalRenderEvents(eventList) {
  if (!eventList.length) return `<small>${languageEscape(languageText('no_events'))}</small>`;
  return `<div class="event-list">${eventList.map(event => `<div><small>${languageEscape(event.date)}</small>
      <span class="${event.tone === 'positive' ? 'positive' : event.tone === 'negative' ? 'negative' : 'muted'}">${languageEscape(terminalLocal(event.text))}</span></div>`).join('')}</div>`;
}

function terminalRenderRangeButtons() {
  return [['3m', 'range_3m'], ['6m', 'range_6m'], ['1y', 'range_1y']].map(([key, text]) =>
    `<button type="button" data-range="${key}" aria-pressed="${terminalRange === key}">${languageEscape(languageText(text))}</button>`).join('');
}

function terminalRenderToggleButtons() {
  return [['smc', 'toggle_smc'], ['bollinger', 'toggle_bollinger'], ['sma', 'toggle_sma'], ['volume', 'toggle_volume'], ['rsi', 'toggle_rsi'], ['macd', 'toggle_macd']]
    .map(([key, text]) => `<button type="button" data-toggle="${key}" aria-pressed="${terminalToggle[key]}">${languageEscape(languageText(text))}</button>`).join('');
}

function terminalRenderSkeleton() {
  const main = document.getElementById('terminal-main');
  const p = terminalPayload, count = p.ohlcv.close.length, last = count - 1;
  const change = count > 1 ? (p.ohlcv.close[last] / p.ohlcv.close[last - 1] - 1) * 100 : 0;
  const changeText = languageText(change >= 0 ? 'change_up' : 'change_down', { value: Math.abs(change).toFixed(1) });
  const dip = p.dip_buy;
  main.innerHTML = `
    <header class="header-row">
      <div><h1>${languageEscape(p.symbol)}</h1><small>${p.ohlcv.close[last].toFixed(2)} · <span class="${change >= 0 ? 'positive' : 'negative'}">${languageEscape(changeText)}</span></small>
        <br><small>${languageEscape(languageText('price_as_of', { date: p.as_of }))} · ${languageEscape(languageText('generated_label', { time: p.generated_at || '—' }))}</small></div>
      <div class="verdict"><small>${languageEscape(languageText('verdict'))}</small><h1 class="${terminalVerdictColor(dip.verdict)}">${dip.score}</h1><small>${languageEscape(terminalVerdictWord(dip.verdict))}</small></div>
    </header>
    <section><h3>${languageEscape(languageText('pipeline'))}</h3><div class="pipeline">${terminalRenderPipeline(p.pipeline)}</div></section>
    <div class="controls" role="group" aria-label="${languageEscape(languageText('chart_price'))}">
      <div class="group">${terminalRenderRangeButtons()}</div>
      <div class="group">${terminalRenderToggleButtons()}</div>
    </div>
    <section class="box chart-block"><header><h3>${languageEscape(languageText('chart_price'))}</h3><small id="price-readout"></small></header>
      <div class="chart-host" data-chart="price"></div></section>
    <section class="box chart-block" data-block="volume"><header><h3>${languageEscape(languageText('chart_volume'))}</h3></header><div class="chart-host" data-chart="volume"></div></section>
    <section class="box chart-block" data-block="rsi"><header><h3>${languageEscape(languageText('chart_rsi'))}</h3></header><div class="chart-host" data-chart="rsi"></div></section>
    <section class="box chart-block" data-block="macd"><header><h3>${languageEscape(languageText('chart_macd'))}</h3></header><div class="chart-host" data-chart="macd"></div></section>
    <section><h3>${languageEscape(languageText('strategies_heading'))}</h3><div class="card-grid">${p.strategy_card_list.map(terminalRenderStrategyCard).join('')}</div></section>
    <section class="box"><h3>${languageEscape(languageText('events_heading'))}</h3>${terminalRenderEvents(p.event_list)}</section>`;
  terminalSyncControls();
  terminalDrawAll();
}

function terminalSyncControls() {
  document.querySelectorAll('[data-range]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.range === terminalRange)));
  document.querySelectorAll('[data-toggle]').forEach(button => button.setAttribute('aria-pressed', String(terminalToggle[button.dataset.toggle])));
  for (const key of ['volume', 'rsi', 'macd']) {
    const block = document.querySelector(`[data-block="${key}"]`);
    if (block) block.hidden = !terminalToggle[key];
  }
}

function terminalRenderSideList(symbolCardList) {
  const current = terminalSymbolFromPath();
  document.getElementById('symbol-list').innerHTML = symbolCardList.map(card => {
    const unit = card.change_unit === 'percent' ? '%' : (card.change_unit || '');
    const change = card.change_value === null || card.change_value === undefined ? '' : `${card.change_value >= 0 ? '+' : ''}${Number(card.change_value).toFixed(1)}${unit}`;
    return `<a class="row" href="/terminal/${encodeURIComponent(card.symbol)}"${card.symbol === current ? ' aria-current="true"' : ''}>
      <span>${languageEscape(card.symbol)}</span><small>${terminalFinite(card.price) ? Number(card.price).toFixed(2) : ''} ${languageEscape(change)}</small></a>`;
  }).join('');
}

async function terminalLoadSideList() {
  try {
    const response = await fetch('/api/v1/snapshot');
    if (!response.ok) throw new Error(String(response.status));
    terminalRenderSideList((await response.json()).symbol_card_list);
  } catch (error) { document.getElementById('symbol-list').innerHTML = ''; }
}

async function terminalLoadSymbol(symbol) {
  const loadId = ++terminalLoadId;
  const main = document.getElementById('terminal-main');
  if (!symbol) { main.innerHTML = `<small>${languageEscape(languageText('select_symbol'))}</small>`; return; }
  main.innerHTML = `<small>${languageEscape(languageText('loading_data'))}</small>`;
  let payload = null, status = 0;
  try {
    const response = await fetch('/api/v1/terminal/' + encodeURIComponent(symbol));
    status = response.status;
    if (response.ok) payload = await response.json();
  } catch (error) { status = 0; }
  if (loadId !== terminalLoadId) return;
  if (!payload) {
    terminalPayload = null; terminalFailed = true;
    main.innerHTML = `<small class="negative">${languageEscape(languageText(status === 404 ? 'terminal_unknown' : 'terminal_unavailable'))}</small>`;
    return;
  }
  terminalPayload = payload; terminalFailed = false; terminalHover = null;
  terminalRenderSkeleton();
}

function terminalHandleLanguageChange() {
  document.getElementById('theme-button').setAttribute('aria-label', languageText('switch_theme'));
  document.getElementById('theme-button').title = languageText('switch_theme');
  terminalRenderSideList(terminalSideCardList);
  if (terminalPayload) terminalRenderSkeleton();
  else terminalLoadSymbol(terminalSymbolFromPath());
}

function terminalRedrawSoon() {
  if (!terminalFrame) terminalFrame = requestAnimationFrame(() => { terminalFrame = 0; terminalDrawAll(); });
}

function terminalBindEvents() {
  const main = document.getElementById('terminal-main');
  main.addEventListener('click', event => {
    const rangeButton = event.target.closest('[data-range]');
    if (rangeButton) { terminalRange = rangeButton.dataset.range; terminalDrawAll(); terminalSyncControls(); return; }
    const toggleButton = event.target.closest('[data-toggle]');
    if (toggleButton) { const key = toggleButton.dataset.toggle; terminalToggle[key] = !terminalToggle[key]; terminalSyncControls(); terminalDrawAll(); }
  });
  main.addEventListener('pointermove', event => {
    const host = event.target.closest('[data-chart]');
    if (!host || !terminalPayload) return;
    terminalHover = terminalIndexFromEvent(event, host);
    terminalUpdateReadout();
    terminalRedrawSoon();
  });
  main.addEventListener('pointerout', event => {
    if (event.target.closest('[data-chart]') && !(event.relatedTarget && event.relatedTarget.closest && event.relatedTarget.closest('[data-chart]'))) {
      terminalHover = null; terminalUpdateReadout(); terminalRedrawSoon();
    }
  });
  let resizeTimer = null;
  window.addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(terminalDrawAll, 120); });
  document.getElementById('theme-button').onclick = () => {
    const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem('stock-benchmark-theme', next); } catch (error) { /* storage blocked: theme lasts this visit only */ }
  };
}

async function terminalStart() {
  try { if (localStorage.getItem('stock-benchmark-theme') === 'dark') document.documentElement.dataset.theme = 'dark'; } catch (error) { /* storage blocked: light theme */ }
  languageInitialize('en');
  languageBindSwitch(terminalHandleLanguageChange);
  document.getElementById('theme-button').setAttribute('aria-label', languageText('switch_theme'));
  document.getElementById('theme-button').title = languageText('switch_theme');
  terminalBindEvents();
  try {
    const response = await fetch('/api/v1/snapshot');
    terminalSideCardList = response.ok ? (await response.json()).symbol_card_list : [];
  } catch (error) { terminalSideCardList = []; }
  terminalRenderSideList(terminalSideCardList);
  terminalLoadSymbol(terminalSymbolFromPath());
}

terminalStart();
