/* 屋主服務：手機版「三問」點了切到比較卡片的對應方案 */
(function () {
  'use strict';
  var tabs = document.querySelector('[data-plan-tabs]');
  if (!tabs || !window.REVO) return;
  var mobile = window.matchMedia('(max-width: 899px)');
  window.REVO.$$('[data-plan]').forEach(function (a) {
    a.addEventListener('click', function (e) {
      if (!mobile.matches || !tabs.revoShow) return;
      e.preventDefault();
      tabs.revoShow(a.getAttribute('data-plan'));
      var target = document.getElementById('compare');
      if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });
})();
