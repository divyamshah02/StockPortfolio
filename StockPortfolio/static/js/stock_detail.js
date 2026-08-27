document.addEventListener('DOMContentLoaded', loadStockDetail);

async function loadStockDetail() {
  var result = await callApi('GET', window.STOCK_DETAIL.holdingUrl, null, window.CSRF_TOKEN);
  var ok = result[0];
  var data = result[1];

  document.getElementById('detail-loading').style.display = 'none';

  if (!ok || !data.success) {
    showToast((data && data.error) || 'Could not load this stock.', 'error');
    setTimeout(function () { window.location.href = window.STOCK_DETAIL.tradesUrl; }, 1400);
    return;
  }

  document.getElementById('detail-content').style.display = 'block';

  renderHeader(data.data.stock);
  renderHoldingStats(data.data.holding);
  renderAvgChart(data.data.trades);
  renderTradesTable(data.data.trades);
}

function renderHeader(stock) {
  document.getElementById('detail-avatar').textContent = stock.symbol.slice(0, 2);
  document.getElementById('detail-name').textContent = stock.name || stock.symbol;
  document.getElementById('detail-exchange').textContent = stock.symbol + ' · ' + (stock.exchange || 'NSE');
  document.getElementById('detail-current-price').textContent =
    stock.last_price != null ? formatMoney(stock.last_price) : '—';
}

function renderHoldingStats(holding) {
  if (!holding || holding.quantity <= 0) {
    document.getElementById('holding-stats-row').style.display = 'none';
    document.getElementById('no-holding-note').style.display = 'block';
    return;
  }

  document.getElementById('stat-qty').textContent = formatNumber(holding.quantity);
  document.getElementById('stat-avg').textContent = formatMoney(holding.average_price);

  var unrealizedEl = document.getElementById('stat-unrealized');
  var pctEl = document.getElementById('stat-unrealized-pct');
  if (holding.unrealized_pnl != null) {
    unrealizedEl.textContent = formatMoney(holding.unrealized_pnl);
    unrealizedEl.classList.add(holding.unrealized_pnl >= 0 ? 'up' : 'down');
    if (holding.current_value != null && holding.total_invested > 0) {
      var pct = (holding.unrealized_pnl / holding.total_invested) * 100;
      pctEl.textContent = formatPercent(pct);
      pctEl.classList.add(pct >= 0 ? 'up' : 'down');
    }
  } else {
    unrealizedEl.textContent = '—';
  }

  var realizedEl = document.getElementById('stat-realized');
  realizedEl.textContent = formatMoney(holding.realized_pnl);
  realizedEl.classList.add(Number(holding.realized_pnl) >= 0 ? 'up' : 'down');
}

function renderAvgChart(trades) {
  var ctx = document.getElementById('chart-avg');
  if (!trades || trades.length === 0) {
    ctx.style.display = 'none';
    return;
  }

  var sorted = trades.slice().sort(function (a, b) {
    return new Date(a.trade_date) - new Date(b.trade_date);
  });

  var isLight = document.documentElement.getAttribute('data-theme') === 'light';

  new Chart(ctx, {
    type: 'line',
    data: {
      labels: sorted.map(function (t) { return t.trade_date; }),
      datasets: [
        {
          label: 'Average price (₹)',
          data: sorted.map(function (t) { return t.average_price_after_trade; }),
          borderColor: '#2f6fed',
          backgroundColor: 'rgba(47,111,237,0.12)',
          borderWidth: 2,
          tension: 0.25,
          pointRadius: 3,
          yAxisID: 'y',
          fill: true,
        },
        {
          label: 'Quantity held',
          data: sorted.map(function (t) { return t.quantity_after_trade; }),
          borderColor: '#f59e0b',
          borderWidth: 2,
          borderDash: [4, 4],
          tension: 0.25,
          pointRadius: 3,
          yAxisID: 'y1',
          fill: false,
        },
      ],
    },
    options: {
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { position: 'bottom', labels: { color: isLight ? '#12161d' : '#eaeef3', boxWidth: 10, font: { size: 11 } } },
      },
      scales: {
        x: { ticks: { color: isLight ? '#626c7a' : '#8c98a8' }, grid: { display: false } },
        y: {
          position: 'left',
          ticks: { color: isLight ? '#626c7a' : '#8c98a8', callback: function (v) { return formatMoney(v); } },
          grid: { color: isLight ? '#ebedf1' : '#1b232e' },
        },
        y1: {
          position: 'right',
          ticks: { color: isLight ? '#626c7a' : '#8c98a8' },
          grid: { display: false },
        },
      },
    },
  });
}

function renderTradesTable(trades) {
  var tbody = document.getElementById('trades-tbody');
  tbody.innerHTML = '';

  var sorted = trades.slice().sort(function (a, b) {
    return new Date(b.trade_date) - new Date(a.trade_date);
  });

  sorted.forEach(function (t) {
    var pnlClass = t.realized_pnl > 0 ? 'up' : t.realized_pnl < 0 ? 'down' : '';
    var tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="text-muted-custom">${escapeHtml(t.trade_date)}</td>
      <td><span class="pill ${t.trade_type === 'BUY' ? 'pill-buy' : 'pill-sell'}">${t.trade_type}</span></td>
      <td class="text-end mono">${formatNumber(t.quantity)}</td>
      <td class="text-end mono">${formatMoney(t.price)}</td>
      <td class="text-end mono">${formatNumber(t.quantity_after_trade)}</td>
      <td class="text-end mono">${formatMoney(t.average_price_after_trade)}</td>
      <td class="text-end mono ${pnlClass}">${t.trade_type === 'SELL' ? formatMoney(t.realized_pnl) : '—'}</td>
    `;
    tbody.appendChild(tr);
  });
}
