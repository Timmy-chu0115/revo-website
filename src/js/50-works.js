/* 作品案例：篩選、手機版 BEFORE / AFTER 切換（空間切換用共用的 data-tabs） */
(function () {
  'use strict';
  var R = window.REVO;
  var cases = R.$$('[data-works-case]');
  if (!cases.length) return;

  var filters = R.$('[data-works-filters]');
  if (filters) {
    var btns = R.$$('[data-filter]', filters);
    btns.forEach(function (b) {
      b.addEventListener('click', function () {
        var f = b.getAttribute('data-filter');
        btns.forEach(function (x) { x.setAttribute('aria-selected', x === b ? 'true' : 'false'); });
        cases.forEach(function (c) { c.hidden = !(f === 'all' || c.getAttribute('data-type') === f); });
      });
    });
  }

  cases.forEach(function (c) {
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
