/**
 * pro-effects.js – Advanced site-wide interaction library
 * NCC Unit, Govt. Polytechnic Hamirpur (HP)
 */

/* ══════════════════════════════════════════════════════════
   1. SCROLL PROGRESS BAR
   ══════════════════════════════════════════════════════════ */
(function initScrollProgress() {
  let bar = document.getElementById('scroll-progress');
  if (!bar) {
    bar = document.createElement('div');
    bar.id = 'scroll-progress';
    document.body.prepend(bar);
  }
  window.addEventListener('scroll', () => {
    const pct = (window.scrollY / (document.body.scrollHeight - window.innerHeight)) * 100;
    bar.style.width = Math.min(pct, 100) + '%';
  }, { passive: true });
})();

/* ══════════════════════════════════════════════════════════
   2. CUSTOM CURSOR
   ══════════════════════════════════════════════════════════ */
(function initCursor() {
  if (window.matchMedia('(pointer:coarse)').matches) return;
  let dot = document.getElementById('cursor-dot');
  let ring = document.getElementById('cursor-ring');
  if (!dot) {
    dot = document.createElement('div'); dot.id = 'cursor-dot'; document.body.append(dot);
    ring = document.createElement('div'); ring.id = 'cursor-ring'; document.body.append(ring);
  }
  document.addEventListener('mousemove', e => {
    dot.style.left = ring.style.left = e.clientX + 'px';
    dot.style.top  = ring.style.top  = e.clientY + 'px';
  });
  document.querySelectorAll('a,button,.btn,.card,.stat-card,.stat-card-dark,.activity-card-pro,.timeline-card,.obj-card').forEach(el => {
    el.addEventListener('mouseenter', () => document.body.classList.add('cursor-hover'));
    el.addEventListener('mouseleave', () => document.body.classList.remove('cursor-hover'));
  });
})();

/* ══════════════════════════════════════════════════════════
   3. COUNTER-UP ANIMATION
   ══════════════════════════════════════════════════════════ */
(function initCounters() {
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      entry.target.querySelectorAll('[data-count]').forEach(el => {
        const target = parseInt(el.dataset.count);
        const suffix = el.dataset.suffix || '';
        let current = 0;
        const step = Math.max(1, Math.ceil(target / 80));
        const timer = setInterval(() => {
          current = Math.min(current + step, target);
          el.textContent = current.toLocaleString() + suffix;
          if (current >= target) clearInterval(timer);
        }, 16);
      });
      observer.unobserve(entry.target);
    });
  }, { threshold: 0.3 });
  document.querySelectorAll('.stats-section,.stats-dark-section,.stat-card,.stat-card-dark').forEach(el => observer.observe(el));
})();

/* ══════════════════════════════════════════════════════════
   4. STAGGERED REVEAL ON SCROLL
   ══════════════════════════════════════════════════════════ */
(function initReveal() {
  const style = document.createElement('style');
  style.textContent = `
    .will-reveal { opacity:0; transform:translateY(30px); transition:opacity 0.65s ease, transform 0.65s ease; }
    .will-reveal.revealed { opacity:1; transform:none; }
  `;
  document.head.append(style);
  const observer = new IntersectionObserver(entries => {
    entries.forEach((entry, i) => {
      if (entry.isIntersecting) {
        setTimeout(() => entry.target.classList.add('revealed'), entry.target.dataset.delay || 0);
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12 });
  document.querySelectorAll('.card,.obj-card,.activity-card-pro,.timeline-card,.stat-card-dark').forEach((el, i) => {
    el.classList.add('will-reveal');
    el.dataset.delay = (i % 4) * 100;
    observer.observe(el);
  });
})();

/* ══════════════════════════════════════════════════════════
   5. TOAST NOTIFICATION SYSTEM
   ══════════════════════════════════════════════════════════ */
window.Toast = {
  container: null,
  init() {
    if (this.container) return;
    this.container = document.createElement('div');
    this.container.id = 'toast-container';
    this.container.style.cssText = `
      position:fixed; bottom:24px; right:24px; z-index:99999;
      display:flex; flex-direction:column; gap:12px; pointer-events:none;
    `;
    document.body.append(this.container);
  },
  show(message, type = 'info', duration = 3500) {
    this.init();
    const colors = { success:'#27ae60', error:'#c0392b', info:'#3498db', warning:'#f39c12' };
    const icons  = { success:'✔', error:'✖', info:'ℹ', warning:'⚠' };
    const t = document.createElement('div');
    t.style.cssText = `
      background:white; border-left:4px solid ${colors[type]};
      border-radius:12px; padding:14px 20px 14px 16px;
      box-shadow:0 8px 32px rgba(0,0,0,0.15); display:flex; gap:12px;
      align-items:center; min-width:260px; max-width:360px;
      pointer-events:auto; transform:translateX(120%);
      transition:transform 0.4s cubic-bezier(0.4,0,0.2,1), opacity 0.4s;
      font-family:'Poppins',sans-serif; font-size:0.88rem; color:#2d3748;
    `;
    t.innerHTML = `<span style="font-size:1.1rem;color:${colors[type]}">${icons[type]}</span><span>${message}</span>`;
    this.container.append(t);
    requestAnimationFrame(() => { t.style.transform = 'translateX(0)'; });
    setTimeout(() => {
      t.style.opacity = '0'; t.style.transform = 'translateX(120%)';
      setTimeout(() => t.remove(), 420);
    }, duration);
  }
};

/* ══════════════════════════════════════════════════════════
   6. SMOOTH PAGE TRANSITIONS
   ══════════════════════════════════════════════════════════ */
(function initPageTransitions() {
  const overlay = document.createElement('div');
  overlay.id = 'page-transition-overlay';
  overlay.style.cssText = `
    position:fixed; inset:0; background:var(--navy); z-index:99990;
    pointer-events:none; opacity:0; transition:opacity 0.4s ease;
  `;
  document.body.append(overlay);
  // Fade in on load
  window.addEventListener('load', () => setTimeout(() => overlay.style.opacity = '0', 100));
  document.querySelectorAll('a[href]:not([target="_blank"]):not([href^="#"]):not([href^="mailto"]):not([href^="tel"])').forEach(link => {
    link.addEventListener('click', e => {
      const href = link.getAttribute('href');
      if (!href || href.startsWith('javascript') || href.startsWith('/api')) return;
      e.preventDefault();
      overlay.style.pointerEvents = 'all';
      overlay.style.opacity = '1';
      setTimeout(() => { window.location.href = href; }, 400);
    });
  });
})();

/* ══════════════════════════════════════════════════════════
   7. TILT 3D CARD EFFECT
   ══════════════════════════════════════════════════════════ */
(function init3DTilt() {
  document.querySelectorAll('.tilt-card').forEach(card => {
    card.addEventListener('mousemove', e => {
      const rect = card.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width - 0.5) * 18;
      const y = ((e.clientY - rect.top) / rect.height - 0.5) * -18;
      card.style.transform = `perspective(800px) rotateX(${y}deg) rotateY(${x}deg) scale3d(1.03,1.03,1.03)`;
      card.style.transition = 'transform 0.1s ease';
    });
    card.addEventListener('mouseleave', () => {
      card.style.transform = '';
      card.style.transition = 'transform 0.5s ease';
    });
  });
})();

/* ══════════════════════════════════════════════════════════
   8. MAGNETIC BUTTONS
   ══════════════════════════════════════════════════════════ */
(function initMagneticBtns() {
  document.querySelectorAll('.btn,.btn-nav-enroll').forEach(btn => {
    btn.addEventListener('mousemove', e => {
      const rect = btn.getBoundingClientRect();
      const dx = (e.clientX - rect.left - rect.width/2) * 0.25;
      const dy = (e.clientY - rect.top  - rect.height/2) * 0.25;
      btn.style.transform = `translate(${dx}px, ${dy}px)`;
    });
    btn.addEventListener('mouseleave', () => { btn.style.transform = ''; });
  });
})();

/* ══════════════════════════════════════════════════════════
   9. KEYBOARD SHORTCUTS
   ══════════════════════════════════════════════════════════ */
document.addEventListener('keydown', e => {
  if (e.altKey && e.key === 'h') { window.location.href = '/'; }
  if (e.altKey && e.key === 'e') { const l = document.querySelector('[href*="enrollment"]'); if(l) l.click(); }
});

/* ══════════════════════════════════════════════════════════
   10. RIPPLE ON BUTTONS
   ══════════════════════════════════════════════════════════ */
document.querySelectorAll('.btn').forEach(btn => {
  btn.addEventListener('click', function(e) {
    const ripple = document.createElement('span');
    ripple.className = 'ripple';
    const r = this.getBoundingClientRect();
    const size = Math.max(r.width, r.height);
    ripple.style.cssText = `width:${size}px;height:${size}px;left:${e.clientX-r.left-size/2}px;top:${e.clientY-r.top-size/2}px;`;
    this.append(ripple);
    setTimeout(() => ripple.remove(), 700);
  });
});

console.log('%c⚡ NCC Pro Effects Loaded', 'background:#0d2b5e;color:#f0b429;padding:8px 16px;border-radius:8px;font-weight:700;font-size:14px;');
