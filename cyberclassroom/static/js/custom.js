/* ═══════════════════════════════════════════════════════════
   Cyber Classroom RU — custom.js  v2.0
   ลูกเล่น UI ทั้งหมด (ไม่กระทบ backend / Django)
   ═══════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  /* ─────────────────────────────────────────
     ① Dark Mode Toggle
  ───────────────────────────────────────── */
  function initDarkMode() {
    // Light is DEFAULT (no class), dark-mode is the toggle class
    const html   = document.documentElement;
    const toggle = document.getElementById('darkModeToggle');
    if (!toggle) return;

    // Restore saved preference (default: light)
    const saved  = localStorage.getItem('ccru-theme'); // 'dark' or null=light
    const isDark = saved === 'dark';
    if (isDark) { html.classList.add('dark-mode'); }
    toggle.innerHTML = isDark ? '<i class="fas fa-sun"></i>'  : '<i class="fas fa-moon"></i>';
    toggle.title     = isDark ? 'เปลี่ยนเป็น Light Mode'    : 'เปลี่ยนเป็น Dark Mode';

    toggle.addEventListener('click', function () {
      const nowDark = html.classList.toggle('dark-mode');
      localStorage.setItem('ccru-theme', nowDark ? 'dark' : 'light');
      this.innerHTML = nowDark ? '<i class="fas fa-sun"></i>'  : '<i class="fas fa-moon"></i>';
      this.title     = nowDark ? 'เปลี่ยนเป็น Light Mode'    : 'เปลี่ยนเป็น Dark Mode';
      this.style.transform = 'rotate(360deg)';
      setTimeout(() => { this.style.transform = ''; }, 400);
    });
  }

  /* ─────────────────────────────────────────
     ② Ripple Effect on all .btn
  ───────────────────────────────────────── */
  function initRipple() {
    document.addEventListener('click', function (e) {
      const btn = e.target.closest('.btn');
      if (!btn) return;

      const rect   = btn.getBoundingClientRect();
      const size   = Math.max(rect.width, rect.height) * 2;
      const x      = e.clientX - rect.left - size / 2;
      const y      = e.clientY - rect.top  - size / 2;

      const ripple = document.createElement('span');
      ripple.className = 'ripple-wave';
      ripple.style.cssText = `
        width:${size}px; height:${size}px;
        left:${x}px; top:${y}px;
        position:absolute; border-radius:50%;
        background:rgba(255,255,255,0.32);
        transform:scale(0);
        animation: rippleAnim 0.6s linear;
        pointer-events:none;
      `;
      btn.style.position = 'relative';
      btn.style.overflow = 'hidden';
      btn.appendChild(ripple);
      setTimeout(() => ripple.remove(), 650);
    });
  }

  /* ─────────────────────────────────────────
     ③ Scroll Reveal (IntersectionObserver)
  ───────────────────────────────────────── */
  function initScrollReveal() {
    if (!('IntersectionObserver' in window)) return;

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.06, rootMargin: '0px 0px -32px 0px' });

    // Stagger .reveal elements (channel cards, subject cards)
    document.querySelectorAll('.reveal').forEach((el, i) => {
      el.style.transitionDelay = `${(i % 9) * 60}ms`;
      observer.observe(el);
    });
  }

  /* ─────────────────────────────────────────
     ④ Animated Number Counter
     Usage: <span data-count="120">0</span>
  ───────────────────────────────────────── */
  function animateCount(el, target, duration) {
    duration = duration || 1600;
    const start = performance.now();
    function update(now) {
      const t = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - t, 3); // ease-out cubic
      el.textContent = Math.round(eased * target);
      if (t < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
  }

  function initCounters() {
    if (!('IntersectionObserver' in window)) return;
    const counterObs = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const el     = entry.target;
          const target = parseInt(el.getAttribute('data-count'), 10);
          if (!isNaN(target)) animateCount(el, target);
          counterObs.unobserve(el);
        }
      });
    }, { threshold: 0.5 });

    document.querySelectorAll('[data-count]').forEach(el => counterObs.observe(el));
  }

  /* ─────────────────────────────────────────
     ⑤ Back-to-Top Button
  ───────────────────────────────────────── */
  function initBackToTop() {
    const btn = document.getElementById('backToTop');
    if (!btn) return;

    window.addEventListener('scroll', function () {
      btn.classList.toggle('visible', window.scrollY > 320);
    }, { passive: true });

    btn.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  /* ─────────────────────────────────────────
     ⑥ Navbar Compact on Scroll
  ───────────────────────────────────────── */
  function initNavbarScroll() {
    const navbar = document.querySelector('.navbar');
    if (!navbar) return;
    window.addEventListener('scroll', function () {
      navbar.classList.toggle('navbar-scrolled', window.scrollY > 60);
    }, { passive: true });
  }

  /* ─────────────────────────────────────────
     ⑦ Typewriter Effect (hero title)
     Expects: <span id="hero-typewriter"></span>
  ───────────────────────────────────────── */
  function initTypewriter() {
    const el = document.getElementById('hero-typewriter');
    if (!el) return;

    const texts  = ['Cyber Classroom RU', 'ดูสดได้ทุกที่', 'ทุกเวลา ทุกวิชา', 'มหาวิทยาลัยรามคำแหง'];
    let   tIdx   = 0, cIdx = 0, deleting = false, paused = false;

    function type() {
      if (paused) return;
      const current = texts[tIdx];
      if (!deleting) {
        el.textContent = current.slice(0, ++cIdx);
        if (cIdx === current.length) {
          paused = true;
          setTimeout(() => { deleting = true; paused = false; type(); }, 2000);
          return;
        }
        setTimeout(type, 85);
      } else {
        el.textContent = current.slice(0, --cIdx);
        if (cIdx === 0) {
          deleting = false;
          tIdx = (tIdx + 1) % texts.length;
        }
        setTimeout(type, 45);
      }
    }
    type();
  }

  /* ─────────────────────────────────────────
     ⑧ 3D Card Tilt on Mouse Move
  ───────────────────────────────────────── */
  function initCardTilt() {
    // Only on desktop (no touch) and performance check
    if (window.matchMedia('(hover: none)').matches) return;

    const cards = document.querySelectorAll('.col .card');

    cards.forEach(card => {
      card.addEventListener('mousemove', function (e) {
        const rect   = card.getBoundingClientRect();
        const cx     = rect.left + rect.width / 2;
        const cy     = rect.top  + rect.height / 2;
        const dx     = (e.clientX - cx) / (rect.width  / 2);
        const dy     = (e.clientY - cy) / (rect.height / 2);
        const rotX   = -dy * 6;   // max ±6°
        const rotY   =  dx * 6;

        card.style.transform  = `perspective(800px) rotateX(${rotX}deg) rotateY(${rotY}deg) translateY(-6px) scale(1.02)`;
        card.style.transition = 'none';
        card.style.boxShadow  = `${-dx * 8}px ${-dy * 8}px 32px rgba(30,58,138,0.2)`;
      });

      card.addEventListener('mouseleave', function () {
        card.style.transition = 'all 0.45s cubic-bezier(0.4,0,0.2,1)';
        card.style.transform  = '';
        card.style.boxShadow  = '';
      });
    });
  }

  /* ─────────────────────────────────────────
     ⑨ Input Group Focus Ring
  ───────────────────────────────────────── */
  function initInputFocus() {
    document.querySelectorAll('.input-group .form-control').forEach(input => {
      const grp = input.closest('.input-group');
      if (!grp) return;
      input.addEventListener('focus', () => grp.classList.add('focused'));
      input.addEventListener('blur',  () => grp.classList.remove('focused'));
    });
  }

  /* ─────────────────────────────────────────
     ⑩ Smooth page-load fade-in
  ───────────────────────────────────────── */
  function initPageFade() {
    document.body.style.opacity = '0';
    document.body.style.transition = 'opacity 0.45s ease';
    requestAnimationFrame(() => {
      requestAnimationFrame(() => { document.body.style.opacity = '1'; });
    });
  }

  /* ─────────────────────────────────────────
     ⑪ Ripple keyframe injection
     (injected once since we can't use external CSS here)
  ───────────────────────────────────────── */
  function injectKeyframes() {
    if (document.getElementById('ccru-keyframes')) return;
    const style = document.createElement('style');
    style.id = 'ccru-keyframes';
    style.textContent = `
      @keyframes rippleAnim {
        to { transform: scale(4); opacity: 0; }
      }
    `;
    document.head.appendChild(style);
  }

  /* ─────────────────────────────────────────
     Boot
  ───────────────────────────────────────── */
  document.addEventListener('DOMContentLoaded', function () {
    injectKeyframes();
    initPageFade();
    initDarkMode();
    initRipple();
    initScrollReveal();
    initCounters();
    initBackToTop();
    initNavbarScroll();
    initTypewriter();
    initCardTilt();
    initInputFocus();
  });

})();
