/* 作品案例：篩選（全部／經營案例／空間服務）、手機版 BEFORE / AFTER 切換（空間切換用共用的 data-tabs） */
(function () {
  'use strict';
  var R = window.REVO;
  var groups = R.$$('[data-works-group]');
  if (!groups.length) return;

  var filters = R.$('[data-works-filters]');
  var btns = filters ? R.$$('[data-filter]', filters) : [];
  function apply(f) {
    if (f !== 'biz' && f !== 'space') f = 'all';
    btns.forEach(function (x) { x.setAttribute('aria-selected', x.getAttribute('data-filter') === f ? 'true' : 'false'); });
    groups.forEach(function (g) { g.hidden = !(f === 'all' || g.getAttribute('data-kind') === f); });
  }
  btns.forEach(function (b) {
    b.addEventListener('click', function () {
      var f = b.getAttribute('data-filter');
      apply(f);
      if (history.replaceState) history.replaceState(null, '', f === 'all' ? location.pathname : '#' + f);
    });
  });
  // 網址帶 #space／#biz 時直接套用篩選
  function fromHash() { var h = location.hash.slice(1); if (h === 'space' || h === 'biz') apply(h); }
  fromHash();
  window.addEventListener('hashchange', fromHash);

  R.$$('[data-works-case]').forEach(function (c) {
    var sides = R.$$('[data-side]', c).filter(function (b) { return b.tagName === 'BUTTON'; });
    sides.forEach(function (b) {
      b.addEventListener('click', function () {
        var s = b.getAttribute('data-side');
        c.setAttribute('data-side', s);
        sides.forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
      });
    });
  });
})();
