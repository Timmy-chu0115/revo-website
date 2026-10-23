/* REVO 銳沃 — 共用互動（不需任何套件） */
(function () {
  'use strict';
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  window.REVO = { $: $, $$: $$ };

  /* 手機選單 */
  var menu = $('#site-menu');
  var openBtn = $('[data-menu-open]');
  function setMenu(open) {
    if (!menu) return;
    menu.hidden = !open;
    document.body.classList.toggle('menu-open', open);
    if (openBtn) openBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (open) { var c = $('[data-menu-close]', menu); if (c) c.focus(); } else if (openBtn) openBtn.focus();
  }
  if (openBtn) openBtn.addEventListener('click', function () { setMenu(true); });
  $$('[data-menu-close]').forEach(function (b) { b.addEventListener('click', function () { setMenu(false); }); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && menu && !menu.hidden) setMenu(false); });
  if (menu) $$('a', menu).forEach(function (a) { a.addEventListener('click', function () { setMenu(false); }); });

  /* 頁首捲動底色、手機底部列 */
  var header = $('[data-header]');
  var bar = $('[data-bottombar]');
  var ticking = false;
  function onScroll() {
    var y = window.scrollY || window.pageYOffset;
    if (header) header.classList.toggle('is-scrolled', y > 40);
    if (bar) {
      var footer = $('.site-footer');
      var nearEnd = footer && footer.getBoundingClientRect().top < window.innerHeight - 40;
      bar.classList.toggle('is-shown', y > window.innerHeight * 0.6 && !nearEnd);
    }
    ticking = false;
  }
  window.addEventListener('scroll', function () { if (!ticking) { ticking = true; requestAnimationFrame(onScroll); } }, { passive: true });
  onScroll();

  /* 橫向滑動列的圓點：<div class="swipe" data-swipe="id"> + <div class="dots" data-dots="id"> */
  $$('[data-swipe]').forEach(function (track) {
    var dots = $('[data-dots="' + track.getAttribute('data-swipe') + '"]');
    if (!dots) return;
    var items = Array.prototype.slice.call(track.children);
    dots.innerHTML = items.map(function () { return '<span></span>'; }).join('');
    var spans = Array.prototype.slice.call(dots.children);
    function update() {
      var left = track.scrollLeft, best = 0, bestD = Infinity;
      items.forEach(function (el, i) { var d = Math.abs(el.offsetLeft - track.offsetLeft - left - parseFloat(getComputedStyle(track).paddingLeft || 0)); if (d < bestD) { bestD = d; best = i; } });
      if (track.scrollLeft + track.clientWidth >= track.scrollWidth - 4) best = items.length - 1;
      spans.forEach(function (s, i) { s.classList.toggle('on', i === best); });
    }
    track.addEventListener('scroll', function () { requestAnimationFrame(update); }, { passive: true });
    window.addEventListener('resize', update);
    update();
  });

  /* 通用分頁切換：
     <div data-tabs> <button data-tab="a" aria-selected="true">…</button> …
     <div data-panel="a">…</div> <div data-panel="b" hidden>…</div> </div> */
  $$('[data-tabs]').forEach(function (root) {
    var tabs = $$('[data-tab]', root).filter(function (t) { return t.closest('[data-tabs]') === root; });
    var panels = $$('[data-panel]', root).filter(function (p) { return p.closest('[data-tabs]') === root; });
    function show(id) {
      tabs.forEach(function (t) { t.setAttribute('aria-selected', t.getAttribute('data-tab') === id ? 'true' : 'false'); });
      panels.forEach(function (p) { p.hidden = p.getAttribute('data-panel') !== id; });
    }
    tabs.forEach(function (t) { t.addEventListener('click', function () { show(t.getAttribute('data-tab')); }); });
    root.revoShow = show;
  });
})();
