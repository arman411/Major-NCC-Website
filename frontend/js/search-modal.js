/**
 * search-modal.js – Global keyboard search overlay (Ctrl+K)
 */
(function () {
  const PAGES = [
    { title:'Home',              url:'../index.html',     icon:'🏠', desc:'NCC Unit homepage' },
    { title:'About NCC',         url:'about.html',        icon:'📖', desc:'History, aims & pledge' },
    { title:'Our Unit',          url:'unit.html',         icon:'🏛️', desc:'Unit details & staff' },
    { title:'Activities',        url:'activities.html',   icon:'⛺', desc:'Camps & training' },
    { title:'Gallery',           url:'gallery.html',      icon:'🖼️', desc:'Photos & events' },
    { title:'Achievements',      url:'achievements.html', icon:'🏆', desc:'Awards & honours' },
    { title:'Notices',           url:'notices.html',      icon:'📋', desc:'Notice board' },
    { title:'Contact',           url:'contact.html',      icon:'📞', desc:'Get in touch' },
    { title:'Enroll as Cadet',   url:'enrollment.html',   icon:'📝', desc:'Join the NCC unit' },
    { title:'Cadet Login',       url:'login.html',        icon:'🔐', desc:'Cadet dashboard' },
    { title:'Admin Panel',       url:'admin-login.html',  icon:'⚙️', desc:'Admin access' },
    { title:'Republic Day Camp', url:'activities.html',   icon:'🇮🇳', desc:'National parade camp' },
    { title:'NCC Certificate',   url:'about.html',        icon:'🎖️', desc:'A/B/C certificate info' },
  ];

  let selectedIdx = 0, filtered = [];

  function buildModal() {
    if (document.getElementById('search-modal')) return;
    const el = document.createElement('div');
    el.id = 'search-modal';
    el.innerHTML = `
      <div id="search-overlay"></div>
      <div id="search-box">
        <div id="search-input-wrap">
          <i class="fas fa-search" id="search-icon"></i>
          <input id="search-input" type="text" placeholder="Search pages, activities, notices…" autocomplete="off" />
          <kbd id="search-esc">ESC</kbd>
        </div>
        <div id="search-results"></div>
        <div id="search-footer">
          <span><kbd>↑↓</kbd> Navigate</span>
          <span><kbd>↵</kbd> Open</span>
          <span><kbd>Esc</kbd> Close</span>
        </div>
      </div>`;
    document.body.append(el);
    document.getElementById('search-overlay').onclick = close;
    document.getElementById('search-input').addEventListener('input', e => render(e.target.value));
    el.addEventListener('keydown', handleKey);
    render('');
  }

  function highlight(text, q) {
    if (!q) return text;
    return text.replace(new RegExp('(' + q.replace(/[.*+?^${}()|[\]\\]/g,'\\$&') + ')', 'gi'), '<mark style="background:rgba(52,152,219,0.2);color:var(--navy);border-radius:2px;padding:0 2px;">$1</mark>');
  }

  function render(query) {
    var q = query.trim().toLowerCase();
    filtered = q
      ? PAGES.filter(function(p){ return p.title.toLowerCase().includes(q) || p.desc.toLowerCase().includes(q); })
      : PAGES.slice(0, 9);
    selectedIdx = 0;
    var r = document.getElementById('search-results');
    if (!r) return;
    r.innerHTML = filtered.length
      ? filtered.map(function(p, i){ return '<a class="sr-item'+(i===0?' selected':'')+'" href="'+p.url+'" data-idx="'+i+'"><span class="sr-icon">'+p.icon+'</span><span class="sr-body"><span class="sr-title">'+highlight(p.title,q)+'</span><span class="sr-desc">'+p.desc+'</span></span><i class="fas fa-arrow-right sr-arrow"></i></a>'; }).join('')
      : '<div class="sr-empty">No results found</div>';
    r.querySelectorAll('.sr-item').forEach(function(el, i){
      el.addEventListener('mouseenter', function(){ setSelected(i); });
    });
  }

  function setSelected(idx) {
    selectedIdx = idx;
    document.querySelectorAll('.sr-item').forEach(function(el, i){
      el.classList.toggle('selected', i === idx);
    });
    var sel = document.querySelector('.sr-item.selected');
    if (sel) sel.scrollIntoView({ block: 'nearest' });
  }

  function handleKey(e) {
    if (e.key === 'Escape') { close(); return; }
    if (e.key === 'ArrowDown') { setSelected(Math.min(selectedIdx+1, filtered.length-1)); e.preventDefault(); }
    if (e.key === 'ArrowUp')   { setSelected(Math.max(selectedIdx-1, 0)); e.preventDefault(); }
    if (e.key === 'Enter' && filtered[selectedIdx]) { window.location.href = filtered[selectedIdx].url; }
  }

  function open() {
    buildModal();
    document.getElementById('search-modal').classList.add('open');
    setTimeout(function(){ var inp = document.getElementById('search-input'); if(inp) inp.focus(); }, 60);
  }

  function close() {
    var m = document.getElementById('search-modal'); if (m) m.classList.remove('open');
  }

  document.addEventListener('keydown', function(e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') { e.preventDefault(); var m = document.getElementById('search-modal'); if (m && m.classList.contains('open')) close(); else open(); }
  });

  function injectSearchBtn() {
    document.querySelectorAll('.navbar-actions, .topbar-right').forEach(function(container) {
      if (container.querySelector('.search-trigger')) return;
      var btn = document.createElement('button');
      btn.className = 'search-trigger';
      btn.style.cssText = 'width:36px;height:36px;border-radius:8px;background:var(--off-white);border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;color:var(--text-mid);font-size:0.85rem;transition:all 0.2s;flex-shrink:0;';
      btn.innerHTML = '<i class="fas fa-search"></i>';
      btn.title = 'Search (Ctrl+K)';
      btn.setAttribute('data-tooltip','Ctrl+K');
      btn.onclick = open;
      container.prepend(btn);
    });
  }

  if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', injectSearchBtn); } else { injectSearchBtn(); }
  window._searchModal = { open: open, close: close };
})();
