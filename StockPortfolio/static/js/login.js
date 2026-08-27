let _csrf = null;
let _urlLogin = null;
let _urlSignup = null;
let _urlDashboard = null;

function LoginInit(csrf, urlLogin, urlSignup, urlDashboard) {
  _csrf = csrf;
  _urlLogin = urlLogin;
  _urlSignup = urlSignup;
  _urlDashboard = urlDashboard;

  document.getElementById('btn-login').addEventListener('click', handleLogin);
  document.getElementById('btn-signup').addEventListener('click', handleSignup);

  ['login-email', 'login-password'].forEach(function (id) {
    document.getElementById(id).addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.nativeEvent?.isComposing && e.keyCode !== 229) handleLogin();
    });
  });
  ['signup-name', 'signup-email', 'signup-password'].forEach(function (id) {
    document.getElementById(id).addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.nativeEvent?.isComposing && e.keyCode !== 229) handleSignup();
    });
  });
}

function switchTab(tab) {
  var isLogin = tab === 'login';
  document.getElementById('tab-login').classList.toggle('active', isLogin);
  document.getElementById('tab-signup').classList.toggle('active', !isLogin);
  document.getElementById('form-login').style.display = isLogin ? 'block' : 'none';
  document.getElementById('form-signup').style.display = isLogin ? 'none' : 'block';
  hideError();
}

function showError(msg) {
  var el = document.getElementById('alert-error');
  el.textContent = msg;
  el.classList.add('show');
}

function hideError() {
  document.getElementById('alert-error').classList.remove('show');
}

async function handleLogin() {
  hideError();
  var email = document.getElementById('login-email').value.trim().toLowerCase();
  var password = document.getElementById('login-password').value;

  if (!email || !password) {
    showError('Please enter your email and password.');
    return;
  }

  var btn = document.getElementById('btn-login');
  btn.disabled = true;
  btn.textContent = 'Signing in...';

  var result = await callApi('POST', _urlLogin, { email: email, password: password }, _csrf);
  var ok = result[0];
  var data = result[1];

  btn.disabled = false;
  btn.textContent = 'Sign in';

  if (!ok || !data.success) {
    showError((data && data.error) || 'Login failed. Please try again.');
    return;
  }

  window.location.href = _urlDashboard;
}

async function handleSignup() {
  hideError();
  var full_name = document.getElementById('signup-name').value.trim();
  var email = document.getElementById('signup-email').value.trim().toLowerCase();
  var password = document.getElementById('signup-password').value;

  if (!email || !password) {
    showError('Please enter your email and password.');
    return;
  }

  var btn = document.getElementById('btn-signup');
  btn.disabled = true;
  btn.textContent = 'Creating account...';

  var result = await callApi('POST', _urlSignup, { email: email, password: password, full_name: full_name }, _csrf);
  var ok = result[0];
  var data = result[1];

  btn.disabled = false;
  btn.textContent = 'Create account';

  if (!ok || !data.success) {
    showError((data && data.error) || 'Could not create account. Please try again.');
    return;
  }

  window.location.href = _urlDashboard;
}
