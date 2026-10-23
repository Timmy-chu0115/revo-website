/* 精選寓所：REVO 住宅地圖（全區 ↔ 左營／橋頭／萬丹） */
(function () {
  'use strict';
  var R = window.REVO;
  var root = R.$('[data-map]');
  if (!root) return;
  var frame = R.$('.map-frame', root);
  var views = R.$$('[data-map-view]', root);
  var panels = R.$$('[data-map-panel]', root);
  var legends = R.$$('[data-legend]', root);
  var back = R.$('.map-back', root);
  var mobile = window.matchMedia('(max-width: 899px)');
  var current = 'all';

  // 區域地圖檔（SVG）點進去才載入，直接放進頁面才能套用網站字型
  function load(view) {
    R.$$('[data-map-src]', view).forEach(function (box) {
      var visible = box.classList.contains('only-mobile') === mobile.matches;
      if (!visible || box.dataset.loaded) return;
      box.dataset.loaded = '1';
      fetch(box.getAttribute('data-map-src')).then(function (r) {
        if (!r.ok) throw new Error(r.status);
        return r.text();
      }).then(function (svg) {
        box.innerHTML = svg;
      }).catch(function () {
        box.dataset.loaded = '';
      });
    });
  }

  function show(area, focus) {
    current = area;
    views.forEach(function (v) {
      var on = v.getAttribute('data-map-view') === area;
      v.hidden = !on;
      if (on) load(v);
    });
    panels.forEach(function (p) { p.hidden = p.getAttribute('data-map-panel') !== area; });
    legends.forEach(function (l) { l.hidden = l.getAttribute('data-legend').split(' ').indexOf(area) < 0; });
    back.hidden = area === 'all';
    R.$$('.map-chips [data-map-go]', root).forEach(function (b) {
      b.setAttribute('aria-pressed', b.getAttribute('data-map-go') === area ? 'true' : 'false');
    });
    if (focus) {
      var top = frame.getBoundingClientRect().top;
      var head = document.querySelector('.site-header');
      var offset = (head ? head.offsetHeight : 0) + (mobile.matches ? 64 : 24);
      if (top < offset || top > window.innerHeight * 0.6) {
        window.scrollTo({ top: window.scrollY + top - offset, behavior: 'smooth' });
      }
    }
  }

  root.addEventListener('click', function (e) {
    var b = e.target.closest('[data-map-go]');
    if (!b || !root.contains(b)) return;
    var area = b.getAttribute('data-map-go');
    // 從右側卡片或清單上的按鈕切換時，把地圖捲回畫面內
    var fromList = !!b.closest('.map-side');
    show(area, fromList || (mobile.matches && !b.closest('.map-chips')));
  });

  var onChange = function () { views.forEach(function (v) { if (!v.hidden) load(v); }); };
  if (mobile.addEventListener) mobile.addEventListener('change', onChange);
  else if (mobile.addListener) mobile.addListener(onChange);

  root.classList.add('is-ready');
  show('all', false);
})();
