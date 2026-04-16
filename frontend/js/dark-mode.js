/**
 * dark-mode.js – Full site dark mode with localStorage persistence
 * NCC Unit, Govt. Polytechnic Hamirpur (HP)
 */
(function () {
  const STORAGE_KEY = 'ncc-dark-mode';
  const html = document.documentElement;

  // Apply saved preference immediately (before paint)
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved === 'dark') html.setAttribute('data-theme', 'dark');

  function toggle() {
    const isDark = html.getAttribute('data-theme') === 'dark';
    html.setAttribute('data-theme', isDark ? 'light' : 'dark');
    localStorage.setItem(STORAGE_KEY, isDark ? 'light' : 'dark');
    updateToggleBtns(!isDark);
  }

  function updateToggleBtns(isDark) {
    document.querySelectorAll('.dark-toggle').forEach(btn => {
      btn.innerHTML = isDark
        ? '<i class="fas fa-sun"></i>'
        : '<i class="fas fa-moon"></i>';
      btn.setAttribute('title', isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode');
    });
  }

  // Inject toggle button into every navbar
  function injectToggle() {
    const containers = document.querySelectorAll('.topbar-right, .navbar-actions');
    containers.forEach(container => {
      if (container.querySelector('.dark-toggle')) return;
      const btn = document.createElement('button');
      btn.className = 'dark-toggle topbar-btn';
      btn.style.cssText = 'width:36px;height:36px;border-radius:8px;background:var(--off-white);border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;color:var(--navy);font-size:0.9rem;transition:all 0.2s;';
      btn.onclick = toggle;
      btn.setAttribute('aria-label', 'Toggle dark mode');
      container.prepend(btn);
    });
    updateToggleBtns(html.getAttribute('data-theme') === 'dark');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectToggle);
  } else {
    injectToggle();
  }

  // Register Service Worker
  if ('serviceWorker' in navigator) {
    const swPath = location.pathname.includes('/pages/') ? '../sw.js' : 'sw.js';
    navigator.serviceWorker.register(swPath).catch(() => {});
  }

  window.darkMode = { toggle };
})();
