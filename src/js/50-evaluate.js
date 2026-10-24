/* 免費出租評估表單 /evaluate/ → Google Apps Script（試算表＋Email 通知） */
(function () {
  'use strict';
  var form = document.getElementById('eval-form');
  if (!form) return;
  var $ = window.REVO.$, $$ = window.REVO.$$;
  var LINE_OWNER = '{{LINE_OWNER}}';
  var TS_KEY = '{{TURNSTILE_SITEKEY}}';
  var done = document.getElementById('eval-done');
  var alertBox = document.getElementById('eval-alert');
  var btn = $('.eval-btn', form);
  var btnText = btn.textContent;

  /* ---------- 防機器人（Cloudflare Turnstile）----------
   * site.config.json 的 turnstile_sitekey 有填才啟用；空白就維持原本只靠隱藏欄位。
   * 驗證碼一次有效，每次送出後都要 reset 換新的。 */
  var tsWidget = null, tsFailed = false;
  if (TS_KEY) {
    var tsBox = document.getElementById('eval-turnstile');
    window.revoTurnstileReady = function () {
      tsBox.hidden = false;
      tsWidget = window.turnstile.render(tsBox, { sitekey: TS_KEY, language: 'zh-tw', size: 'flexible' });
    };
    var tsScript = document.createElement('script');
    tsScript.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit&onload=revoTurnstileReady';
    tsScript.async = true;
    // 載不到（網路或擋廣告）就不卡住送出，交給後端判斷；驗證不過會顯示 LINE 備援
    tsScript.onerror = function () { tsFailed = true; };
    document.head.appendChild(tsScript);
  }
  function tsToken() { return tsWidget !== null && window.turnstile ? window.turnstile.getResponse(tsWidget) || '' : ''; }
  function tsReset() { if (tsWidget !== null && window.turnstile) window.turnstile.reset(tsWidget); }

  /* ---------- 選項按鈕 ---------- */
  $$('[data-chips]', form).forEach(function (group) {
    var multi = group.hasAttribute('data-multi');
    $$('.chip', group).forEach(function (chip) {
      chip.addEventListener('click', function () {
        var on = chip.getAttribute('aria-pressed') === 'true';
        if (!multi) $$('.chip', group).forEach(function (c) { c.setAttribute('aria-pressed', 'false'); });
        chip.setAttribute('aria-pressed', multi && on ? 'false' : 'true');
        clearError(group.getAttribute('data-chips'));
      });
    });
  });
  function chipValue(name) {
    return $$('[data-chips="' + name + '"] .chip[aria-pressed="true"]', form)
      .map(function (c) { return c.textContent.trim(); }).join('、');
  }

  /* ---------- 檢查 ---------- */
  var MSG = {
    district: '請選擇房子所在的行政區。',
    size: '請填寫大約的坪數（數字）。',
    age: '請選擇屋齡。',
    rooms: '請選擇格局。',
    status: '請選擇房子目前的狀態。',
    name: '請填寫怎麼稱呼你。',
    phone: '請填寫手機號碼。',
    phoneFormat: '手機號碼請填 09 開頭的 10 碼數字，例如 0912-345-678。',
    consent: '請勾選同意隱私權政策，我們才能使用這些資料與你聯繫。'
  };
  function field(name) { return $('[data-field="' + name + '"]', form); }
  function control(name) {
    var f = field(name);
    return f && ($('input, select, textarea', f) || $('.chip', f));
  }
  function setError(name, msg) {
    var f = field(name), err = document.getElementById('err-' + name);
    if (!f || !err) return;
    f.classList.add('is-invalid');
    err.textContent = msg;
    err.hidden = false;
    var c = $('input, select, textarea', f);
    if (c) c.setAttribute('aria-invalid', 'true');
    var g = $('[data-chips]', f);
    if (g) g.setAttribute('aria-invalid', 'true');
  }
  function clearError(name) {
    var f = field(name), err = document.getElementById('err-' + name);
    if (!f || !f.classList.contains('is-invalid')) return;
    f.classList.remove('is-invalid');
    if (err) { err.hidden = true; err.textContent = ''; }
    $$('[aria-invalid]', f).forEach(function (el) { el.removeAttribute('aria-invalid'); });
  }
  ['district', 'size', 'name', 'phone', 'consent'].forEach(function (name) {
    var c = control(name);
    c.addEventListener(c.tagName === 'SELECT' || c.type === 'checkbox' ? 'change' : 'input', function () { clearError(name); });
  });

  function digits(v) { return String(v || '').replace(/\D/g, ''); }

  function collect() {
    var el = form.elements;
    return {
      district: el['district'].value,
      community: el['community'].value.trim(),
      size: el['size'].value.trim(),
      age: chipValue('age'),
      rooms: chipValue('rooms'),
      status: chipValue('status'),
      plans: chipValue('plans'),
      name: el['name'].value.trim(),
      phone: digits(el['phone'].value),
      line: el['line'].value.trim(),
      times: chipValue('times'),
      note: el['note'].value.trim(),
      consent: el['consent'].checked ? 'yes' : '',
      page: location.pathname,
      website: el['website'].value,
      turnstile: tsToken()
    };
  }

  function validate(d) {
    var bad = [];
    if (!d.district) bad.push(['district', MSG.district]);
    if (!d.size || !(parseFloat(d.size) > 0)) bad.push(['size', MSG.size]);
    ['age', 'rooms', 'status'].forEach(function (k) { if (!d[k]) bad.push([k, MSG[k]]); });
    if (!d.name) bad.push(['name', MSG.name]);
    if (!d.phone) bad.push(['phone', MSG.phone]);
    else if (!/^09\d{8}$/.test(d.phone)) bad.push(['phone', MSG.phoneFormat]);
    if (!d.consent) bad.push(['consent', MSG.consent]);
    return bad;
  }

  function showAlert(html) { alertBox.innerHTML = html; alertBox.hidden = false; }
  function hideAlert() { alertBox.hidden = true; alertBox.innerHTML = ''; }
  var LINE_LINK = '<a href="' + LINE_OWNER + '" target="_blank" rel="noopener">加 REVO LINE</a>';
  var FAIL = '目前無法送出，可能是網路不穩。請稍後再試一次，或直接' + LINE_LINK + '、來電 <a href="tel:+886983144528">0983-144-528</a>。';

  function setSending(on) {
    btn.disabled = on;
    btn.textContent = on ? '送出中…' : btnText;
    form.setAttribute('aria-busy', on ? 'true' : 'false');
  }

  function showDone() {
    form.hidden = true;
    done.hidden = false;
    var card = done.closest('.eval-card') || done;
    var top = card.getBoundingClientRect().top + window.pageYOffset - (parseInt(getComputedStyle(document.documentElement).scrollPaddingTop, 10) || 80);
    window.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });
    var h = $('.eval-done-title', done);
    if (h) h.focus({ preventScroll: true });
  }

  /* ---------- 送出 ----------
   * 作法：一般 POST（application/x-www-form-urlencoded，不加自訂標頭 → 不觸發 CORS 預檢）。
   * Apps Script 會 302 轉到 script.googleusercontent.com，該回應帶 Access-Control-Allow-Origin: *，
   * 所以正常情況可以讀到 {ok:true} 或 {ok:false,error}。
   * 萬一瀏覽器擋下讀取（fetch 丟 TypeError，但請求其實可能已送達），改用 mode:'no-cors' 再送一次：
   * 後端同一支手機 60 秒內只收一筆（CacheService），所以重送不會產生重複資料；
   * no-cors 只要沒有網路錯誤就代表 Google 已收到，視為成功。兩次都失敗才顯示錯誤與 LINE 備援。 */
  function post(params, mode) {
    var opts = { method: 'POST', body: params, redirect: 'follow', credentials: 'omit' };
    if (mode) opts.mode = mode;
    var ctrl = window.AbortController ? new AbortController() : null;
    var timer;
    if (ctrl) { opts.signal = ctrl.signal; timer = setTimeout(function () { ctrl.abort(); }, 25000); }
    return fetch(form.action, opts).finally(function () { clearTimeout(timer); });
  }

  var sending = false;
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    if (sending) return;
    hideAlert();
    var d = collect();
    ['district', 'size', 'age', 'rooms', 'status', 'name', 'phone', 'consent'].forEach(clearError);
    var bad = validate(d);
    if (bad.length) {
      bad.forEach(function (b) { setError(b[0], b[1]); });
      var first = control(bad[0][0]);
      if (first) {
        first.focus({ preventScroll: true });
        field(bad[0][0]).scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
      return;
    }

    if (TS_KEY && !d.turnstile && !tsFailed) {
      showAlert('正在確認你不是機器人，請稍候幾秒再按一次送出。');
      return;
    }

    var params = new URLSearchParams();
    Object.keys(d).forEach(function (k) { params.append(k, d[k]); });
    sending = true;
    setSending(true);

    post(params)
      .then(function (res) {
        return res.text().then(function (t) {
          try { return JSON.parse(t); } catch (err) { return { ok: false, error: 'server' }; }
        });
      }, function (err) {
        if (err && err.name === 'AbortError') throw err;
        // 讀不到回應（多半是 CORS）→ 以 no-cors 重送
        return post(params, 'no-cors').then(function () { return { ok: true, opaque: true }; });
      })
      .then(function (r) {
        if (r && r.ok) { showDone(); return; }
        var code = r && r.error;
        if (code === 'phone') { setError('phone', MSG.phoneFormat); control('phone').focus(); }
        else if (code === 'district') { setError('district', MSG.district); control('district').focus(); }
        else if (code === 'missing') { showAlert('有必填欄位沒有填到，請檢查後再送出。'); }
        else if (code === 'verify') { showAlert('驗證沒有通過，請重新整理頁面後再試一次，或直接' + LINE_LINK + '。'); }
        else { showAlert(FAIL); }
      })
      .catch(function () { showAlert(FAIL); })
      .then(function () { sending = false; setSending(false); tsReset(); });
  });
})();
