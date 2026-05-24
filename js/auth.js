/**
 * auth.js — JWT Auth management for NCC Frontend
 * Handles login redirect, route protection, role checks
 */

(function() {
  'use strict';

  /**
   * Require the user to be logged in.
   * Call at top of protected pages.
   * @param {string} requiredRole - 'admin' | 'cadet' | null (any logged-in user)
   * @param {string} redirectTo  - where to redirect if not authed (default: login.html)
   */
  window.requireAuth = function(requiredRole = null, redirectTo = null) {
    const token = localStorage.getItem('ncc_access_token');
    const user  = (() => { try { return JSON.parse(localStorage.getItem('ncc_user')); } catch { return null; } })();

    const loginPage = redirectTo || (window.location.pathname.includes('/pages/') ? 'login.html' : 'pages/login.html');

    if (!token || !user) {
      window.location.href = loginPage;
      return false;
    }

    // Only decode & check expiry for real JWTs (3 dot-separated base64 parts)
    const parts = token.split('.');
    if (parts.length === 3) {
      try {
        const payload = JSON.parse(atob(parts[1]));
        if (payload.exp && Date.now() / 1000 > payload.exp) {
          localStorage.removeItem('ncc_access_token');
          localStorage.removeItem('ncc_refresh_token');
          localStorage.removeItem('ncc_user');
          window.location.href = loginPage;
          return false;
        }
      } catch(e) {
        // Malformed JWT — clear and redirect
        localStorage.removeItem('ncc_access_token');
        localStorage.removeItem('ncc_refresh_token');
        localStorage.removeItem('ncc_user');
        window.location.href = loginPage;
        return false;
      }
    }
    // Mock tokens expire after 8 hours
    if (token.startsWith('mock_')) {
      const createdAt = parseInt(localStorage.getItem('ncc_session_created') || '0', 10);
      const EIGHT_HOURS = 8 * 60 * 60 * 1000;
      if (createdAt && Date.now() - createdAt > EIGHT_HOURS) {
        localStorage.removeItem('ncc_access_token');
        localStorage.removeItem('ncc_refresh_token');
        localStorage.removeItem('ncc_user');
        localStorage.removeItem('ncc_session_created');
        window.location.href = loginPage;
        return false;
      }
    }

    if (requiredRole && user.role !== requiredRole) {
      // Show access denied page inline
      document.body.innerHTML = `
        <div style="min-height:100vh;display:flex;align-items:center;justify-content:center;
          font-family:Poppins,sans-serif;background:#f0f4ff;flex-direction:column;gap:16px;">
          <div style="font-size:4rem;">🚫</div>
          <h2 style="color:#0d2b5e;margin:0">Access Denied</h2>
          <p style="color:#7f8c8d">You need <strong>${requiredRole}</strong> privileges to view this page.</p>
          <a href="javascript:history.back()" style="padding:10px 24px;background:#0d2b5e;color:white;
            border-radius:8px;text-decoration:none;font-weight:600">Go Back</a>
        </div>`;
      return false;
    }

    return true;
  };

  /**
   * Update the navbar to show logged-in state (user icon + logout button),
   * or login/signup when logged out. Preserves the dark-mode toggle button.
   */
  window.updateNavbarAuth = function() {
    const user = (() => { try { return JSON.parse(localStorage.getItem('ncc_user')); } catch { return null; } })();
    const actionsEl = document.querySelector('.navbar-actions');
    if (!actionsEl) return;

    // Determine relative path prefix (pages/ vs root)
    const isPages = window.location.pathname.includes('/pages/');
    const prefix = isPages ? '' : 'pages/';

    // Dark mode button HTML — always preserved
    const darkBtn = `<button id="dark-mode-btn" title="Toggle Dark Mode"><i class="fas fa-moon"></i></button>`;

    if (user) {
      const portalLink = (user.role === 'admin' ? `${prefix}admin-dashboard.html` : `${prefix}cadet-portal.html`);
      actionsEl.innerHTML = `
        ${darkBtn}
        <a href="${portalLink}" class="btn-nav-login" style="display:flex;align-items:center;gap:6px;">
          <i class="fas fa-user-circle"></i> ${user.username || 'My Portal'}
        </a>
        <button onclick="window.doLogout()" class="btn-nav-signup" style="cursor:pointer;border:none;">
          <i class="fas fa-sign-out-alt"></i> Logout
        </button>`;
    } else {
      // Not logged in — show Login + Sign Up
      actionsEl.innerHTML = `
        ${darkBtn}
        <a href="${prefix}login.html" class="btn-nav-login" id="nav-login-btn">
          <i class="fas fa-sign-in-alt"></i> Login
        </a>
        <a href="${prefix}signup.html" class="btn-nav-signup" id="nav-signup-btn">
          <i class="fas fa-user-plus"></i> Sign Up
        </a>`;
    }

    // Re-init dark mode button after innerHTML replacement
    if (typeof initDarkModeBtn === 'function') initDarkModeBtn();
  };

  window.doLogout = async function() {
    try { await NccAPI.logout(); } catch(_) {}
    Auth.clearTokens();
    // Always send to the unified login page
    const isPages = window.location.pathname.includes('/pages/');
    window.location.href = isPages ? 'login.html' : 'pages/login.html';
  };

  /**
   * Quick helper — redirect to login if not authenticated.
   * Works on any page without needing a role check.
   * @param {string} [role] - optional role ('admin'|'cadet')
   */
  window.requireLoginOrRedirect = function(role) {
    return window.requireAuth(role || null);
  };

  // Auto-update navbar on every page load
  document.addEventListener('DOMContentLoaded', () => {
    window.updateNavbarAuth();
  });

})();
