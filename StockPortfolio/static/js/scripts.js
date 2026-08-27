let _csrfToken = null;
let _allScripts = [];
let _scriptFormModal = null;
let _deleteScriptModal = null;
let _scriptDetailModal = null;
let _deleteTargetId = null;
let _detailScriptId = null;

document.addEventListener('DOMContentLoaded', function () {
  _csrfToken = window.CSRF_TOKEN || '';
  _scriptFormModal = new bootstrap.Modal(document.getElementById('modal-script-form'));
  _deleteScriptModal = new bootstrap.Modal(document.getElementById('modal-delete-script'));
  _scriptDetailModal = new bootstrap.Modal(document.getElementById('modal-script-detail'));

  document.getElementById('btn-open-new-script').addEventListener('click', function () { openScriptForm(null); });
  document.getElementById('btn-save-script').addEventListener('click', saveScript);
  document.getElementById('btn-confirm-delete-script').addEventListener('click', confirmDeleteScript);
  document.getElementById('btn-detail-edit').addEventListener('click', function () {
    _scriptDetailModal.hide();
    openScriptForm(_allScripts.find(function (s) { return s.id === _detailScriptId; }));
  });

  loadScripts();
});

function hideScriptError() {
  document.getElementById('alert-script-error').classList.remove('show');
}

function showScriptError(msg) {
  var el = document.getElementById('alert-script-error');
  el.textContent = msg;
  el.classList.add('show');
}

async function loadScripts() {
  document.getElementById('scripts-loading').style.display = 'block';
  document.getElementById('scripts-grid').style.display = 'none';
  document.getElementById('scripts-empty').style.display = 'none';

  var result = await callApi('GET', window.SCRIPTS_URLS.scripts, null, _csrfToken);
  var ok = result[0];
  var data = result[1];

  document.getElementById('scripts-loading').style.display = 'none';

  if (!ok || !data.success) {
    showToast((data && data.error) || 'Could not load scripts.', 'error');
    return;
  }

  _allScripts = data.data.scripts || [];
  renderScripts(_allScripts);
}

function renderScripts(scripts) {
  var grid = document.getElementById('scripts-grid');
  grid.innerHTML = '';

  if (!scripts || scripts.length === 0) {
    grid.style.display = 'none';
    document.getElementById('scripts-empty').style.display = 'block';
    return;
  }

  document.getElementById('scripts-empty').style.display = 'none';
  grid.style.display = 'flex';

  scripts.forEach(function (s) {
    var col = document.createElement('div');
    col.className = 'col-md-6 col-lg-4';

    var totalPnlClass = s.total_pnl > 0 ? 'up' : s.total_pnl < 0 ? 'down' : '';
    var realizedClass = s.total_realized_pnl > 0 ? 'up' : s.total_realized_pnl < 0 ? 'down' : '';
    var unrealizedClass = s.total_unrealized_pnl > 0 ? 'up' : s.total_unrealized_pnl < 0 ? 'down' : '';

    col.innerHTML = `
      <div class="script-card">
        <div class="d-flex justify-content-between align-items-start gap-2">
          <div>
            <h3 class="script-card-name">${escapeHtml(s.name)}</h3>
            <div class="script-card-desc">${s.description ? escapeHtml(s.description) : '<span class="text-faint">No description</span>'}</div>
          </div>
          <span class="pill ${totalPnlClass === 'up' ? 'pill-gain' : totalPnlClass === 'down' ? 'pill-loss' : 'pill-neutral'}">${formatMoney(s.total_pnl)}</span>
        </div>

        <div class="script-card-metrics">
          <div>
            <div class="script-metric-label">Realized P&amp;L</div>
            <div class="script-metric-value ${realizedClass}">${formatMoney(s.total_realized_pnl)}</div>
          </div>
          <div>
            <div class="script-metric-label">Unrealized P&amp;L</div>
            <div class="script-metric-value ${unrealizedClass}">${formatMoney(s.total_unrealized_pnl)}</div>
          </div>
          <div>
            <div class="script-metric-label">Invested</div>
            <div class="script-metric-value">${formatMoney(s.total_invested)}</div>
          </div>
          <div>
            <div class="script-metric-label">Trades</div>
            <div class="script-metric-value">${formatNumber(s.trade_count)}</div>
          </div>
        </div>

        <div class="script-card-footer">
          <span class="text-faint" style="font-size:11.5px;">${s.stocks_traded} stock${s.stocks_traded === 1 ? '' : 's'} traded</span>
          <div class="script-card-actions">
            <button type="button" class="btn btn-outline-custom btn-sm" data-action="view" data-id="${s.id}">Show more</button>
            <button type="button" class="btn btn-ghost btn-sm" data-action="delete" data-id="${s.id}" aria-label="Delete script">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>
            </button>
          </div>
        </div>
      </div>
    `;

    col.querySelector('[data-action="view"]').addEventListener('click', function () { openScriptDetail(s.id); });
    col.querySelector('[data-action="delete"]').addEventListener('click', function () { openDeleteScriptModal(s.id); });

    grid.appendChild(col);
  });
}

function openScriptForm(script) {
  hideScriptError();
  document.getElementById('script-form-title').textContent = script ? 'Edit script' : 'New script';
  document.getElementById('script-form-id').value = script ? script.id : '';
  document.getElementById('script-name').value = script ? script.name : '';
  document.getElementById('script-description').value = script ? (script.description || '') : '';
  _scriptFormModal.show();
}

async function saveScript() {
  hideScriptError();

  var id = document.getElementById('script-form-id').value;
  var name = document.getElementById('script-name').value.trim();
  var description = document.getElementById('script-description').value.trim();

  if (!name) {
    showScriptError('Give this script a name.');
    return;
  }

  var btn = document.getElementById('btn-save-script');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-sm"></span> Saving...';

  var url = id ? window.SCRIPTS_URLS.scriptDetail.replace('__ID__', id) : window.SCRIPTS_URLS.scripts;
  var method = id ? 'PUT' : 'POST';
  var result = await callApi(method, url, { name: name, description: description }, _csrfToken);
  var ok = result[0];
  var data = result[1];

  btn.disabled = false;
  btn.textContent = 'Save script';

  if (!ok || !data.success) {
    showScriptError((data && data.error) || 'Could not save this script.');
    return;
  }

  _scriptFormModal.hide();
  showToast(id ? 'Script updated.' : 'Script created.', 'success');
  loadScripts();
}

function openDeleteScriptModal(id) {
  _deleteTargetId = id;
  _deleteScriptModal.show();
}

async function confirmDeleteScript() {
  if (!_deleteTargetId) return;

  var url = window.SCRIPTS_URLS.scriptDetail.replace('__ID__', _deleteTargetId);
  var result = await callApi('DELETE', url, null, _csrfToken);
  var ok = result[0];
  var data = result[1];

  _deleteScriptModal.hide();

  if (!ok || !data.success) {
    showToast((data && data.error) || 'Could not delete this script.', 'error');
    return;
  }

  showToast('Script deleted.', 'success');
  _deleteTargetId = null;
  loadScripts();
}

async function openScriptDetail(id) {
  _detailScriptId = id;
  document.getElementById('detail-script-name').textContent = 'Loading…';
  document.getElementById('detail-script-description').textContent = '';
  document.getElementById('detail-stat-cards').innerHTML = '';
  document.getElementById('detail-breakdown-tbody').innerHTML = '';
  document.getElementById('detail-trades-tbody').innerHTML = '';
  _scriptDetailModal.show();

  var url = window.SCRIPTS_URLS.scriptDetail.replace('__ID__', id);
  var result = await callApi('GET', url, null, _csrfToken);
  var ok = result[0];
  var data = result[1];

  if (!ok || !data.success) {
    showToast((data && data.error) || 'Could not load script details.', 'error');
    _scriptDetailModal.hide();
    return;
  }

  renderScriptDetail(data.data);
}

function renderScriptDetail(data) {
  var s = data.script;
  document.getElementById('detail-script-name').textContent = s.name;
  document.getElementById('detail-script-description').textContent = s.description || 'No description';

  var stats = [
    { label: 'Total invested', value: formatMoney(s.total_invested), cls: '' },
    { label: 'Realized P&L', value: formatMoney(s.total_realized_pnl), cls: s.total_realized_pnl > 0 ? 'up' : s.total_realized_pnl < 0 ? 'down' : '' },
    { label: 'Unrealized P&L', value: formatMoney(s.total_unrealized_pnl), cls: s.total_unrealized_pnl > 0 ? 'up' : s.total_unrealized_pnl < 0 ? 'down' : '' },
    { label: 'Total P&L', value: formatMoney(s.total_pnl), cls: s.total_pnl > 0 ? 'up' : s.total_pnl < 0 ? 'down' : '' },
  ];

  var statCardsEl = document.getElementById('detail-stat-cards');
  statCardsEl.innerHTML = stats.map(function (st) {
    return `
      <div class="col-6 col-md-3">
        <div class="detail-stat-card">
          <div class="stat-label">${st.label}</div>
          <div class="stat-value ${st.cls}">${st.value}</div>
        </div>
      </div>
    `;
  }).join('');

  var breakdownTbody = document.getElementById('detail-breakdown-tbody');
  if (!data.stock_breakdown || data.stock_breakdown.length === 0) {
    breakdownTbody.innerHTML = '<tr><td colspan="7" class="text-muted-custom text-center">No stocks traded under this script yet.</td></tr>';
  } else {
    breakdownTbody.innerHTML = data.stock_breakdown.map(function (b) {
      var uClass = b.unrealized_pnl > 0 ? 'up' : b.unrealized_pnl < 0 ? 'down' : '';
      var rClass = b.realized_pnl > 0 ? 'up' : b.realized_pnl < 0 ? 'down' : '';
      return `
        <tr>
          <td class="fw-semibold">${escapeHtml(b.symbol)}</td>
          <td class="text-end mono">${formatNumber(b.quantity)}</td>
          <td class="text-end mono">${b.quantity > 0 ? formatMoney(b.average_price) : '—'}</td>
          <td class="text-end mono">${b.current_price != null ? formatMoney(b.current_price) : '—'}</td>
          <td class="text-end mono ${uClass}">${b.unrealized_pnl != null ? formatMoney(b.unrealized_pnl) : '—'}</td>
          <td class="text-end mono ${rClass}">${formatMoney(b.realized_pnl)}</td>
          <td class="text-end mono">${formatNumber(b.trade_count)}</td>
        </tr>
      `;
    }).join('');
  }

  var tradesTbody = document.getElementById('detail-trades-tbody');
  if (!data.trades || data.trades.length === 0) {
    tradesTbody.innerHTML = '<tr><td colspan="6" class="text-muted-custom text-center">No trades yet.</td></tr>';
  } else {
    tradesTbody.innerHTML = data.trades.map(function (t) {
      var pnlClass = t.realized_pnl > 0 ? 'up' : t.realized_pnl < 0 ? 'down' : '';
      return `
        <tr>
          <td class="text-muted-custom">${escapeHtml(t.trade_date)}</td>
          <td class="fw-semibold">${escapeHtml(t.stock_symbol)}</td>
          <td><span class="pill ${t.trade_type === 'BUY' ? 'pill-buy' : 'pill-sell'}">${t.trade_type}</span></td>
          <td class="text-end mono">${formatNumber(t.quantity)}</td>
          <td class="text-end mono">${formatMoney(t.price)}</td>
          <td class="text-end mono ${pnlClass}">${t.trade_type === 'SELL' ? formatMoney(t.realized_pnl) : '—'}</td>
        </tr>
      `;
    }).join('');
  }
}
