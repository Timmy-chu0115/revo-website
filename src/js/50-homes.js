/* 房源頁：桌機「看全部 10 張照片」展開／收合 */
(function () {
  'use strict';
  var R = window.REVO;
  var btn = R.$('[data-gallery-toggle]');
  if (!btn) return;
  var all = document.getElementById(btn.getAttribute('aria-controls'));
  if (!all) return;
  btn.addEventListener('click', function () {
    var open = all.hidden;
    all.hidden = !open;
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    btn.textContent = open ? '收合照片' : '看全部 10 張照片';
  });
})();
