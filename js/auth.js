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

    // Decode JWT and check expiry
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      if (payload.exp && Date.now() / 1000 > payload.exp) {
        localStorage.removeItem('ncc_access_token');
        localStorage.removeItem('ncc_refresh_token');
        localStorage.removeItem('ncc_user');
        window.location.href = loginPage;
        return false;
      }
    } catch(e) {
      window.location.href = loginPage;
      return false;
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
   * Update the navbar to show logged-in state (user icon + logout button).
   */
  window.updateNavbarAuth = function() {
    const user = (() => { try { return JSON.parse(localStorage.getItem('ncc_user')); } catch { return null; } })();
    const actionsEl = document.querySelector('.navbar-actions');
    if (!actionsEl) return;

    if (user) {
      const portalLink = user.role === 'admin' ? 'admin-dashboard.html' : 'cadet-portal.html';
      actionsEl.innerHTML = `
        <a href="${portalLink}" class="btn-nav-login" style="display:flex;align-items:center;gap:6px;">
          <i class="fas fa-user-circle"></i> ${user.username || 'My Portal'}
        </a>
        <button onclick="window.doLogout()" class="btn-nav-enroll" style="cursor:pointer;border:none;">
          <i class="fas fa-sign-out-alt"></i> Logout
        </button>`;
    }
  };

  window.doLogout = async function() {
    try { await NccAPI.logout(); } catch(_) {}
    Auth.clearTokens();
    const isPages = window.location.pathname.includes('/pages/');
    window.location.href = isPages ? '../index.html' : 'index.html';
  };

  // Auto-update navbar on every page
  document.addEventListener('DOMContentLoaded', () => {
    if (Auth && Auth.isLoggedIn()) {
      window.updateNavbarAuth();
    }
  });

})();
