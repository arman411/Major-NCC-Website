"""
inject_advanced.py – Injects dark mode, search modal, PWA & floating widget into all pages
"""
import os, re

PAGES_DIR  = r"e:\Major NCC Website\frontend\pages"
FINDEX     = r"e:\Major NCC Website\frontend\index.html"

# ── CSS to append into global style.css ──────────────────────
ADVANCED_CSS = r"""

/* ════════════════════════════════════════════════════════════
   DARK MODE THEME
   ════════════════════════════════════════════════════════════ */
[data-theme="dark"] {
  --navy:        #4a8fc8;
  --navy-light:  #5ba3dc;
  --red:         #e05c4b;
  --sky:         #5dade2;
  --white:       #1a1f2e;
  --off-white:   #151a27;
  --light-gray:  #1e2538;
  --mid-gray:    #2a3148;
  --text-dark:   #e8edf8;
  --text-mid:    #a8b4cc;
  --text-light:  #6b7a99;
  --shadow-sm:   0 2px 12px rgba(0,0,0,0.3);
  --shadow-md:   0 8px 30px rgba(0,0,0,0.4);
  --shadow-lg:   0 20px 60px rgba(0,0,0,0.5);
  --shadow-xl:   0 30px 80px rgba(0,0,0,0.6);
}
[data-theme="dark"] body              { background: #0f1623; color: #e8edf8; }
[data-theme="dark"] #navbar           { background: rgba(15,22,35,0.95); border-bottom-color: rgba(255,255,255,0.06); }
[data-theme="dark"] .nav-link         { color: #a8b4cc; }
[data-theme="dark"] .nav-link.active, [data-theme="dark"] .nav-link:hover { color: #e8edf8; }
[data-theme="dark"] .card,
[data-theme="dark"] .stat-card,
[data-theme="dark"] .timeline-card,
[data-theme="dark"] .enrollment-card,
[data-theme="dark"] .chart-card,
[data-theme="dark"] .admin-stat-card,
[data-theme="dark"] .table-card,
[data-theme="dark"] .qa-card { background: #1e2538; border-color: #2a3148; }
[data-theme="dark"] .btn-outline      { border-color: #4a8fc8; color: #4a8fc8; }
[data-theme="dark"] .btn-outline:hover { background: #4a8fc8; color: #fff; }
[data-theme="dark"] .form-control     { background: #1a1f2e; border-color: #2a3148; color: #e8edf8; }
[data-theme="dark"] .form-label       { background: #1a1f2e; color: #6b7a99; }
[data-theme="dark"] .page-hero        { background: linear-gradient(160deg, #0f1623 0%, #151a27 50%, #1a2035 100%); }
[data-theme="dark"] .mobile-nav       { background: rgba(15,22,35,0.98); }
[data-theme="dark"] .activity-card-pro,
[data-theme="dark"] .notice-item      { background: #1e2538; border-color: #2a3148; }
[data-theme="dark"] .topbar           { background: #1e2538; border-bottom-color: #2a3148; }
[data-theme="dark"] .sidebar          { background: #0a0f1c; }
[data-theme="dark"] .sidebar-link:hover { background: rgba(255,255,255,0.05); }
[data-theme="dark"] html              { color-scheme: dark; }

/* Smooth dark-mode transition */
body, #navbar, .card, .stat-card, .form-control, .mobile-nav,
.activity-card-pro, .notice-item, .topbar, .sidebar, .timeline-card,
.enrollment-card, .chart-card, .admin-stat-card {
  transition: background 0.3s ease, border-color 0.3s ease, color 0.3s ease;
}

/* ════════════════════════════════════════════════════════════
   SEARCH MODAL
   ════════════════════════════════════════════════════════════ */
#search-modal {
  position: fixed; inset: 0; z-index: 99990;
  display: none; align-items: flex-start; justify-content: center;
  padding-top: 80px;
}
#search-modal.open { display: flex; animation: modalFadeIn 0.2s ease; }
@keyframes modalFadeIn { from { opacity: 0; } to { opacity: 1; } }
#search-overlay {
  position: absolute; inset: 0;
  background: rgba(0,0,0,0.55);
  backdrop-filter: blur(6px);
}
#search-box {
  position: relative; z-index: 1;
  background: white; border-radius: 20px;
  width: min(680px, 90vw);
  box-shadow: 0 40px 120px rgba(0,0,0,0.35), 0 0 0 1px rgba(13,43,94,0.08);
  overflow: hidden;
  animation: boxSlideDown 0.25s cubic-bezier(0.4,0,0.2,1);
}
@keyframes boxSlideDown {
  from { opacity:0; transform:translateY(-20px) scale(0.97); }
  to   { opacity:1; transform:translateY(0) scale(1); }
}
[data-theme="dark"] #search-box { background: #1e2538; box-shadow: 0 40px 120px rgba(0,0,0,0.6); }
#search-input-wrap {
  display: flex; align-items: center; gap: 12px;
  padding: 16px 20px; border-bottom: 1px solid var(--mid-gray);
}
#search-icon { color: var(--text-light); font-size: 1rem; flex-shrink: 0; }
#search-input {
  flex: 1; border: none; outline: none; font-size: 1rem;
  font-family: 'Poppins', sans-serif; background: transparent;
  color: var(--text-dark); font-weight: 500;
}
#search-input::placeholder { color: var(--text-light); }
#search-esc {
  font-size: 0.7rem; padding: 3px 8px; border-radius: 6px;
  background: var(--light-gray); color: var(--text-light); font-weight: 600;
  flex-shrink: 0;
}
#search-results { max-height: 380px; overflow-y: auto; padding: 8px; }
.sr-item {
  display: flex; align-items: center; gap: 14px;
  padding: 12px 14px; border-radius: 12px;
  cursor: pointer; transition: background 0.15s; text-decoration: none;
  color: var(--text-dark);
}
.sr-item.selected, .sr-item:hover { background: var(--light-gray); }
[data-theme="dark"] .sr-item.selected, [data-theme="dark"] .sr-item:hover { background: rgba(255,255,255,0.07); }
.sr-icon { font-size: 1.4rem; width: 36px; text-align: center; flex-shrink: 0; }
.sr-body { flex: 1; min-width: 0; }
.sr-title { display: block; font-size: 0.92rem; font-weight: 600; color: var(--text-dark); }
.sr-desc  { display: block; font-size: 0.78rem; color: var(--text-light); margin-top: 2px; }
.sr-arrow { color: var(--mid-gray); font-size: 0.7rem; flex-shrink: 0; transition: transform 0.15s; }
.sr-item:hover .sr-arrow { transform: translateX(4px); color: var(--sky); }
.sr-empty { text-align: center; padding: 40px 20px; color: var(--text-light); font-size: 0.9rem; }
#search-footer {
  display: flex; gap: 20px; padding: 10px 20px;
  border-top: 1px solid var(--mid-gray); font-size: 0.72rem; color: var(--text-light);
}
#search-footer kbd {
  padding: 2px 7px; background: var(--light-gray); border-radius: 5px;
  font-family: inherit; font-size: 0.68rem; font-weight: 700; margin-right: 4px;
}

/* ════════════════════════════════════════════════════════════
   FLOATING HELP / CONTACT WIDGET
   ════════════════════════════════════════════════════════════ */
#float-widget {
  position: fixed; bottom: 88px; right: 28px; z-index: 890;
  display: flex; flex-direction: column; align-items: flex-end; gap: 10px;
}
#float-widget-btn {
  width: 52px; height: 52px; border-radius: 50%;
  background: linear-gradient(135deg, #25D366, #128C7E);
  color: white; border: none; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.4rem; box-shadow: 0 8px 28px rgba(37,211,102,0.45);
  transition: all 0.3s cubic-bezier(0.4,0,0.2,1);
  animation: floatWiggle 4s ease-in-out infinite;
}
@keyframes floatWiggle {
  0%,100% { transform: translateY(0) rotate(0deg); }
  25% { transform: translateY(-4px) rotate(-5deg); }
  75% { transform: translateY(-2px) rotate(5deg); }
}
#float-widget-btn:hover { transform: scale(1.12); box-shadow: 0 12px 40px rgba(37,211,102,0.6); }
#float-widget-menu {
  background: white; border-radius: 16px; padding: 8px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.2);
  min-width: 200px; display: none; flex-direction: column; gap: 4px;
  animation: menuFade 0.2s ease;
  border: 1px solid var(--mid-gray);
}
[data-theme="dark"] #float-widget-menu { background: #1e2538; border-color: #2a3148; }
#float-widget-menu.open { display: flex; }
@keyframes menuFade { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:none; } }
.fw-item {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px; border-radius: 10px; cursor: pointer;
  font-size: 0.85rem; font-weight: 600; color: var(--text-dark);
  text-decoration: none; transition: background 0.15s;
}
.fw-item:hover { background: var(--light-gray); }
[data-theme="dark"] .fw-item:hover { background: rgba(255,255,255,0.06); }
.fw-item .fw-icon {
  width: 32px; height: 32px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center; font-size: 1rem;
}

/* ════════════════════════════════════════════════════════════
   INTERACTIVE MAP (Leaflet) CONTAINER
   ════════════════════════════════════════════════════════════ */
#leaflet-map {
  height: 380px; border-radius: var(--radius-xl);
  overflow: hidden; box-shadow: var(--shadow-lg);
  border: 3px solid white; margin-top: 64px;
  position: relative; z-index: 1;
}
"""

# ── Floating Widget HTML ──────────────────────────────────────
FLOAT_WIDGET = '''
<!-- Floating Help Widget -->
<div id="float-widget">
  <div id="float-widget-menu">
    <div style="padding:10px 14px 6px;font-size:0.72rem;font-weight:700;color:var(--text-light);letter-spacing:1px;text-transform:uppercase;">Quick Links</div>
    <a class="fw-item" href="enrollment.html"><div class="fw-icon" style="background:rgba(192,57,43,0.1);color:var(--red);">📝</div>Enroll as Cadet</a>
    <a class="fw-item" href="notices.html"><div class="fw-icon" style="background:rgba(13,43,94,0.08);color:var(--navy);">📋</div>Latest Notices</a>
    <a class="fw-item" href="contact.html"><div class="fw-icon" style="background:rgba(52,152,219,0.1);color:var(--sky);">📞</div>Contact ANO</a>
    <a class="fw-item" href="login.html"><div class="fw-icon" style="background:rgba(39,174,96,0.1);color:#27ae60;">🔐</div>Cadet Login</a>
  </div>
  <button id="float-widget-btn" title="Quick Links" onclick="(function(){var m=document.getElementById('float-widget-menu');m.classList.toggle('open');})()">💬</button>
</div>
'''

# ── Scripts to inject before </body> ─────────────────────────
NEW_SCRIPTS = '''
<link rel="manifest" href="../manifest.json">
<script src="../js/dark-mode.js" defer></script>
<script src="../js/search-modal.js" defer></script>
'''
NEW_SCRIPTS_INDEX = '''
<link rel="manifest" href="manifest.json">
<script src="js/dark-mode.js" defer></script>
<script src="js/search-modal.js" defer></script>
'''

def process(path, is_index=False):
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        html = f.read()
    orig = html

    # Inject manifest + scripts into <head>
    tag = NEW_SCRIPTS_INDEX if is_index else NEW_SCRIPTS
    if 'dark-mode.js' not in html:
        html = html.replace('</head>', tag + '</head>', 1)

    # Inject floating widget before </body>
    if 'float-widget' not in html and 'admin-dashboard' not in path and 'admin-login' not in path:
        insert = FLOAT_WIDGET
        if is_index:
            insert = insert.replace('href="enrollment.html"', 'href="pages/enrollment.html"')
            insert = insert.replace('href="notices.html"', 'href="pages/notices.html"')
            insert = insert.replace('href="contact.html"', 'href="pages/contact.html"')
            insert = insert.replace('href="login.html"', 'href="pages/login.html"')
        html = html.replace('</body>', insert + '\n</body>', 1)

    if html != orig:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f'  ✅ {os.path.basename(path)}')
    else:
        print(f'  ⚠  {os.path.basename(path)} – no change')

# Append advanced CSS to style.css
CSS_FILE = r"e:\Major NCC Website\frontend\css\style.css"
with open(CSS_FILE, 'r', encoding='utf-8') as f:
    css = f.read()
if 'DARK MODE THEME' not in css:
    with open(CSS_FILE, 'a', encoding='utf-8') as f:
        f.write(ADVANCED_CSS)
    print("✅ Advanced CSS appended to style.css")
else:
    print("⚠  CSS already patched")

# Upgrade contact page map
CONTACT = r"e:\Major NCC Website\frontend\pages\contact.html"
with open(CONTACT, 'r', encoding='utf-8') as f:
    ch = f.read()
if 'leaflet-map' not in ch:
    LEAFLET_HEAD = '''
  <!-- Leaflet Map -->
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>'''
    LEAFLET_MAP = '''
    <!-- Interactive Map -->
    <div id="leaflet-map" data-aos="fade-up"></div>
    <script>
    window.addEventListener('load', function() {
      var map = L.map('leaflet-map', {scrollWheelZoom: false}).setView([31.6862, 76.5218], 15);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© <a href="https://openstreetmap.org">OpenStreetMap</a>'
      }).addTo(map);
      var icon = L.divIcon({
        html: '<div style="background:#c0392b;width:40px;height:40px;border-radius:50% 50% 50% 0;transform:rotate(-45deg);border:4px solid white;box-shadow:0 4px 20px rgba(192,57,43,0.5);"></div>',
        iconSize: [40,40], iconAnchor: [20,40]
      });
      L.marker([31.6862, 76.5218], {icon: icon})
        .addTo(map)
        .bindPopup('<b>NCC Unit</b><br>Govt. Polytechnic Hamirpur (HP)<br><small>Hamirpur – 177001</small>')
        .openPopup();
    });
    </script>'''
    ch = ch.replace('<link rel="stylesheet" href="../css/style.css" />', LEAFLET_HEAD + '\n  <link rel="stylesheet" href="../css/style.css" />', 1)
    # Replace map placeholder with real map
    if 'map-placeholder' in ch:
        import re as _re
        ch = _re.sub(r'<div class="map-placeholder"[^>]*>.*?</div>', LEAFLET_MAP, ch, flags=_re.DOTALL, count=1)
    else:
        ch = ch.replace('</section>\n\n<footer', LEAFLET_MAP + '\n</section>\n\n<footer', 1)
    with open(CONTACT, 'w', encoding='utf-8') as f:
        f.write(ch)
    print("✅ Contact page upgraded with real Leaflet map")

# Process all pages
print("\n🔧 Injecting dark-mode + search modal + floating widget...")
for fname in os.listdir(PAGES_DIR):
    if fname.endswith('.html'):
        process(os.path.join(PAGES_DIR, fname))
process(FINDEX, is_index=True)
print("\n✅ All done!")
