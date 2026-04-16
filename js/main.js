/* ========================================================
   NCC WEBSITE - Shared JavaScript
   Handles: Loader, Navbar, Back-to-top, Ripple, Tilt, AOS
   ======================================================== */

(function () {
  'use strict';

  /* ── Page Loader ─────────────────────────────────────── */
  window.addEventListener('load', () => {
    const loader = document.getElementById('page-loader');
    if (!loader) return;
    setTimeout(() => {
      loader.classList.add('loaded');
      document.body.style.overflow = '';
    }, 600);
  });
  // Prevent scroll during load
  document.body.style.overflow = 'hidden';

  /* ── Navbar ──────────────────────────────────────────── */
  const navbar  = document.getElementById('navbar');
  const ham     = document.querySelector('.hamburger');
  const mobileNav = document.querySelector('.mobile-nav');

  if (navbar) {
    const onScroll = () => {
      if (window.scrollY > 50) {
        navbar.classList.add('scrolled');
      } else {
        navbar.classList.remove('scrolled');
      }
    };
    window.addEventListener('scroll', onScroll, { passive:true });
    onScroll();
  }

  if (ham && mobileNav) {
    ham.addEventListener('click', () => {
      ham.classList.toggle('open');
      mobileNav.classList.toggle('open');
    });
    // Close on link click
    mobileNav.querySelectorAll('a').forEach(a => {
      a.addEventListener('click', () => {
        ham.classList.remove('open');
        mobileNav.classList.remove('open');
      });
    });
  }

  // Highlight active nav link
  const setActiveLink = () => {
    const current = window.location.pathname.split('/').pop() || 'index.html';
    document.querySelectorAll('.nav-link').forEach(link => {
      const href = link.getAttribute('href');
      if (!href) return;
      const target = href.split('/').pop();
      if (target === current || (current === '' && target === 'index.html')) {
        link.classList.add('active');
      }
    });
  };
  setActiveLink();

  /* ── Back to Top ─────────────────────────────────────── */
  const btt = document.getElementById('back-to-top');
  if (btt) {
    window.addEventListener('scroll', () => {
      if (window.scrollY > 400) {
        btt.classList.add('visible');
      } else {
        btt.classList.remove('visible');
      }
    }, { passive:true });
    btt.addEventListener('click', () => {
      window.scrollTo({ top:0, behavior:'smooth' });
    });
  }

  /* ── Ripple Effect ───────────────────────────────────── */
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('.btn');
    if (!btn) return;
    const ripple = document.createElement('span');
    ripple.classList.add('ripple');
    const rect = btn.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    ripple.style.cssText = `
      width: ${size}px; height: ${size}px;
      left: ${e.clientX - rect.left - size/2}px;
      top: ${e.clientY - rect.top - size/2}px;
    `;
    btn.appendChild(ripple);
    setTimeout(() => ripple.remove(), 700);
  });

  /* ── 3D Tilt Effect ──────────────────────────────────── */
  document.querySelectorAll('.tilt-card').forEach(card => {
    const inner = card.querySelector('.tilt-inner') || card;
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width;
      const y = (e.clientY - rect.top) / rect.height;
      const rotateY = (x - 0.5) * 16;
      const rotateX = (0.5 - y) * 16;
      inner.style.transform = `perspective(800px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(1.03,1.03,1.03)`;
      inner.style.transition = 'transform 0.1s ease';
    });
    card.addEventListener('mouseleave', () => {
      inner.style.transform = 'perspective(800px) rotateX(0deg) rotateY(0deg) scale3d(1,1,1)';
      inner.style.transition = 'transform 0.4s ease';
    });
  });

  /* ── Smooth Scroll for anchors ───────────────────────── */
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', (e) => {
      const target = document.querySelector(a.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior:'smooth', block:'start' });
      }
    });
  });

  /* ── Animated Counters ───────────────────────────────── */
  const counters = document.querySelectorAll('[data-count]');
  if (counters.length > 0) {
    const animateCounter = (el) => {
      const target = parseInt(el.dataset.count);
      const duration = 2000;
      const start = performance.now();
      const step = (now) => {
        const progress = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.floor(eased * target).toLocaleString() + (el.dataset.suffix || '');
        if (progress < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    };
    const obs = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting && !entry.target.dataset.counted) {
          entry.target.dataset.counted = 'true';
          animateCounter(entry.target);
        }
      });
    }, { threshold: 0.5 });
    counters.forEach(c => obs.observe(c));
  }

  /* ── AOS Init ────────────────────────────────────────── */
  if (typeof AOS !== 'undefined') {
    AOS.init({
      duration: 1000,
      once: true,
      easing: 'ease-out-back',
      offset: 80,
    });
  }

  /* ── GSAP Advanced Animations ────────────────────────── */
  if (typeof gsap !== 'undefined' && typeof ScrollTrigger !== 'undefined') {
    gsap.registerPlugin(ScrollTrigger);
    
    // Page Hero entry animations
    if (document.querySelector('.page-hero h1')) {
      gsap.from(".page-hero h1", { y: 50, opacity: 0, duration: 1.2, ease: "back.out(1.5)" });
      gsap.from(".page-hero p", { y: 30, opacity: 0, duration: 1, delay: 0.3, ease: "power3.out" });
    }
    
    // Smooth fade in for section headers
    gsap.utils.toArray('.section-header').forEach(header => {
      gsap.from(header, {
        scrollTrigger: {
          trigger: header,
          start: "top 85%",
          toggleActions: "play none none reverse"
        },
        y: 40,
        opacity: 0,
        duration: 1,
        ease: "power2.out"
      });
    });
    
    // Interactive Parallax
    gsap.utils.toArray('.parallax').forEach(el => {
      const speed = el.dataset.speed || 0.2;
      gsap.to(el, {
        y: (i, target) => -ScrollTrigger.maxScroll(window) * speed,
        ease: "none",
        scrollTrigger: {
          trigger: el,
          start: "top bottom",
          end: "bottom top",
          scrub: 1
        }
      });
    });
  }

})();
