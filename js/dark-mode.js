/**
 * dark-mode.js — Dark Mode toggle for NCC Website
 * Persists preference to localStorage.
 * Respects prefers-color-scheme by default.
 */

(function() {
  'use strict';

  const STORAGE_KEY = 'ncc_theme';

  function getPreference() {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) return stored;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(STORAGE_KEY, theme);
    // Update toggle button icon if present
    const btn = document.getElementById('dark-mode-btn');
    if (btn) {
      btn.innerHTML = theme === 'dark'
        ? '<i class="fas fa-sun"></i>'
        : '<i class="fas fa-moon"></i>';
      btn.title = theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode';
    }
  }

  function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'light';
    applyTheme(current === 'dark' ? 'light' : 'dark');
  }

  // Apply immediately to prevent flash
  applyTheme(getPreference());

  // After DOM is ready, wire up the toggle button
  document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('dark-mode-btn');
    if (btn) btn.addEventListener('click', toggleTheme);
  });

  // Expose globally
  window.toggleTheme = toggleTheme;
  window.applyTheme = applyTheme;
})();
