function showToast(message, type) {
  var stack = document.getElementById('toast-stack');
  if (!stack) return;

  var el = document.createElement('div');
  el.className = 'toast-item ' + (type === 'error' ? 'error' : type === 'success' ? 'success' : '');
  el.textContent = message;
  stack.appendChild(el);

  setTimeout(function () {
    el.style.opacity = '0';
    el.style.transition = 'opacity 0.2s ease';
    setTimeout(function () { el.remove(); }, 200);
  }, 3200);
}

function formatMoney(value) {
  var n = Number(value);
  if (isNaN(n)) return '—';
  return '\u20B9' + n.toLocaleString('en-IN', { maximumFractionDigits: 2, minimumFractionDigits: 2 });
}

function formatNumber(value) {
  var n = Number(value);
  if (isNaN(n)) return '—';
  return n.toLocaleString('en-IN');
}

function formatPercent(value) {
  var n = Number(value);
  if (isNaN(n)) return '—';
  return (n >= 0 ? '+' : '') + n.toFixed(2) + '%';
}

function escapeHtml(str) {
  return String(str == null ? '' : str).replace(/[&<>"']/g, function (c) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
  });
}
