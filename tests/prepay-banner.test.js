/* jsc 실행: jsc js/prepay-banner.js tests/prepay-banner.test.js
 * 연납 신청 기간 안내 줄의 상태 판정·문구. 기간 데이터는 data/tax-rates.json applicationWindows와 같은 구조(테스트 고정본) */
(function () {
  'use strict';
  var B = globalThis.ChailjiPrepayBanner;
  var failures = 0, total = 0;
  function eq(a, b, label) {
    total++;
    if (a !== b) { failures++; print('FAIL ' + label + '\n  기대: ' + b + '\n  실제: ' + a); }
  }
  function d(s) { var p = s.split('-'); return { y: +p[0], m: +p[1], d: +p[2] }; }
  function kindOf(st) { return st ? st.kind + ':' + st.window.month + '월:' + st.year + ':' + st.days : 'hidden'; }

  var WINDOWS = [
    { month: 1, startDay: 16, endDay: 31, coveredMonths: 11, label: '1월 연납' },
    { month: 3, startDay: 16, endDay: 31, coveredMonths: 9, label: '3월 연납' },
    { month: 6, startDay: 16, endDay: 30, coveredMonths: 6, label: '6월 연납' },
    { month: 9, startDay: 16, endDay: 30, coveredMonths: 3, label: '9월 연납' }
  ];
  var LUMP = WINDOWS.slice(0, 2); // 10만원 이하 차량: 1·3월만 (build.py가 걸러서 심는다)
  var RATES = { '2024': 0.05, '2025': 0.05, '2026': 0.05 };
  var LEAD = 60;

  // 작업 검증 날짜 4개
  eq(kindOf(B.state(WINDOWS, d('2026-10-04'), LEAD)), 'hidden', '10/4: 다음 1월까지 104일 → 숨김');
  eq(kindOf(B.state(WINDOWS, d('2026-12-01'), LEAD)), 'soon:1월:2027:46', '12/1: 1월 연납 D-46 (다음 해)');
  eq(kindOf(B.state(WINDOWS, d('2027-01-20'), LEAD)), 'open:1월:2027:11', '1/20: 1월 신청 기간, 마감까지 11일');
  eq(kindOf(B.state(WINDOWS, d('2027-02-10'), LEAD)), 'soon:3월:2027:34', '2/10: 3월 연납 D-34');

  // 경계: 시작일·마감일 포함, 마감 다음 날은 다음 기간 예고
  eq(kindOf(B.state(WINDOWS, d('2027-01-16'), LEAD)), 'open:1월:2027:15', '1/16 시작일 포함');
  eq(kindOf(B.state(WINDOWS, d('2027-01-31'), LEAD)), 'open:1월:2027:0', '1/31 마감일 포함');
  eq(kindOf(B.state(WINDOWS, d('2027-01-15'), LEAD)), 'soon:1월:2027:1', '1/15 하루 전 D-1');
  eq(kindOf(B.state(WINDOWS, d('2027-06-30'), LEAD)), 'open:6월:2027:0', '6/30 마감일 포함 (30일 달)');
  eq(kindOf(B.state(WINDOWS, d('2026-11-16'), LEAD)), 'hidden', '11/16: 61일 전 → 숨김');
  eq(kindOf(B.state(WINDOWS, d('2026-11-17'), LEAD)), 'soon:1월:2027:60', '11/17: 정확히 60일 전 → 노출');
  eq(kindOf(B.state(WINDOWS, d('2028-02-29'), LEAD)), 'soon:3월:2028:16', '윤년 2/29');

  // 10만원 이하(6월 일괄부과) 차량은 6·9월 기간이 없다
  eq(kindOf(B.state(WINDOWS, d('2027-05-01'), LEAD)), 'soon:6월:2027:46', '일반: 5/1 → 6월 연납 D-46');
  eq(kindOf(B.state(LUMP, d('2027-05-01'), LEAD)), 'hidden', '일괄부과 차량: 5/1 → 숨김');
  eq(kindOf(B.state(LUMP, d('2027-06-20'), LEAD)), 'hidden', '일괄부과 차량: 6월 기간에도 숨김');

  // 공제율 폴백
  eq(B.rateFor(RATES, 2026).fallback, false, '2026 키 있음');
  eq(B.rateFor(RATES, 2027).year, '2026', '2027 키 없음 → 2026');
  eq(B.rateFor(RATES, 2027).fallback, true, '2027 폴백 표시');

  // 문구
  var c = B.copy(B.state(WINDOWS, d('2027-01-20'), LEAD), RATES, true);
  eq(c.badge, '1월 연납', '배지는 기간 라벨');
  eq(c.main, '지금 신청 기간이에요 · 1월 31일까지', '1월 기간 중 문구');
  eq(c.showApply, true, '기간 중에는 위택스 링크');
  eq(c.note, '2~12월분 세액의 5%(2026년 공제율 기준)를 공제받아요 — 이 페이지의 ‘1월 연납 시’ 금액으로 낼 수 있어요.',
    '1월 기간: 1월 기준 금액 + 2027년은 2026년 공제율 기준 명시');

  c = B.copy(B.state(WINDOWS, d('2026-01-20'), LEAD), RATES, true);
  eq(c.note.indexOf('공제율 기준') < 0, true, '2026년 1월은 폴백 문구 없음');

  c = B.copy(B.state(WINDOWS, d('2026-12-01'), LEAD), RATES, false);
  eq(c.main, '신청 시작까지 D-46 · 1월 16일부터', '예고 문구');
  eq(c.dday, 'D-46', 'D-day 분리');
  eq(c.ddayWarn, false, 'D-46은 여유 (텍스트만)');
  eq(c.showApply, false, '예고 때는 신청 링크 숨김');
  eq(c.note, '2~12월분 세액의 5%(2026년 공제율 기준)를 공제받아요.', '허브: 금액 언급 없이');

  c = B.copy(B.state(WINDOWS, d('2027-03-05'), LEAD), RATES, true);
  eq(c.ddayWarn, true, 'D-11은 임박 배지');
  eq(c.note, '4~12월분만 5%(2026년 공제율 기준) 공제돼 이 페이지의 ‘1월 연납 시’ 금액보다 할인이 적어요.',
    '3월: 1월 기준 금액보다 적다고 명시');

  c = B.copy(B.state(WINDOWS, d('2026-09-20'), LEAD), RATES, false);
  eq(c.note, '10~12월분만 5% 공제돼 1월 연납보다 할인이 적어요.', '9월(허브)');

  print(failures === 0 ? '통과: ' + total + '/' + total : '실패: ' + failures + '/' + total);
  if (failures > 0) throw new Error(failures + '개 실패');
})();
