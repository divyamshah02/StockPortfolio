let _csrfToken = null;
let _selectedType = 'BUY';
let _verifiedSymbol = null;
let _allTrades = [];
let _deleteTargetId = null;
let _deleteModal = null;

document.addEventListener('DOMContentLoaded', function () {
  _csrfToken = window.CSRF_TOKEN || '';
  _deleteModal = new bootstrap.Modal(document.getElementById('modal-delete-trade'));

  document.getElementById('trade-date').value = new Date().toISOString().slice(0, 10);

  document.getElementById('btn-type-buy').addEventListener('click', function () { setTradeType('BUY'); });
  document.getElementById('btn-type-sell').addEventListener('click', function () { setTradeType('SELL'); });

  document.getElementById('btn-check-price').addEventListener('click', checkPrice);
  document.getElementById('trade-symbol').addEventListener('input', function () {
    _verifiedSymbol = null;
    document.getElementById('check-price-box').classList.remove('show');
  });
  document.getElementById('trade-symbol').addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.nativeEvent?.isComposing && e.keyCode !== 229) {
      e.preventDefault();
      checkPrice();
    }
  });

  document.getElementById('btn-submit-trade').addEventListener('click', submitTrade);
  document.getElementById('filter-symbol').addEventListener('change', applyFilters);
  document.getElementById('filter-type').addEventListener('change', applyFilters);
  document.getElementById('btn-confirm-delete-trade').addEventListener('click', confirmDeleteTrade);

  loadTrades();
});

function setTradeType(type) {
  _selectedType = type;
  document.getElementById('btn-type-buy').classList.toggle('active', type === 'BUY');
  document.getElementById('btn-type-sell').classList.toggle('active', type === 'SELL');
}

function hideTradeError() {
  document.getElementById('alert-trade-error').classList.remove('show');
}

function showTradeError(msg) {
  var el = document.getElementById('alert-trade-error');
  el.textContent = msg;
  el.classList.add('show');
}

async function checkPrice() {
  hideTradeError();
  var symbol = document.getElementById('trade-symbol').value.trim().toUpperCase();
  if (!symbol) {
    showTradeError('Enter a stock symbol first.');
    return;
  }

  var btn = document.getElementById('btn-check-price');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-sm"></span>';

  var result = await callApi('GET', window.TRADES_URLS.checkPrice + '?symbol=' + encodeURIComponent(symbol), null, _csrfToken);
  var ok = result[0];
  var data = result[1];

  btn.disabled = false;
  btn.textContent = 'Check';

  if (!ok || !data.success) {
    _verifiedSymbol = null;
    document.getElementById('check-price-box').classList.remove('show');
    showTradeError((data && data.error) || 'Could not verify that symbol.');
    return;
  }

  var info = data.data;
  _verifiedSymbol = info.symbol;
  document.getElementById('trade-symbol').value = info.symbol;
  document.getElementById('check-price-name').textContent = info.name;
  document.getElementById('check-price-exchange').textContent = info.exchange;
  document.getElementById('check-price-value').textContent = formatMoney(info.current_price);
  document.getElementById('check-price-box').classList.add('show');

  var priceField = document.getElementById('trade-price');
  if (!priceField.value) priceField.value = info.current_price;

  showToast('Verified ' + info.symbol + ' — ' + info.name, 'success');
}

async function submitTrade() {
  hideTradeError();

  var symbol = document.getElementById('trade-symbol').value.trim().toUpperCase();
  var quantity = document.getElementById('trade-quantity').value;
  var price = document.getElementById('trade-price').value;
  var trade_date = document.getElementById('trade-date').value;
  var notes = document.getElementById('trade-notes').value.trim();

  if (!symbol) {
    showTradeError('Enter and check a stock symbol first.');
    return;
  }
  if (!_verifiedSymbol || _verifiedSymbol !== symbol) {
    showTradeError('Please click "Check" to verify this symbol before saving.');
    return;
  }
  if (!quantity || Number(quantity) <= 0) {
    showTradeError('Enter a valid quantity.');
    return;
  }
  if (!price || Number(price) <= 0) {
    showTradeError('Enter a valid price.');
    return;
  }
  if (!trade_date) {
    showTradeError('Select the trade date.');
    return;
  }

  var btn = document.getElementById('btn-submit-trade');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-sm"></span> Saving...';

  var result = await callApi('POST', window.TRADES_URLS.trades, {
    symbol: symbol,
    trade_type: _selectedType,
    quantity: quantity,
    price: price,
    trade_date: trade_date,
    notes: notes
  }, _csrfToken);

  var ok = result[0];
  var data = result[1];

  btn.disabled = false;
  btn.textContent = 'Save trade';

  if (!ok || !data.success) {
    showTradeError((data && data.error) || 'Could not save this trade.');
    return;
  }

  showToast((_selectedType === 'BUY' ? 'Buy' : 'Sell') + ' trade recorded for ' + symbol, 'success');
  resetTradeForm();
  loadTrades();
}

function resetTradeForm() {
  document.getElementById('trade-symbol').value = '';
  document.getElementById('trade-quantity').value = '';
  document.getElementById('trade-price').value = '';
  document.getElementById('trade-notes').value = '';
  document.getElementById('trade-date').value = new Date().toISOString().slice(0, 10);
  document.getElementById('check-price-box').classList.remove('show');
  _verifiedSymbol = null;
  setTradeType('BUY');
}

async function loadTrades() {
  document.getElementById('trades-loading').style.display = 'block';
  document.getElementById('trades-table-wrap').style.display = 'none';
  document.getElementById('trades-empty').style.display = 'none';

  var result = await callApi('GET', window.TRADES_URLS.trades, null, _csrfToken);
  var ok = result[0];
  var data = result[1];

  document.getElementById('trades-loading').style.display = 'none';

  if (!ok || !data.success) {
    showToast((data && data.error) || 'Could not load trades.', 'error');
    return;
  }

  _allTrades = data.data.trades || [];
  populateSymbolFilter(_allTrades);
  applyFilters();
}

function populateSymbolFilter(trades) {
  var select = document.getElementById('filter-symbol');
  var current = select.value;
  var symbols = Array.from(new Set(trades.map(function (t) { return t.stock_symbol; }))).sort();

  select.innerHTML = '<option value="">All stocks</option>';
  symbols.forEach(function (s) {
    var opt = document.createElement('option');
    opt.value = s;
    opt.textContent = s;
    select.appendChild(opt);
  });
  select.value = current;
}

function applyFilters() {
  var symbol = document.getElementById('filter-symbol').value;
  var type = document.getElementById('filter-type').value;

  var filtered = _allTrades.filter(function (t) {
    if (symbol && t.stock_symbol !== symbol) return false;
    if (type && t.trade_type !== type) return false;
    return true;
  });

  renderTrades(filtered);
}

function renderTrades(trades) {
  var tbody = document.getElementById('trades-tbody');
  tbody.innerHTML = '';

  if (!trades || trades.length === 0) {
    document.getElementById('trades-table-wrap').style.display = 'none';
    document.getElementById('trades-empty').style.display = 'block';
    return;
  }

  document.getElementById('trades-table-wrap').style.display = 'block';
  document.getElementById('trades-empty').style.display = 'none';

  trades.forEach(function (t) {
    var pnlClass = t.realized_pnl > 0 ? 'up' : t.realized_pnl < 0 ? 'down' : '';
    var tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="text-muted-custom">${escapeHtml(t.trade_date)}</td>
      <td class="fw-semibold">${escapeHtml(t.stock_symbol)}</td>
      <td><span class="pill ${t.trade_type === 'BUY' ? 'pill-buy' : 'pill-sell'}">${t.trade_type}</span></td>
      <td class="text-end mono">${formatNumber(t.quantity)}</td>
      <td class="text-end mono">${formatMoney(t.price)}</td>
      <td class="text-end mono">${formatNumber(t.quantity_after_trade)}</td>
      <td class="text-end mono">${formatMoney(t.average_price_after_trade)}</td>
      <td class="text-end mono ${pnlClass}">${t.trade_type === 'SELL' ? formatMoney(t.realized_pnl) : '—'}</td>
      <td class="text-end">
        <button type="button" class="btn btn-ghost btn-sm" data-id="${t.id}" onclick="openDeleteModal(${t.id})" aria-label="Delete trade">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function openDeleteModal(id) {
  _deleteTargetId = id;
  _deleteModal.show();
}

async function confirmDeleteTrade() {
  if (!_deleteTargetId) return;

  var url = window.TRADES_URLS.tradeDetail.replace('__ID__', _deleteTargetId);
  var result = await callApi('DELETE', url, null, _csrfToken);
  var ok = result[0];
  var data = result[1];

  _deleteModal.hide();

  if (!ok || !data.success) {
    showToast((data && data.error) || 'Could not delete this trade.', 'error');
    return;
  }

  showToast('Trade deleted.', 'success');
  _deleteTargetId = null;
  loadTrades();
}
