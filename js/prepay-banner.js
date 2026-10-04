/* 차일지 — 자동차세 연납 신청 기간 안내 줄 (차종·허브·계산기 페이지의 .prepay-banner).
 * 신청 기간·공제율·노출 일수는 scripts/build.py가 data/tax-rates.json에서 읽어 data-* 속성으로 심는다 — 여기 하드코딩 금지.
 * 날짜 판단만 브라우저의 오늘 날짜로 한다. 기간 밖이거나 JS가 꺼져 있으면 hidden 그대로(아무것도 안 보임).
 * state·copy는 DOM 비의존 순수 함수 — jsc 테스트 가능 (tests/prepay-banner.test.js). */
(function (global) {
  'use strict';

  var DAY_MS = 86400000;

  // 달력 날짜 → 일 번호. UTC로 세서 서머타임·시각과 무관하게 날짜 차이만 센다
  function dayNum(y, m, d) { return Math.round(Date.UTC(y, m - 1, d) / DAY_MS); }

  // windows: [{month, startDay, endDay, coveredMonths, label}], today: {y, m, d}
  // 반환: null(숨김) | {kind: 'open'|'soon', window, year(그 기간의 연도), days}
  //   open = 신청 기간 중 (days = 마감까지 남은 날), soon = 다음 시작까지 leadDays 이내 (days = 시작까지 남은 날)
  function state(windows, today, leadDays) {
    var t = dayNum(today.y, today.m, today.d);
    var next = null;
    for (var dy = 0; dy <= 1; dy++) { // 12월에는 다음 해 1월 기간을 본다
      var y = today.y + dy;
      for (var i = 0; i < windows.length; i++) {
        var w = windows[i];
        var s = dayNum(y, w.month, w.startDay);
        var e = dayNum(y, w.month, w.endDay);
        if (t >= s && t <= e) return { kind: 'open', window: w, year: y, days: e - t };
        if (s > t && (!next || s < next.s)) next = { s: s, w: w, y: y };
      }
    }
    if (next && next.s - t <= leadDays) return { kind: 'soon', window: next.w, year: next.y, days: next.s - t };
    return null;
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
  // 페이지 금액은 늘 1월 연납 기준이라, 1월이 아닌 기간에는 할인이 그보다 적다는 걸 밝힌다
  function copy(st, rateByYear, hasAmount) {
    var w = st.window;
    var r = rateFor(rateByYear, st.year);
    var from = 12 - w.coveredMonths + 1; // 신청 다음 달 ~ 12월
    var isJan = w.month === 1; // 페이지 금액(januaryProration)과 같은 기간
    var main = st.kind === 'open'
      ? '지금 신청 기간이에요 · ' + w.month + '월 ' + w.endDay + '일까지'
      : '신청 시작까지 D-' + st.days + ' · ' + w.month + '월 ' + w.startDay + '일부터';
    // 그 해 공제율이 아직 데이터에 없으면 어느 해 기준인지 반드시 밝힌다
    var rateText = pct(r.rate) + (r.fallback ? '(' + r.year + '년 공제율 기준)' : '');
    var note;
    if (isJan) {
      note = from + '~12월분 세액의 ' + rateText + '를 공제받아요' +
        (hasAmount ? ' — 이 페이지의 ‘1월 연납 시’ 금액으로 낼 수 있어요.' : '.');
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

  global.ChailjiPrepayBanner = { state: state, rateFor: rateFor, copy: copy };

  if (typeof document === 'undefined') return;

  function render(el, today) {
    var windows, rates;
    try {
      windows = JSON.parse(el.getAttribute('data-windows') || '[]');
      rates = JSON.parse(el.getAttribute('data-rates') || '{}');
    } catch (e) { return; }
    var st = state(windows, today, Number(el.getAttribute('data-lead-days')) || 0);
    if (!st) return;
    var c = copy(st, rates, el.hasAttribute('data-amount-note'));
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

  function init() {
    var now = new Date();
    var today = { y: now.getFullYear(), m: now.getMonth() + 1, d: now.getDate() };
    var els = document.querySelectorAll('.prepay-banner');
    for (var i = 0; i < els.length; i++) render(els[i], today);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})(typeof window !== 'undefined' ? window : globalThis);
