(function () {
  var STORAGE_KEY = "stockportfolio-theme";

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", theme === "light" ? "#f5f6f8" : "#0a0e14");
  }

  function toggleTheme() {
    var current = document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
    var next = current === "light" ? "dark" : "light";
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch (e) {}
    applyTheme(next);
  }

  window.toggleTheme = toggleTheme;
  window.__applyStoredTheme = function () {
    var stored = null;
    try {
      stored = localStorage.getItem(STORAGE_KEY);
    } catch (e) {}
    applyTheme(stored === "light" ? "light" : "dark");
  };
})();
