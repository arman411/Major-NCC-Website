/**
 * api.js — Central API Client for NCC Website
 * All fetch calls go through this module.
 * Uses http://localhost:8000 as the backend base.
 */

const API_BASE = 'http://localhost:8000';

// ── Token Management ──────────────────────────────────────────────────────────
const Auth = {
  getToken: () => localStorage.getItem('ncc_access_token'),
  getRefresh: () => localStorage.getItem('ncc_refresh_token'),
  setTokens: (access, refresh) => {
    localStorage.setItem('ncc_access_token', access);
    if (refresh) localStorage.setItem('ncc_refresh_token', refresh);
  },
  clearTokens: () => {
    localStorage.removeItem('ncc_access_token');
    localStorage.removeItem('ncc_refresh_token');
    localStorage.removeItem('ncc_user');
  },
  getUser: () => {
    try { return JSON.parse(localStorage.getItem('ncc_user') || 'null'); } catch { return null; }
  },
  setUser: (user) => localStorage.setItem('ncc_user', JSON.stringify(user)),
  isLoggedIn: () => !!localStorage.getItem('ncc_access_token'),
  isAdmin: () => {
    const u = Auth.getUser();
    return u && u.role === 'admin';
  }
};

// ── Core Fetch Wrapper ────────────────────────────────────────────────────────
async function apiFetch(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const token = Auth.getToken();

  const headers = { ...options.headers };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (options.json) {
    headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(options.json);
    delete options.json;
  }

  try {
    const res = await fetch(url, { ...options, headers });
    if (res.status === 401) {
      Auth.clearTokens();
      return { error: true, status: 401, message: 'Session expired. Please login again.' };
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return { error: true, status: res.status, message: data.detail || 'Request failed' };
    }
    return data;
  } catch (err) {
    console.warn('API offline or unreachable:', err.message);
    return { offline: true, error: true, message: 'Cannot reach server. Please check your connection.' };
  }
}

// ── Convenience helpers ───────────────────────────────────────────────────────
const api = {
  get:    (url, params) => {
    const qs = params ? '?' + new URLSearchParams(params).toString() : '';
    return apiFetch(url + qs);
  },
  post:   (url, json)   => apiFetch(url, { method: 'POST', json }),
  postForm: (url, form) => apiFetch(url, { method: 'POST', body: form }),
  patch:  (url, json)   => apiFetch(url, { method: 'PATCH', json }),
  patchForm: (url, form) => apiFetch(url, { method: 'PATCH', body: form }),
  delete: (url)         => apiFetch(url, { method: 'DELETE' }),
};

// ── Route-specific helpers ────────────────────────────────────────────────────
const NccAPI = {
  // Public Stats
  getPublicStats: () => api.get('/api/stats/public'),

  // Leaderboard
  getLeaderboard: () => api.get('/api/leaderboard/'),

  // Notices
  getNotices: (params = {}) => api.get('/api/notices/', params),
  createNotice: (form) => api.postForm('/api/notices/', form),
  deleteNotice: (id) => api.delete(`/api/notices/${id}`),

  // Gallery
  getGallery: (params = {}) => api.get('/api/gallery/', params),
  addGallery: (form) => api.postForm('/api/gallery/', form),
  deleteGallery: (id) => api.delete(`/api/gallery/${id}`),

  // Achievements
  getAchievements: (params = {}) => api.get('/api/achievements/', params),
  createAchievement: (form) => api.postForm('/api/achievements/', form),
  deleteAchievement: (id) => api.delete(`/api/achievements/${id}`),

  // camps
  getCamps: () => api.get('/api/camps/'),

  // Contact
  submitContact: (json) => api.post('/api/contact/', json),
  getContacts: () => api.get('/api/contact/'),
  markRead: (id) => api.patch(`/api/contact/${id}/read`, {}),

  // Auth
  login: (json) => api.post('/api/auth/login', json),
  verifyOtp: (json) => api.post('/api/auth/verify-otp', json),
  signup: (json) => api.post('/api/auth/signup', json),
  me: () => api.get('/api/auth/me'),
  logout: () => api.post('/api/auth/logout', {}),

  // Students
  enroll: (form) => api.postForm('/api/students/enroll', form),
  getStudents: (params = {}) => api.get('/api/students/', params),
  updateStudentStatus: (id, form) => api.patchForm(`/api/students/${id}/status`, form),
  deleteStudent: (id) => api.delete(`/api/students/${id}`),

  // Events
  getEvents: (params = {}) => api.get('/api/events/', params),
  createEvent: (form) => api.postForm('/api/events/', form),
  deleteEvent: (id) => api.delete(`/api/events/${id}`),

  // Certificates
  getCertificates: () => api.get('/api/certificates/mine'),
  generateCertificate: (studentId) => `${API_BASE}/api/certificates/generate/${studentId}`,

  // Dashboard
  getDashboardStats: () => api.get('/api/dashboard/stats'),

  // Analytics
  trackView: (page) => {
    const form = new FormData();
    form.append('page', page);
    api.postForm('/api/analytics/pageview', form).catch(() => {});
  }
};

// ── Toast notification ────────────────────────────────────────────────────────
function showToast(message, type = 'info', duration = 4000) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.style.cssText = `
      position:fixed;bottom:24px;right:24px;z-index:9999;
      display:flex;flex-direction:column;gap:12px;
    `;
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  const colors = { info:'#3498db', success:'#27ae60', error:'#c0392b', warning:'#f39c12' };
  const icons  = { info:'ℹ️', success:'✅', error:'❌', warning:'⚠️' };
  toast.style.cssText = `
    background:white;border-left:4px solid ${colors[type]||colors.info};
    border-radius:8px;padding:14px 18px;box-shadow:0 8px 32px rgba(0,0,0,0.15);
    font-family:'Poppins',sans-serif;font-size:0.875rem;color:#1a2a4a;
    max-width:320px;animation:toastIn 0.35s ease;display:flex;gap:10px;align-items:center;
  `;
  toast.innerHTML = `<span>${icons[type]||icons.info}</span><span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.animation = 'toastOut 0.3s ease forwards';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// Inject toast CSS
(function() {
  const style = document.createElement('style');
  style.textContent = `
    @keyframes toastIn  { from{opacity:0;transform:translateX(50px)} to{opacity:1;transform:none} }
    @keyframes toastOut { from{opacity:1;transform:none} to{opacity:0;transform:translateX(50px)} }
  `;
  document.head.appendChild(style);
})();

// Track current page
NccAPI.trackView(window.location.pathname);

// Expose globally
window.NccAPI = NccAPI;
window.Auth = Auth;
window.showToast = showToast;
window.API_BASE = API_BASE;
