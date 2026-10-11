/* Stockwise front end.
   Plain JavaScript, no frameworks. Each function does one job:
   fetch data from the server (api), then put it on the page (render...). */

const $ = (id) => document.getElementById(id);
const money = (n) => "$" + n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const percent = (n, digits = 1) => (n > 0 ? "+" : "") + n.toFixed(digits) + "%";
const upOrDown = (n) => (n >= 0 ? "up" : "down");
const cssColor = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const escapeHtml = (text) => text.replace(/[&<>\"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const SIGNAL = {
  bullish: { chip: "chip-up", label: "Positive" },
  bearish: { chip: "chip-down", label: "Negative" },
  neutral: { chip: "chip-flat", label: "Neutral" },
};

async function api(path, options) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Something went wrong. Please try again.");
  return data;
}

function showStatus(message, isError = false) {
  const box = $("status");
  box.textContent = message;
  box.className = "status" + (isError ? " error" : "");
  box.hidden = !message;
}

const state = { ticker: "MSFT", horizon: 21, tab: "forecast", market: "all" };
const charts = {};
let stockCatalog = [];

function getMarketName(stock) {
  if (stock && stock.market) return stock.market;
  return stock && /RELIANCE|TCS|INFY|HDFCBANK|ICICIBANK|SBIN|LT|ITC|TATAMOTORS|HCLTECH|MARUTI|KOTAKBANK|AXISBANK|NESTLEIND|BHARTIARTL|WIPRO/i.test(stock.ticker || "") ? "India" : "US";
}

function buildSparkline(values) {
  const clean = values.filter((num) => Number.isFinite(num));
  if (!clean.length) return "";
  const min = Math.min(...clean);
  const max = Math.max(...clean);
  const range = max - min || 1;

  return clean.map((value, index) => {
    const x = (index / Math.max(clean.length - 1, 1)) * 88;
    const y = 32 - ((value - min) / range) * 20;
    return `${index === 0 ? "M" : "L"}${x.toFixed(2)} ${y.toFixed(2)}`;
  }).join(" ");
}

async function hydrateStockCards(cards) {
  const jobs = cards.map(async (button) => {
    try {
      const data = await api(`/api/stock/${button.dataset.ticker}?horizon=21`);
      const priceNode = button.querySelector(".stock-price");
      const deltaNode = button.querySelector(".stock-delta");
      const sparklinePath = button.querySelector(".sparkline-path");
      const diff = Number(data.changes.day || 0);

      if (priceNode) priceNode.textContent = money(data.last_price);
      if (deltaNode) {
        deltaNode.textContent = percent(diff, 2);
        deltaNode.className = "stock-delta " + (diff >= 0 ? "up" : "down");
      }
      if (sparklinePath) {
        const path = buildSparkline(data.history.close.slice(-20));
        sparklinePath.setAttribute("d", path);
        sparklinePath.setAttribute("stroke", diff >= 0 ? "var(--up)" : "var(--down)");
      }
    } catch (error) {
      // Ignore individual card fetch issues and keep the search list usable.
    }
  });

  await Promise.all(jobs);
}

function renderStockGrid() {
  const query = ($("stock-search")?.value || "").trim().toLowerCase();
  const filtered = stockCatalog.filter((stock) => {
    const matchQuery = `${stock.name} ${stock.ticker}`.toLowerCase().includes(query);
    const matchMarket = state.market === "all" || getMarketName(stock) === state.market;
    return matchQuery && matchMarket;
  });

  if (!filtered.length) {
    $("stock-grid").innerHTML = `<div class="panel"><p class="muted">No matching stocks found. Try another company name or ticker.</p></div>`;
    return;
  }

  const cardsHtml = filtered.slice(0, 24).map((stock) => `
    <button class="stock-card ${stock.ticker === state.ticker ? "active" : ""}" type="button" data-ticker="${stock.ticker}">
      <div class="stock-card-top">
        <strong>${stock.ticker}</strong>
        <span class="market-badge ${getMarketName(stock).toLowerCase()}">${getMarketName(stock)}</span>
      </div>
      <span class="stock-name">${stock.name}</span>
      <svg class="sparkline" viewBox="0 0 88 32" aria-hidden="true">
        <path class="sparkline-path" d="" fill="none" stroke="var(--brand)" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"></path>
      </svg>
      <div class="stock-price-row">
        <span class="stock-price">--</span>
        <span class="stock-delta neutral">--</span>
      </div>
    </button>
  `).join("");

  $("stock-grid").innerHTML = cardsHtml;

  $("stock-grid").querySelectorAll(".stock-card").forEach((button) => {
    button.onclick = () => {
      state.ticker = button.dataset.ticker;
      $("stock-select").value = state.ticker;
      renderStockGrid();
      showTab("forecast");
    };
  });

  hydrateStockCards([...$("stock-grid").querySelectorAll(".stock-card")]);
}

function drawChart(id, config) {
  if (charts[id]) charts[id].destroy();
  charts[id] = new Chart($(id), config);
}

function dateTicks() {
  return {
    maxTicksLimit: 8, color: cssColor("--muted"),
    callback(value) {
      const date = new Date(this.getLabelForValue(value) + "T00:00:00");
      return date.toLocaleDateString("en-US", { month: "short", year: "2-digit" });
    },
  };
}

function showTab(name) {
  state.tab = name;
  document.querySelectorAll(".tab").forEach((button) => button.classList.toggle("active", button.dataset.tab === name));
  document.querySelectorAll("main > section").forEach((section) => (section.hidden = section.id !== "tab-" + name));
  $("picker").hidden = !["forecast", "company"].includes(name);
  $("horizon-group").hidden = name !== "forecast";
  showStatus("");
  if (name === "forecast") loadForecast();
  if (name === "company") loadCompany();
}

async function loadForecast() {
  showStatus("Loading " + state.ticker + "...");
  try {
    const data = await api(`/api/stock/${state.ticker}?horizon=${state.horizon}`);
    showStatus("");
    renderSummary(data);
    renderPriceChart(data);
    renderSignals(data);
    renderScorecard(data);
    renderRisk(data.risk);
  } catch (problem) {
    showStatus(problem.message, true);
  }
}

function renderSummary(data) {
  const { forecast, changes } = data;
  $("stock-name").textContent = `${data.name} (${data.ticker})`;
  $("stock-price").textContent = money(data.last_price);
  $("stock-change").textContent = percent(changes.day, 2) + " on the last day";
  $("stock-change").className = "change " + upOrDown(changes.day);
  $("stock-meta").textContent = `Last close: ${data.last_date}. Past month ${percent(changes.month)}, past year ${percent(changes.year)}.`;

  const lean = forecast.summary.lean;
  $("lean-chip").textContent = lean;
  $("lean-chip").className = "chip " + (lean === "Leaning up" ? "chip-up" : lean === "Leaning down" ? "chip-down" : "chip-flat");
  $("confidence-chip").textContent = "Model confidence: " + forecast.picked.confidence;
  $("forecast-text").textContent = forecast.summary.text;
  $("forecast-caveat").textContent = forecast.summary.caveat;
}

function renderPriceChart(data) {
  const past = data.history, future = data.forecast.chart;
  const labels = past.dates.concat(future.dates);
  const gap = Array(past.dates.length - 1).fill(null);
  const pad = (values) => values.concat(Array(future.dates.length).fill(null));
  const fromToday = (values) => gap.concat([data.last_price], values);
  const showAverages = $("show-averages").checked;

  drawChart("price-chart", {
    type: "line",
    data: {
      labels,
      datasets: [
        { label: "Price", data: pad(past.close), borderColor: cssColor("--brand"), borderWidth: 2, pointRadius: 0 },
        { label: "50-day average", data: pad(past.sma50), borderColor: "#E0A100", borderWidth: 1.5, pointRadius: 0, hidden: !showAverages },
        { label: "200-day average", data: pad(past.sma200), borderColor: "#9A6BD8", borderWidth: 1.5, pointRadius: 0, hidden: !showAverages },
        { label: "Forecast", data: fromToday(future.mid), borderColor: cssColor("--forecast"), borderDash: [6, 4], borderWidth: 2, pointRadius: 0 },
        { label: "_low", data: fromToday(future.low), borderColor: "transparent", pointRadius: 0 },
        { label: "Likely range", data: fromToday(future.high), borderColor: "transparent", backgroundColor: cssColor("--forecast-fill"), fill: "-1", pointRadius: 0 },
      ],
    },
    options: {
      maintainAspectRatio: false, interaction: { mode: "index", intersect: false },
      scales: {
        x: { ticks: dateTicks(), grid: { display: false } },
        y: { ticks: { color: cssColor("--muted"), callback: (v) => "$" + v }, grid: { color: cssColor("--line") } },
      },
      plugins: {
        legend: { labels: { color: cssColor("--ink"), filter: (item) => item.text !== "_low", usePointStyle: true } },
        tooltip: { filter: (item) => item.dataset.label !== "_low" && item.raw !== null, callbacks: { label: (c) => `${c.dataset.label}: ${money(c.raw)}` } },
      },
    },
  });
}

function renderSignals(data) {
  const moodChip = $("mood-chip");
  const mood = data.mood;
  moodChip.textContent = "Overall: " + mood;
  moodChip.className = "chip " + (mood === "Positive" ? "chip-up" : mood === "Negative" ? "chip-down" : "chip-flat");

  $("signals").innerHTML = data.indicators.map((item) => `
    <div class="reading">
      <span class="reading-name">${item.name}</span>
      <span class="reading-value">${item.value} <span class="chip ${SIGNAL[item.signal].chip}">${SIGNAL[item.signal].label}</span></span>
      <p class="reading-explain">${item.explain}</p>
    </div>`).join("");
}

function renderScorecard(data) {
  const rows = data.forecast.scorecard;
  $("test-note").textContent = `We trained on older prices, then tested on ${rows[0].test_period}, which the model had not seen.`;
  $("scorecard").innerHTML = rows.map((row) => `
    <tr class="${row.horizon === state.horizon ? "picked" : ""}">
      <td>${row.label}</td>
      <td class="${upOrDown(row.expected_change)}">${percent(row.expected_change)}</td>
      <td>${row.all_accuracy}%</td>
      <td>${row.all_baseline}%</td>
    </tr>`).join("");
}

function renderRisk(risk) {
  $("risk").innerHTML = `
    <dt>Yearly price swings (volatility)</dt><dd>${risk.volatility}%</dd>
    <dt>Biggest fall from a peak</dt><dd>${risk.worst_fall}%</dd>
    <dt>Best single day</dt><dd>${percent(risk.best_day)}</dd>
    <dt>Worst single day</dt><dd>${percent(risk.worst_day)}</dd>`;
}

async function loadCompany() {
  const stock = $("stock-select").selectedOptions[0].textContent;
  $("company-title").textContent = stock;
  showStatus("Loading company numbers...");
  try {
    const data = await api(`/api/company/${state.ticker}`);
    showStatus("");
    $("company-empty").hidden = data.available;
    $("company-body").hidden = !data.available;
    if (!data.available) {
      $("company-empty").innerHTML = `<h2>No yearly financials for ${state.ticker}</h2><p>The company files we have do not include this stock. Try another one, or use the Forecast tab, which does not need them.</p>`;
      return;
    }
    renderCompanyChecks(data);
    renderCompanyChart(data);
    renderBalanceSheet(data);
  } catch (problem) {
    showStatus(problem.message, true);
  }
}

function renderCompanyChecks(data) {
  $("company-checks").innerHTML = data.checks.map((check) => `
    <div class="reading">
      <span class="reading-name">${check.name}</span>
      <span class="reading-value">${check.value} <span class="chip ${SIGNAL[check.signal].chip}">${check.label}</span></span>
      <p class="reading-explain">${check.explain}</p>
    </div>`).join("");
}

function renderCompanyChart(data) {
  drawChart("company-chart", {
    type: "bar",
    data: {
      labels: data.years,
      datasets: [
        { label: "Sales", data: data.revenue, backgroundColor: cssColor("--brand") },
        { label: "Profit", data: data.profit, backgroundColor: cssColor("--up") },
      ],
    },
    options: {
      maintainAspectRatio: false,
      scales: {
        x: { ticks: { color: cssColor("--muted") }, grid: { display: false } },
        y: { ticks: { color: cssColor("--muted"), callback: (v) => "$" + v + "B" }, grid: { color: cssColor("--line") } },
      },
      plugins: { legend: { labels: { color: cssColor("--ink") } }, tooltip: { callbacks: { label: (c) => `${c.dataset.label}: $${c.raw}B` } } },
    },
  });
}

function renderBalanceSheet(data) {
  const row = (label, values) => `<tr><td>${label}</td>${values.map((v) => `<td>${v}</td>`).join("")}</tr>`;
  $("balance-table").innerHTML = `
    <thead><tr><th>Billions of $</th>${data.years.map((y) => `<th>${y}</th>`).join("")}</tr></thead>
    <tbody>${row("Assets (what it owns)", data.assets)}${row("Cash", data.cash)}${row("Equity (owners' share)", data.equity)}</tbody>`;

  const shown = Object.entries(data.valuation).filter(([, value]) => value !== null);
  $("valuation").innerHTML = shown.length
    ? shown.map(([name, value]) => `<dt>${name}</dt><dd>${value}</dd>`).join("")
    : `<dt>Valuation ratios</dt><dd>Not available</dd>`;
}

async function setUpNews() {
  const info = await api("/api/sentiment/info");
  $("news-info").textContent = `Learned from ${info.sentences.toLocaleString()} headlines labelled by finance experts. It is right about ${info.accuracy}% of the time on headlines it has not seen, so treat it as a guide, not a verdict. It reads the text you paste; it does not search for live news.`;
  $("news-example").onclick = () => ($("news-input").value = info.examples.join("\n"));
}

async function checkNews() {
  const headlines = $("news-input").value.split("\n");
  $("news-go").disabled = true;
  try {
    const data = await api("/api/sentiment", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ headlines }),
    });
    showStatus("");
    $("news-output").hidden = false;
    $("meter-marker").style.left = (data.average_mood + 100) / 2 + "%";
    const word = data.average_mood > 15 ? "mostly positive" : data.average_mood < -15 ? "mostly negative" : "neutral or mixed";
    $("news-average").textContent = `These headlines read as ${word}.`;
    $("news-list").innerHTML = data.results.map((r) => `
      <li><span>${escapeHtml(r.text)}</span>
          <span class="chip ${SIGNAL[{ positive: "bullish", negative: "bearish", neutral: "neutral" }[r.label]].chip}">${r.label} (${r.confidence}% sure)</span></li>`).join("");
  } catch (problem) {
    showStatus(problem.message, true);
  } finally {
    $("news-go").disabled = false;
  }
}

async function setUpEconomy() {
  const options = await api("/api/economy/options");
  $("economy-indicator").innerHTML = options.indicators.map((name) => `<option>${name}</option>`).join("");
  $("economy-index").innerHTML = options.indexes.map((name) => `<option>${name}</option>`).join("");
  $("economy-indicator").onchange = $("economy-index").onchange = loadEconomy;
  loadEconomy();
}

async function loadEconomy() {
  try {
    const query = new URLSearchParams({ indicator: $("economy-indicator").value, index: $("economy-index").value });
    const data = await api("/api/economy?" + query);
    $("economy-explain").textContent = data.explain;
    $("economy-note").textContent = `Yearly averages from ${data.rows.toLocaleString()} daily rows (${data.first_date} to ${data.last_date}).`;
    drawChart("economy-chart", {
      type: "line",
      data: { labels: data.years, datasets: [{ label: data.indicator, data: data.values, borderColor: cssColor("--brand"), backgroundColor: cssColor("--brand"), borderWidth: 2.5, pointRadius: 4, tension: 0.25 }] },
      options: {
        maintainAspectRatio: false,
        scales: { x: { ticks: { color: cssColor("--muted") }, grid: { display: false } }, y: { ticks: { color: cssColor("--muted") }, grid: { color: cssColor("--line") } } },
        plugins: { legend: { display: false } },
      },
    });
  } catch (problem) {
    showStatus(problem.message, true);
  }
}

async function start() {
  try {
    const info = await api("/api/stocks");
    stockCatalog = info.stocks;
    $("stock-select").innerHTML = info.stocks.map((s) => `<option value="${s.ticker}">${s.name} (${s.ticker})</option>`).join("");
    $("stock-select").value = state.ticker;
    $("data-range").textContent = `${info.data_starts} to ${info.data_ends}`;

    $("horizon-group").innerHTML = info.horizons.map((h) =>
      `<button type="button" data-days="${h.days}" aria-pressed="${h.days === state.horizon}">${h.label}</button>`).join("");

    renderStockGrid();
    $("stock-search").oninput = renderStockGrid;
  } catch (problem) {
    showStatus("Could not reach the server. Is `python app.py` still running?", true);
    return;
  }

  document.querySelectorAll(".tab").forEach((button) => (button.onclick = () => showTab(button.dataset.tab)));
  document.querySelectorAll(".market-tab").forEach((button) => {
    button.onclick = () => {
      state.market = button.dataset.market;
      document.querySelectorAll(".market-tab").forEach((tab) => tab.classList.toggle("active", tab === button));
      renderStockGrid();
    };
  });
  $("stock-select").onchange = (event) => { state.ticker = event.target.value; showTab(state.tab); };
  $("horizon-group").onclick = (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    state.horizon = Number(button.dataset.days);
    $("horizon-group").querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", b === button));
    loadForecast();
  };
  $("show-averages").onchange = loadForecast;
  $("news-go").onclick = checkNews;

  setUpNews();
  setUpEconomy();
  showTab("forecast");
}

start();
