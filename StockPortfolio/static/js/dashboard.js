let allocationChart = null;
let pnlChart = null;

document.addEventListener('DOMContentLoaded', loadDashboard);

async function loadDashboard() {
  const result = await callApi('GET', window.DASHBOARD_URLS.dashboard);
  const ok = result[0];
  const data = result[1];

  document.getElementById('dash-loading').style.display = 'none';
  document.getElementById('dash-content').style.display = 'block';

  if (!ok || !data.success) {
    showToast((data && data.error) || 'Could not load dashboard.', 'error');
    return;
  }

  renderSummary(data.data.summary);
  renderAllocation(data.data.allocation);
  renderPnlChart(data.data.holdings);
  renderHoldingsTable(data.data.holdings);
  renderRecentTrades(data.data.recent_trades);
}

function renderSummary(summary) {
  document.getElementById('stat-invested').textContent = formatMoney(summary.total_invested);
  document.getElementById('stat-current').textContent = formatMoney(summary.total_current_value);

  const unrealizedEl = document.getElementById('stat-unrealized');
  unrealizedEl.textContent = formatMoney(summary.total_unrealized_pnl);
  unrealizedEl.classList.add(summary.total_unrealized_pnl >= 0 ? 'up' : 'down');

  const pctEl = document.getElementById('stat-unrealized-pct');
  pctEl.textContent = formatPercent(summary.total_unrealized_pnl_percent);
  pctEl.classList.add(summary.total_unrealized_pnl_percent >= 0 ? 'up' : 'down');

  const realizedEl = document.getElementById('stat-realized');
  realizedEl.textContent = formatMoney(summary.total_realized_pnl);
  realizedEl.classList.add(summary.total_realized_pnl >= 0 ? 'up' : 'down');
}

function chartColors(n) {
  const palette = ['#2f6fed', '#22c55e', '#f59e0b', '#ef4444', '#4f86ff', '#8c98a8', '#0ea5e9', '#a855f7'];
  const out = [];
  for (let i = 0; i < n; i++) out.push(palette[i % palette.length]);
  return out;
}

function renderAllocation(allocation) {
  const ctx = document.getElementById('chart-allocation');
  if (!allocation || allocation.length === 0) {
    document.getElementById('allocation-empty').style.display = 'block';
    ctx.style.display = 'none';
    return;
  }

  const isLight = document.documentElement.getAttribute('data-theme') === 'light';

  allocationChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: allocation.map((a) => a.symbol),
      datasets: [{
        data: allocation.map((a) => a.value),
        backgroundColor: chartColors(allocation.length),
        borderWidth: 2,
        borderColor: isLight ? '#ffffff' : '#131a24',
      }],
    },
    options: {
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: isLight ? '#12161d' : '#eaeef3', boxWidth: 10, font: { size: 11 } },
        },
      },
      cutout: '62%',
    },
  });
}

function renderPnlChart(holdings) {
  const ctx = document.getElementById('chart-pnl');
  const isLight = document.documentElement.getAttribute('data-theme') === 'light';

  if (!holdings || holdings.length === 0) {
    ctx.style.display = 'none';
    return;
  }

  pnlChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: holdings.map((h) => h.symbol),
      datasets: [{
        label: 'Unrealized P&L',
        data: holdings.map((h) => h.unrealized_pnl),
        backgroundColor: holdings.map((h) => (h.unrealized_pnl >= 0 ? '#22c55e' : '#ef4444')),
        borderRadius: 5,
        maxBarThickness: 42,
      }],
    },
    options: {
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: isLight ? '#626c7a' : '#8c98a8' }, grid: { display: false } },
        y: {
          ticks: { color: isLight ? '#626c7a' : '#8c98a8', callback: (v) => formatMoney(v) },
          grid: { color: isLight ? '#ebedf1' : '#1b232e' },
        },
      },
    },
  });
}

function renderHoldingsTable(holdings) {
  const tbody = document.getElementById('holdings-tbody');
  tbody.innerHTML = '';

  if (!holdings || holdings.length === 0) {
    document.getElementById('holdings-empty').style.display = 'block';
    document.getElementById('table-holdings').style.display = 'none';
    return;
  }

  holdings.forEach((h) => {
    const pnlClass = h.unrealized_pnl >= 0 ? 'up' : 'down';
    const detailUrl = window.DASHBOARD_URLS.holdingsDetail.replace('__SYMBOL__', h.symbol);
    const invested = h.average_price * h.quantity;

    const tr = document.createElement('tr');
    tr.className = 'row-clickable';
    tr.onclick = () => { window.location.href = detailUrl; };
    tr.innerHTML = `
      <td>
        <div class="stock-symbol-cell">
          <div class="stock-avatar">${escapeHtml(h.symbol.slice(0, 2))}</div>
          <span class="fw-semibold">${escapeHtml(h.symbol)}</span>
        </div>
      </td>
      <td class="text-end mono">${formatNumber(h.quantity)}</td>
      <td class="text-end mono">${formatMoney(h.average_price)}</td>
      <td class="text-end mono">${h.current_price != null ? formatMoney(h.current_price) : '—'}</td>
      <td class="text-end mono">${formatMoney(invested)}</td>
      <td class="text-end mono">${h.current_price != null ? formatMoney(h.current_price * h.quantity) : '—'}</td>
      <td class="text-end mono ${pnlClass}">
        ${h.unrealized_pnl != null ? formatMoney(h.unrealized_pnl) : '—'}
        ${h.unrealized_pnl_percent != null ? `<span class="d-block" style="font-size:11px;">${formatPercent(h.unrealized_pnl_percent)}</span>` : ''}
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function renderRecentTrades(trades) {
  const tbody = document.getElementById('recent-trades-tbody');
  tbody.innerHTML = '';

  if (!trades || trades.length === 0) {
    document.getElementById('recent-trades-empty').style.display = 'block';
    document.getElementById('table-recent-trades').style.display = 'none';
    return;
  }

  trades.forEach((t) => {
    const tr = document.createElement('tr');
    const pnlClass = t.realized_pnl > 0 ? 'up' : t.realized_pnl < 0 ? 'down' : '';
    tr.innerHTML = `
      <td class="text-muted-custom">${escapeHtml(t.trade_date)}</td>
      <td class="fw-semibold">${escapeHtml(t.stock_symbol)}</td>
      <td><span class="pill ${t.trade_type === 'BUY' ? 'pill-buy' : 'pill-sell'}">${t.trade_type}</span></td>
      <td class="text-end mono">${formatNumber(t.quantity)}</td>
      <td class="text-end mono">${formatMoney(t.price)}</td>
      <td class="text-end mono ${pnlClass}">${t.trade_type === 'SELL' ? formatMoney(t.realized_pnl) : '—'}</td>
    `;
    tbody.appendChild(tr);
  });
}
