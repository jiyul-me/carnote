/* 차일지 — 자동차세 연납 신청 기간 안내 줄 (차종·허브·계산기 페이지의 .prepay-banner).
 * 신청 기간·공제율·예고 일수는 scripts/build.py가 data/tax-rates.json에서 읽어 data-* 속성으로 심는다 — 여기 하드코딩 금지.
 * 날짜 판단만 브라우저의 오늘 날짜로 한다. 기간 밖이거나 JS가 꺼져 있으면 hidden 그대로(아무것도 안 보임).
 * state·copy는 DOM 비의존 순수 함수 — jsc 테스트 가능 (tests/prepay-banner.test.js). */
(function (global) {
  'use strict';

  var DAY_MS = 86400000;

  // 달력 날짜 → 일 번호. UTC로 세서 서머타임·시각과 무관하게 날짜 차이만 센다
  function dayNum(y, m, d) { return Math.round(Date.UTC(y, m - 1, d) / DAY_MS); }

  // 6월 일괄부과 차량(본세 10만원 이하)은 6·9월 연납이 없다 — lumpSumEligible=false 기간을 뺀다
  function eligible(windows, lumpSum) {
    if (!lumpSum) return windows;
    var out = [];
    for (var i = 0; i < windows.length; i++) if (windows[i].lumpSumEligible !== false) out.push(windows[i]);
    return out;
  }

  // windows: [{month, startDay, endDay, coveredMonths, label, bannerLeadDays}], today: {y, m, d}
  // defaultLead: 기간에 bannerLeadDays가 없을 때 쓰는 예고 일수
  // 반환: null(숨김) | {kind: 'open'|'soon', window, year(그 기간의 연도), days}
  //   open = 신청 기간 중 (days = 마감까지 남은 날)
  //   soon = 시작까지 그 기간의 예고 일수(bannerLeadDays) 이내 (days = 시작까지 남은 날). 여러 개면 가장 가까운 것
  function state(windows, today, defaultLead) {
    var t = dayNum(today.y, today.m, today.d);
    var next = null;
    for (var dy = 0; dy <= 1; dy++) { // 연말에는 다음 해 1월 기간을 본다
      var y = today.y + dy;
      for (var i = 0; i < windows.length; i++) {
        var w = windows[i];
        var s = dayNum(y, w.month, w.startDay);
        var e = dayNum(y, w.month, w.endDay);
        if (t >= s && t <= e) return { kind: 'open', window: w, year: y, days: e - t };
        var lead = w.bannerLeadDays != null ? w.bannerLeadDays : (defaultLead || 0);
        if (s > t && s - t <= lead && (!next || s < next.s)) next = { s: s, w: w, y: y };
      }
    }
    return next ? { kind: 'soon', window: next.w, year: next.y, days: next.s - t } : null;
  }

  // 공제율 선택 — tax-rates.json fallbackRule (tax-calc.js rateFor·build.py prepay_rate와 같은 규칙):
  // 그 해 키가 없으면 가장 최근 연도의 공제율 + 'YYYY년 기준' 표기 강제
  function rateFor(rateByYear, year) {
    var key = String(year);
    if (rateByYear[key] != null) return { year: key, rate: rateByYear[key], fallback: false };
    var years = Object.keys(rateByYear).sort();
    var latest = years[years.length - 1];
    return { year: latest, rate: rateByYear[latest], fallback: true };
  }

  function pct(rate) { return Math.round(rate * 1000) / 10 + '%'; }

  // 상태별 문구. hasAmount = 이 페이지에 '1월 연납 시' 금액이 보이는지 (차종·계산기 true, 허브 false)
  // opts.amountYear = 페이지 금액의 기준 연도(빌드 연도), opts.ageBased = 그 금액이 차령에 따라 달라지는지
  // 페이지 금액은 늘 1월 연납 기준이라, 1월이 아닌 기간에는 할인이 그보다 적다는 걸 밝힌다.
  // 안내하는 1월이 페이지 금액의 기준 연도가 아니면(11~12월의 다음 해 예고, 해가 바뀐 뒤 아직 다시 빌드 전)
  // '이 금액으로 낼 수 있다'고 하지 않는다 — 그 해엔 차령이 늘어 금액이 달라질 수 있다
  function copy(st, rateByYear, hasAmount, opts) {
    opts = opts || {};
    var w = st.window;
    var r = rateFor(rateByYear, st.year);
    var from = 12 - w.coveredMonths + 1; // 신청 다음 달 ~ 12월
    var isJan = w.month === 1; // 페이지 금액(januaryProration)과 같은 기간
    var amountYear = opts.amountYear || null;
    var main = st.kind === 'open'
      ? '지금 신청 기간이에요 · ' + w.month + '월 ' + w.endDay + '일까지'
      : '신청 시작까지 D-' + st.days + ' · ' + w.month + '월 ' + w.startDay + '일부터';
    // 그 해 공제율이 아직 데이터에 없으면 어느 해 기준인지 반드시 밝힌다
    var rateText = pct(r.rate) + (r.fallback ? '(' + r.year + '년 공제율 기준)' : '');
    var note;
    if (isJan) {
      note = from + '~12월분 세액의 ' + rateText + '를 공제받아요';
      if (!hasAmount) {
        note += '.';
      } else if (!amountYear || amountYear === st.year) {
        note += ' — 이 페이지의 ‘1월 연납 시’ 금액으로 낼 수 있어요.';
      } else if (opts.ageBased && st.year > amountYear) {
        note += '. 이 페이지 금액은 ' + amountYear + '년 기준이라, ' + st.year + '년 1월엔 차령이 ' +
          (st.year - amountYear) + '년 늘어 금액이 달라질 수 있어요.';
      } else {
        note += '. 이 페이지 금액은 ' + amountYear + '년 기준이에요.';
      }
    } else {
      note = from + '~12월분만 ' + rateText + ' 공제돼 ' +
        (hasAmount ? '이 페이지의 ‘1월 연납 시’ 금액보다' : '1월 연납보다') + ' 할인이 적어요.';
    }
    return {
      badge: w.label,
      main: main,
      dday: st.kind === 'soon' ? 'D-' + st.days : null,
      ddayWarn: st.kind === 'soon' && st.days <= 14, // DESIGN: D-14 이하 임박 배지
      note: note,
      showApply: st.kind === 'open'
    };
  }

  var api = { state: state, rateFor: rateFor, copy: copy, eligible: eligible };
  global.ChailjiPrepayBanner = api;

  if (typeof document === 'undefined') return;

  function todayParts() {
    var now = new Date();
    return { y: now.getFullYear(), m: now.getMonth() + 1, d: now.getDate() };
  }

  function render(el, today) {
    var windows, rates;
    try {
      windows = JSON.parse(el.getAttribute('data-windows') || '[]');
      rates = JSON.parse(el.getAttribute('data-rates') || '{}');
    } catch (e) { return; }
    var st = state(eligible(windows, el.hasAttribute('data-lump-sum')), today, 0);
    if (!st) { el.hidden = true; return; } // 계산기 입력이 바뀌어 기간이 빠지면 다시 숨긴다
    var c = copy(st, rates, el.hasAttribute('data-amount-note'), {
      amountYear: Number(el.getAttribute('data-build-year')) || null,
      ageBased: el.hasAttribute('data-age-based')
    });
    el.querySelector('.prepay-badge').textContent = c.badge;
    var main = el.querySelector('.prepay-main');
    if (c.dday) {
      // 'D-xx'만 D-day 배지 규칙으로 (임박이면 warning 배경, 여유면 텍스트만)
      var parts = c.main.split(c.dday);
      var dd = document.createElement('span');
      dd.className = 'dday' + (c.ddayWarn ? ' b-warn' : '');
      dd.textContent = c.dday;
      main.textContent = '';
      main.appendChild(document.createTextNode(parts[0]));
      main.appendChild(dd);
      main.appendChild(document.createTextNode(parts.slice(1).join(c.dday)));
    } else {
      main.textContent = c.main;
    }
    var apply = el.querySelector('.prepay-apply');
    if (apply) apply.hidden = !c.showApply;
    el.querySelector('.prepay-note').textContent = c.note;
    el.hidden = false;
  }

  function setFlag(el, name, on) {
    if (on) el.setAttribute(name, '');
    else el.removeAttribute(name);
  }

  // 계산기: 입력(배기량·전기차)에 따라 일괄부과 여부·차령 의존 여부를 바꿔 다시 그린다.
  // 표시는 data-* 속성에 남겨서, 이 파일의 첫 그리기(init)보다 먼저 불려도 init이 같은 상태로 그린다
  api.update = function (el, opts) {
    opts = opts || {};
    if ('lumpSum' in opts) setFlag(el, 'data-lump-sum', opts.lumpSum);
    if ('ageBased' in opts) setFlag(el, 'data-age-based', opts.ageBased);
    render(el, todayParts());
  };

  function init() {
    var today = todayParts();
    var els = document.querySelectorAll('.prepay-banner');
    for (var i = 0; i < els.length; i++) render(els[i], today);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})(typeof window !== 'undefined' ? window : globalThis);
