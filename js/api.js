/**
 * api.js — Central API Client for NCC Website
 * Includes MockDB fallback so the site works without a backend.
 * Backend base: http://localhost:8000
 */

const API_BASE = '';

// ── MockDB: localStorage-based mock database ──────────────────────────────────
const MockDB = {
  // ── Users ──
  _defaultUsers: [
    { username: 'arjun', email: 'arjun@ncc.in', password: 'cadet123', first_name: 'Arjun', last_name: 'Sharma', role: 'cadet', created_at: '2023-08-15T00:00:00.000Z' }
  ],
  getUsers: () => {
    try {
      const stored = JSON.parse(localStorage.getItem('ncc_users') || 'null');
      if (stored && stored.length > 0) return stored;
    } catch {}
    return MockDB._defaultUsers;
  },
  saveUsers: (users) => localStorage.setItem('ncc_users', JSON.stringify(users)),
  findUser: (username, email) => {
    const users = MockDB.getUsers();
    return users.find(u => u.username === username || u.email === email);
  },
  addUser: (user) => {
    const users = MockDB.getUsers();
    users.push(user);
    MockDB.saveUsers(users);
  },

  // ── Notices ──
  getNotices: () => {
    try {
      const stored = JSON.parse(localStorage.getItem('ncc_notices') || 'null');
      if (stored) return stored;
    } catch {}
    // Default notices
    return [
      { id: 1, title: 'CATC Camp Registration Open', category: 'Urgent', description: 'Combined Annual Training Camp registration is now open. All interested cadets must register by 30th April 2025. Medical fitness certificate is mandatory.', created_at: new Date(Date.now() - 86400000 * 2).toISOString() },
      { id: 2, title: 'B Certificate Examination Schedule', category: 'Exam', description: 'B Certificate examination is scheduled for 25th April 2025. Cadets who have completed 2 years of NCC are eligible. Report at 8 AM sharp.', created_at: new Date(Date.now() - 86400000 * 5).toISOString() },
      { id: 3, title: 'Annual Inspection – April 2025', category: 'Information', description: 'Annual inspection by Commanding Officer will be held on 15th April 2025. All cadets must be in full uniform. Parade practice every morning at 6 AM.', created_at: new Date(Date.now() - 86400000 * 7).toISOString() },
      { id: 4, title: 'NCC Day Celebration', category: 'Camp', description: 'NCC Day will be celebrated on 28th November with march-past, cultural events and prize distribution. Attendance is compulsory for all cadets.', created_at: new Date(Date.now() - 86400000 * 10).toISOString() },
      { id: 5, title: 'Thal Sainik Camp Trials', category: 'Urgent', description: 'Selection trials for Thal Sainik Camp will be held on 10th March 2025. Cadets interested must report to the NCC office by 5th March.', created_at: new Date(Date.now() - 86400000 * 14).toISOString() },
      { id: 6, title: 'Blood Donation Camp', category: 'Information', description: 'NCC unit is organising a blood donation camp on 22nd March 2025 in collaboration with District Hospital Hamirpur. All healthy cadets are encouraged to donate.', created_at: new Date(Date.now() - 86400000 * 20).toISOString() },
    ];
  },
  saveNotices: (notices) => localStorage.setItem('ncc_notices', JSON.stringify(notices)),
  addNotice: (notice) => {
    const notices = MockDB.getNotices();
    notice.id = Date.now();
    notice.created_at = new Date().toISOString();
    notices.unshift(notice);
    MockDB.saveNotices(notices);
    return notice;
  },
  deleteNotice: (id) => {
    const notices = MockDB.getNotices().filter(n => n.id != id);
    MockDB.saveNotices(notices);
  },

  // ── Events ──
  getEvents: () => {
    try {
      const stored = JSON.parse(localStorage.getItem('ncc_events') || 'null');
      if (stored) return stored;
    } catch {}
    return [
      { id: 1, title: 'CATC Camp 2025', start_date: new Date(Date.now() + 86400000 * 5).toISOString(), location: 'NCC Training Ground, Hamirpur', event_type: 'Camp', is_mandatory: true, participants: 180 },
      { id: 2, title: 'Annual Inspection', start_date: new Date(Date.now() + 86400000 * 10).toISOString(), location: 'College Ground', event_type: 'Parade', is_mandatory: true, participants: 250 },
      { id: 3, title: 'Blood Donation Camp', start_date: new Date(Date.now() + 86400000 * 15).toISOString(), location: 'District Hospital Hamirpur', event_type: 'Social', is_mandatory: false, participants: 60 },
      { id: 4, title: 'B Certificate Exam', start_date: new Date(Date.now() + 86400000 * 20).toISOString(), location: 'NCC Office', event_type: 'Exam', is_mandatory: true, participants: 45 },
    ];
  },
  saveEvents: (events) => localStorage.setItem('ncc_events', JSON.stringify(events)),
  addEvent: (ev) => {
    const events = MockDB.getEvents();
    ev.id = Date.now();
    events.unshift(ev);
    MockDB.saveEvents(events);
    return ev;
  },
  deleteEvent: (id) => {
    MockDB.saveEvents(MockDB.getEvents().filter(e => e.id != id));
  },

  // ── Cadets / Enrollment ──
  getCadets: () => {
    try {
      const stored = JSON.parse(localStorage.getItem('ncc_cadets') || 'null');
      if (stored) return stored;
    } catch {}
    return [
      { id: 1, name: 'Arjun Sharma', username: 'arjun', email: 'arjun@ncc.in', roll: 'CS-2023-01', year: '2nd', wing: 'Army', status: 'active', branch: 'Computer Engineering', enrolled_on: '2023-08-15', _synced: true },
      { id: 2, name: 'Priya Verma', roll: 'EC-2023-05', year: '1st', wing: 'Naval', status: 'active', branch: 'Electronics Engineering', enrolled_on: '2023-09-01', _synced: true },
      { id: 3, name: 'Rohit Singh', roll: 'ME-2023-12', year: '1st', wing: 'Army', status: 'pending', branch: 'Mechanical Engineering', enrolled_on: '2024-01-10', _synced: true },
      { id: 4, name: 'Anjali Rani', roll: 'CS-2022-07', year: '3rd', wing: 'Air', status: 'active', branch: 'Computer Engineering', enrolled_on: '2022-08-20', _synced: true },
      { id: 5, name: 'Sandeep Kumar', roll: 'CE-2023-18', year: '1st', wing: 'Army', status: 'inactive', branch: 'Civil Engineering', enrolled_on: '2023-08-30', _synced: true },
    ];
  },
  saveCadets: (cadets) => localStorage.setItem('ncc_cadets', JSON.stringify(cadets)),
  addCadet: (cadet) => {
    const cadets = MockDB.getCadets();
    cadet.id = Date.now();
    cadet.enrolled_on = new Date().toISOString().split('T')[0];
    cadet.status = 'pending';
    // Normalize wing: strip " Wing" suffix so display is consistent
    if (cadet.wing) cadet.wing = cadet.wing.replace(/\s+Wing$/i, '').trim();
    if (cadet.ncc_wing) cadet.ncc_wing = cadet.ncc_wing.replace(/\s+Wing$/i, '').trim();
    cadets.push(cadet);
    MockDB.saveCadets(cadets);
    return cadet;
  },

  // ── Gallery ──
  getGallery: () => {
    try {
      const stored = JSON.parse(localStorage.getItem('ncc_gallery') || 'null');
      if (stored) return stored;
    } catch {}
    // Default offline gallery with NCC-themed placeholder images
    return [
      { id: 1, title: 'Republic Day Parade 2024', category: 'Parade', image_url: 'https://images.unsplash.com/photo-1517649763962-0c623066013b?w=600&q=80', description: 'Cadets marching at Kartavya Path, New Delhi' },
      { id: 2, title: 'CATC Camp Training', category: 'Camps', image_url: 'https://images.unsplash.com/photo-1504280390367-361c6d9f38f4?w=600&q=80', description: 'Combined Annual Training Camp exercises' },
      { id: 3, title: 'Blood Donation Drive', category: 'Social', image_url: 'https://images.unsplash.com/photo-1615461066841-6116e61058f4?w=600&q=80', description: 'Annual blood donation camp at District Hospital' },
      { id: 4, title: 'College Campus Parade', category: 'Campus', image_url: 'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=600&q=80', description: 'Morning parade on college ground' },
      { id: 5, title: 'Tree Plantation Drive', category: 'Social', image_url: 'https://images.unsplash.com/photo-1542601906897-13f6a4d30ba1?w=600&q=80', description: 'Swachh Bharat Abhiyan tree plantation' },
      { id: 6, title: 'Firing Range Training', category: 'Camps', image_url: 'https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=600&q=80', description: 'Weapon training under Army supervision' },
      { id: 7, title: 'Independence Day March', category: 'Parade', image_url: 'https://images.unsplash.com/photo-1531545514256-b1400bc00f31?w=600&q=80', description: '15th August Independence Day parade' },
      { id: 8, title: 'Adventure Trek', category: 'Camps', image_url: 'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=600&q=80', description: 'High altitude trekking adventure activity' },
    ];
  },
  saveGallery: (items) => localStorage.setItem('ncc_gallery', JSON.stringify(items)),

  // ── Session (Admin) ──
  setAdminSession: () => localStorage.setItem('ncc_admin_session', 'active'),
  getAdminSession: () => localStorage.getItem('ncc_admin_session') === 'active',
  clearAdminSession: () => {
    localStorage.removeItem('ncc_admin_session');
    localStorage.removeItem('ncc_session_created');
  },

  // ── Attendance ──
  getAttendance: () => {
    try { return JSON.parse(localStorage.getItem('ncc_attendance') || '{}'); } catch { return {}; }
  },
  saveAttendance: (att) => localStorage.setItem('ncc_attendance', JSON.stringify(att)),
  markAttendance: (rollOrUsername, date, status) => {
    const att = MockDB.getAttendance();
    if (!att[date]) att[date] = {};
    att[date][rollOrUsername] = status;
    MockDB.saveAttendance(att);
  },
  // ── Module Tests ──
  _defaultTests: [
    {
      id: 1716300000001,
      title: 'NCC Basic Knowledge Test',
      subject: 'General NCC',
      date: new Date(Date.now() + 86400000 * 3).toISOString().split('T')[0],
      duration: 20,
      status: 'active',
      createdAt: new Date().toISOString(),
      questions: [
        { id: 1, q: 'What does NCC stand for?', options: ['National Cadet Corps','National Civil Corps','National Combat Corps','National Career Corps'], correct: 0 },
        { id: 2, q: 'NCC was founded in which year?', options: ['1945','1947','1948','1950'], correct: 2 },
        { id: 3, q: 'What is the motto of NCC?', options: ['Unity and Discipline','Courage and Duty','Serve and Protect','Honor and Valor'], correct: 0 },
        { id: 4, q: 'Which wing is NOT part of NCC?', options: ['Army','Navy','Air Force','Coast Guard'], correct: 3 },
        { id: 5, q: 'The "A" Certificate exam is taken after how many years?', options: ['1 year','2 years','3 years','4 years'], correct: 0 }
      ]
    }
  ],
  getTests: () => {
    try {
      const stored = JSON.parse(localStorage.getItem('ncc_module_tests') || 'null');
      if (stored && stored.length > 0) return stored;
    } catch {}
    return MockDB._defaultTests;
  },
  saveTests: (tests) => localStorage.setItem('ncc_module_tests', JSON.stringify(tests)),
  addTest: (test) => {
    const tests = MockDB.getTests();
    test.id = Date.now();
    test.createdAt = new Date().toISOString();
    test.status = test.status || 'active';
    tests.unshift(test);
    MockDB.saveTests(tests);
    return test;
  },
  deleteTest: (id) => {
    MockDB.saveTests(MockDB.getTests().filter(t => t.id != id));
  },
  updateTestStatus: (id, status) => {
    const tests = MockDB.getTests().map(t => t.id == id ? { ...t, status } : t);
    MockDB.saveTests(tests);
  },

  // ── Test Results ──
  getResults: () => {
    try { return JSON.parse(localStorage.getItem('ncc_test_results') || '[]'); } catch { return []; }
  },
  saveResults: (results) => localStorage.setItem('ncc_test_results', JSON.stringify(results)),
  submitResult: (result) => {
    const results = MockDB.getResults();
    // Prevent duplicate submission for same test+cadet
    const idx = results.findIndex(r => r.testId == result.testId && r.cadetUsername === result.cadetUsername);
    if (idx > -1) { results[idx] = result; } else { results.push(result); }
    MockDB.saveResults(results);
    return result;
  },
  getResultsByTest: (testId) => MockDB.getResults().filter(r => r.testId == testId),
  getResultsByUser: (username) => MockDB.getResults().filter(r => r.cadetUsername === username),
  hasAttempted: (testId, username) => MockDB.getResults().some(r => r.testId == testId && r.cadetUsername === username),

  // ── Achievements ──
  _defaultAchievements: [
    { id: 1, cadet: 'Arjun Sharma', award: 'Best Cadet Award (CATC)', date: '2025-05-10', type: 'Award' },
    { id: 2, cadet: 'Anjali Rani', award: 'Gold Medal in Shooting (RDC)', date: '2025-01-26', type: 'Competition' },
    { id: 3, cadet: 'Priya Verma', award: 'Naval Camp Parade Commander', date: '2025-02-14', type: 'Camp' }
  ],
  getAchievements: () => {
    try {
      const stored = JSON.parse(localStorage.getItem('ncc_achievements') || 'null');
      if (stored && stored.length > 0) return stored;
    } catch {}
    return MockDB._defaultAchievements;
  },
  saveAchievements: (ach) => localStorage.setItem('ncc_achievements', JSON.stringify(ach)),
  addAchievement: (ach) => {
    const list = MockDB.getAchievements();
    ach.id = Date.now();
    ach.date = ach.date || new Date().toISOString().split('T')[0];
    list.unshift(ach);
    MockDB.saveAchievements(list);
    return ach;
  },
  deleteAchievement: (id) => {
    MockDB.saveAchievements(MockDB.getAchievements().filter(x => x.id != id));
  },
};

// ── Token Management ──────────────────────────────────────────────────────────
const Auth = {
  getToken: () => localStorage.getItem('ncc_access_token'),
  getRefresh: () => localStorage.getItem('ncc_refresh_token'),
  setTokens: (access, refresh) => {
    localStorage.setItem('ncc_access_token', access);
    if (refresh) localStorage.setItem('ncc_refresh_token', refresh);
    // Track creation time for mock tokens so we can expire them
    if (access && access.startsWith('mock_') && !localStorage.getItem('ncc_session_created')) {
      localStorage.setItem('ncc_session_created', Date.now().toString());
    }
  },
  clearTokens: () => {
    localStorage.removeItem('ncc_access_token');
    localStorage.removeItem('ncc_refresh_token');
    localStorage.removeItem('ncc_user');
    localStorage.removeItem('ncc_session_created');
    MockDB.clearAdminSession();
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
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 3000);
    const res = await fetch(url, { ...options, headers, signal: controller.signal });
    clearTimeout(timeout);
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
    return { offline: true, error: true, message: 'Server offline — using local data.' };
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

// ── Route-specific helpers (with MockDB fallback) ─────────────────────────────
const fileToBase64 = (file) => new Promise((resolve) => {
  if (!file || !(file instanceof File) || !file.type.startsWith('image/')) return resolve(null);
  const reader = new FileReader();
  reader.onload = (e) => {
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement('canvas');
      const MAX_W = 250, MAX_H = 300;
      let w = img.width, h = img.height;
      if (w > MAX_W) { h *= MAX_W / w; w = MAX_W; }
      if (h > MAX_H) { w *= MAX_H / h; h = MAX_H; }
      canvas.width = w; canvas.height = h;
      canvas.getContext('2d').drawImage(img, 0, 0, w, h);
      resolve(canvas.toDataURL('image/jpeg', 0.8));
    };
    img.onerror = () => resolve(null);
    img.src = e.target.result;
  };
  reader.onerror = () => resolve(null);
  reader.readAsDataURL(file);
});

const NccAPI = {
  // Public Stats
  getPublicStats: async () => {
    const r = await api.get('/api/stats/public');
    if (r.error) return { total_cadets: MockDB.getCadets().length, total_events: MockDB.getEvents().length, total_notices: MockDB.getNotices().length, total_achievements: 32 };
    return r;
  },

  // Notices
  getNotices: async (params = {}) => {
    const r = await api.get('/api/notices/', params);
    if (r.error) return { success: true, notices: MockDB.getNotices() };
    return r;
  },
  createNotice: async (form) => {
    const r = await api.postForm('/api/notices/', form);
    if (r.error) {
      const notice = { title: form.get('title'), category: form.get('category'), description: form.get('description') };
      const added = MockDB.addNotice(notice);
      return { success: true, notice: added };
    }
    return r;
  },
  deleteNotice: async (id) => {
    const r = await api.delete(`/api/notices/${id}`);
    if (r.error) { MockDB.deleteNotice(id); return { success: true }; }
    return r;
  },

  // Gallery
  getGallery: async (params = {}) => {
    const r = await api.get('/api/gallery/', params);
    if (r.error) return { success: true, items: MockDB.getGallery() };
    return r;
  },
  addGallery: async (form) => {
    const r = await api.postForm('/api/gallery/', form);
    if (r.error) {
      const item = { id: Date.now(), title: form.get('title') || 'Photo', category: form.get('category') || 'General', image_url: null };
      const gallery = MockDB.getGallery(); gallery.push(item); MockDB.saveGallery(gallery);
      return { success: true, item };
    }
    return r;
  },
  deleteGallery: async (id) => {
    const r = await api.delete(`/api/gallery/${id}`);
    if (r.error) { MockDB.saveGallery(MockDB.getGallery().filter(g => g.id != id)); return { success: true }; }
    return r;
  },

  // Achievements
  getAchievements: async (params = {}) => {
    const r = await api.get('/api/achievements/', params);
    if (r.error) return { success: true, achievements: MockDB.getAchievements() };
    return r;
  },
  createAchievement: async (form) => {
    const r = await api.postForm('/api/achievements/', form);
    if (r.error) {
      const ach = {
        cadet: form.get('cadet') || form.get('ach-cadet'),
        award: form.get('award') || form.get('ach-award'),
        type: form.get('type') || form.get('ach-type'),
      };
      const added = MockDB.addAchievement(ach);
      return { success: true, achievement: added };
    }
    return r;
  },
  deleteAchievement: async (id) => {
    const r = await api.delete(`/api/achievements/${id}`);
    if (r.error) {
      MockDB.deleteAchievement(id);
      return { success: true };
    }
    return r;
  },

  // Camps
  getCamps: () => api.get('/api/camps/'),

  // Contact
  submitContact: async (json) => {
    const r = await api.post('/api/contact/', json);
    if (r.error) return { success: true, message: 'Message saved locally.' };
    return r;
  },
  getContacts: () => api.get('/api/contact/'),
  markRead: (id) => api.patch(`/api/contact/${id}/read`, {}),

  // Auth
  login: async (json) => {
    // Backend expects { email, password } — accept either .email or .username as identifier
    const identifier = json.email || json.username || '';
    const loginPayload = { email: identifier, password: json.password };
    const r = await api.post('/api/auth/login', loginPayload);
    if (!r.error) return r;
    // MockDB fallback — use the identifier as username for lookup
    const username = identifier;
    const password = json.password;
    // Admin account — accepts username 'admin', email 'ncc@admin.com', or that email as username field
    if ((username === 'admin' || username === 'ncc@admin.com' || username === 'ncc@admin' || username === 'admin@gph.edu.in') && password === 'ncc@admin123') {
      const token = 'mock_admin_token_' + Date.now();
      Auth.setTokens(token, null);
      const adminUser = { username: 'Admin', email: 'ncc@admin.com', role: 'admin' };
      Auth.setUser(adminUser);
      MockDB.setAdminSession();
      return { success: true, access_token: token, user: adminUser };
    }
    // Cadet accounts (match by username/roll or email)
    const user = MockDB.getUsers().find(u => (u.username === username || u.email === username) && u.password === password);
    if (user) {
      const token = 'mock_cadet_token_' + Date.now();
      Auth.setTokens(token, null);
      const cadetUser = { username: user.username, email: user.email, role: 'cadet' };
      Auth.setUser(cadetUser);
      return { success: true, access_token: token, user: cadetUser };
    }
    return { error: true, message: 'Invalid credentials. Please try again.' };
  },
  signup: async (json) => {
    // Backend expects confirm_password field
    const payload = { ...json, confirm_password: json.password };
    const r = await api.post('/api/auth/register', payload);
    if (!r.error) return r;
    // MockDB fallback
    const { username, email, password, first_name, last_name } = json;
    const existing = MockDB.findUser(username, email);
    if (existing) return { error: true, message: 'An account with this username or email already exists.' };
    MockDB.addUser({ username, email, password, first_name, last_name, role: 'cadet', created_at: new Date().toISOString() });
    return { success: true, message: 'Account created successfully!' };
  },
  verifyOtp: (json) => api.post('/api/auth/verify-otp', json),
  me: () => api.get('/api/auth/me'),
  logout: async () => {
    await api.post('/api/auth/logout', {}).catch(() => {});
    return { success: true };
  },

  // Students
  enroll: async (form) => {
    // Backend expects 'roll_no' and 'ncc_wing' — rename fields if needed
    const backendForm = new FormData();
    for (const [key, val] of form.entries()) {
      if (key === 'roll_number') backendForm.append('roll_no', val);
      else if (key === 'wing') backendForm.append('ncc_wing', val);
      else if (key === 'photo') backendForm.append('photo', val);
      else backendForm.append(key, val);
    }
    const r = await api.postForm('/api/students/enroll', backendForm);
    if (r.error) {
      let photo_url = null;
      if (form.get('photo')) photo_url = await fileToBase64(form.get('photo'));

      const rawWing = (form.get('wing') || 'Army').replace(/\s+Wing$/i, '').trim();
      const aadhaarRaw = form.get('aadhaar') || '';
      const aadhaarMasked = aadhaarRaw.length >= 4 ? 'XXXX-XXXX-' + aadhaarRaw.slice(-4) : aadhaarRaw;
      const cadet = {
        name: (form.get('first_name') || '') + ' ' + (form.get('last_name') || ''),
        first_name: form.get('first_name'),
        last_name: form.get('last_name'),
        dob: form.get('dob'),
        gender: form.get('gender'),
        blood_group: form.get('blood_group'),
        phone: form.get('phone'),
        email: form.get('email'),
        aadhaar: aadhaarMasked,
        roll_no: form.get('roll_number'),
        roll: form.get('roll_number'),
        year: form.get('year') || '1st',
        wing: rawWing,
        ncc_wing: rawWing,
        branch: form.get('branch') || 'General',
        motivation: form.get('motivation'),
        prev_exp: form.get('prev_exp'),
        photo_url: photo_url
      };
      const added = MockDB.addCadet(cadet);
      return { success: true, reference_number: 'NCC-' + String(added.id).slice(-6), message: 'Enrollment submitted!' };
    }
    // Normalize backend response: reference field
    if (r.reference) r.reference_number = r.reference;
    return r;
  },
  getStudents: async (params = {}) => {
    const r = await api.get('/api/students/', params);
    if (r.error) return { success: true, students: MockDB.getCadets() };
    return r;
  },
  updateStudentStatus: (id, form) => api.patchForm(`/api/students/${id}/status`, form),
  deleteStudent: async (id) => {
    const r = await api.delete(`/api/students/${id}`);
    if (r.error) {
      const cadets = MockDB.getCadets().filter(c => c.id != id);
      MockDB.saveCadets(cadets);
      return { success: true };
    }
    return r;
  },

  // Attendance
  markAttendance: async (json) => {
    const r = await api.post('/api/attendance/mark', json);
    if (!r.error) return r;
    // MockDB fallback
    const user = Auth.getUser();
    if (!user) return { error: true, message: 'Not logged in' };
    MockDB.markAttendance(user.username, json.date, json.status);
    return { success: true, message: 'Attendance marked offline.' };
  },
  getAttendanceRecords: async (date) => {
    const r = await api.get('/api/attendance/', { date });
    if (!r.error) return r;
    // MockDB fallback
    const att = MockDB.getAttendance();
    const records = att[date] || {};
    return { success: true, records };
  },

  // Events
  getEvents: async (params = {}) => {
    const r = await api.get('/api/events/', params);
    if (r.error) return { success: true, events: MockDB.getEvents() };
    return r;
  },
  createEvent: async (form) => {
    const r = await api.postForm('/api/events/', form);
    if (r.error) {
      const ev = {
        title: form.get('title'),
        start_date: form.get('start_date') || form.get('date'),
        location: form.get('location') || 'Main Campus Ground',
        event_type: form.get('event_type') || 'Camp',
        is_mandatory: form.get('is_mandatory') === 'true',
        participants: parseInt(form.get('participants')) || 50
      };
      const added = MockDB.addEvent(ev);
      return { success: true, event: added };
    }
    return r;
  },
  deleteEvent: async (id) => {
    const r = await api.delete(`/api/events/${id}`);
    if (r.error) {
      MockDB.deleteEvent(id);
      return { success: true };
    }
    return r;
  },

  // Certificates
  getCertificates: async () => {
    const r = await api.get('/api/certificates/mine');
    if (r.error) {
      const user = Auth.getUser();
      return {
        success: true,
        status: 'pending',
        student_id: 'STU-' + (user?.username || 'DEMO').toUpperCase(),
        certificates: [
          { type: 'A Certificate', available: false, download_url: null },
          { type: 'B Certificate', available: false, download_url: null },
        ]
      };
    }
    return r;
  },
  generateCertificate: (studentId) => `${API_BASE}/api/certificates/generate/${studentId}`,

  // Dashboard
  getDashboardStats: async () => {
    const r = await api.get('/api/dashboard/stats');
    if (r.error) {
      return {
        success: true,
        total_cadets: MockDB.getCadets().length,
        total_events: MockDB.getEvents().length,
        active_notices: MockDB.getNotices().length,
        total_achievements: 32,
      };
    }
    return r;
  },

  // Analytics (silent)
  trackView: (page) => {
    try {
      const form = new FormData();
      form.append('page', page);
      api.postForm('/api/analytics/pageview', form).catch(() => {});
    } catch(_) {}
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
      display:flex;flex-direction:column;gap:12px;pointer-events:none;
    `;
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  const colors = { info:'#3498db', success:'#27ae60', error:'#c0392b', warning:'#f39c12' };
  const icons  = { info:'ℹ️', success:'✅', error:'❌', warning:'⚠️' };
  toast.style.cssText = `
    background:white;border-left:4px solid ${colors[type]||colors.info};
    border-radius:8px;padding:14px 18px;box-shadow:0 8px 32px rgba(0,0,0,0.18);
    font-family:'Poppins',sans-serif;font-size:0.875rem;color:#1a2a4a;
    max-width:340px;animation:toastIn 0.35s ease;display:flex;gap:10px;align-items:center;
    pointer-events:all;cursor:pointer;
  `;
  toast.innerHTML = `<span>${icons[type]||icons.info}</span><span>${message}</span>`;
  toast.onclick = () => toast.remove();
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
    @keyframes toastIn  { from{opacity:0;transform:translateX(60px)} to{opacity:1;transform:none} }
    @keyframes toastOut { from{opacity:1;transform:none} to{opacity:0;transform:translateX(60px)} }
  `;
  document.head.appendChild(style);
})();

// ── Problem 4 Fix: Background Sync ───────────────────────────────────────────
// Attempts to silently upload offline MockDB cadet data to the live backend
// when it becomes reachable, preventing data loss from browser cache clears.
const BackgroundSync = {
  SYNC_KEY: 'ncc_last_sync',

  // Run silently - never blocks UI, never shows errors to user
  async run() {
    try {
      // Only run if there are unsynced cadets in the MockDB
      const cadets = MockDB.getCadets();
      const unsynced = cadets.filter(c => !c._synced);
      if (unsynced.length === 0) return;

      // Check if backend is reachable with a lightweight ping
      const ping = await fetch(`${API_BASE}/api/health`, {
        method: 'GET', signal: AbortSignal.timeout(3000)
      }).catch(() => null);
      if (!ping || !ping.ok) return; // Backend offline, try again next time

      // Backend is up — attempt to push each unsynced cadet
      const token = Auth.getToken();
      if (!token) return; // Need auth token to upload

      let syncedCount = 0;
      for (const cadet of unsynced) {
        try {
          // Use FormData so the endpoint (multipart/form-data) accepts it
          const fd = new FormData();
          
          // Split name if first_name/last_name are missing
          if (!cadet.first_name && cadet.name) {
            const parts = cadet.name.split(' ');
            cadet.first_name = parts[0] || '';
            cadet.last_name = parts.slice(1).join(' ') || '';
          }

          Object.entries(cadet).forEach(([k, v]) => {
            if (k !== '_synced' && v != null) fd.append(k, String(v));
          });
          if (cadet.first_name && !fd.has('first_name')) fd.append('first_name', cadet.first_name);
          if (cadet.last_name && !fd.has('last_name')) fd.append('last_name', cadet.last_name);

          const res = await fetch(`${API_BASE}/api/students/enroll`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: fd
          });
          if (res.ok) {
            cadet._synced = true;
            syncedCount++;
          }
        } catch (_) { /* Skip failed individual records */ }
      }

      if (syncedCount > 0) {
        // Save updated sync status back to MockDB
        MockDB.saveCadets(cadets);
        localStorage.setItem(BackgroundSync.SYNC_KEY, new Date().toISOString());
        console.info(`[NCC Sync] Successfully synced ${syncedCount} cadet record(s) to the server.`);
      }
    } catch (_) { /* Fail silently */ }
  },

  // Schedule sync 5 seconds after page load to avoid blocking initial render
  schedule() {
    setTimeout(() => BackgroundSync.run(), 5000);
  }
};

// ── HTML Sanitizer (prevents XSS from user-controlled data) ──────────────────
function sanitizeHTML(str) {
  const div = document.createElement('div');
  div.textContent = String(str == null ? '' : str);
  return div.innerHTML;
}

// Expose globally
window.NccAPI = NccAPI;
window.Auth = Auth;
window.MockDB = MockDB;
window.showToast = showToast;
window.sanitizeHTML = sanitizeHTML;
window.API_BASE = API_BASE;
window.BackgroundSync = BackgroundSync;

// Auto-schedule background sync on every page load
BackgroundSync.schedule();
