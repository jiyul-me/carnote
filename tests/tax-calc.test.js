/* jsc 실행: jsc js/tax-calc.js tests/tax-calc.test.js
 * 기대값은 scripts/build.py 산출값과의 동일성(패리티) 검증 — build.py 스팟 체크에서 확인된 수치 */
(function () {
  'use strict';
  var T = globalThis.ChailjiTax;
  var failures = 0, total = 0;
  function eq(a, b, label) {
    total++;
    if (a !== b) { failures++; print('FAIL ' + label + '\n  기대: ' + b + '\n  실제: ' + a); }
  }

  // data/tax-rates.json과 동일 구조 (테스트 고정본)
  var RATES = {
    displacement: {
      brackets: [
        { maxCc: 1000, wonPerCc: 80 },
        { maxCc: 1600, wonPerCc: 140 },
        { maxCc: null, wonPerCc: 200 }
      ],
      agingDiscount: { startCarAge: 3, ratePerYear: 0.05, maxRate: 0.5 },
      educationTaxRate: 0.3,
      ev: { annualTotalKrw: 130000 }
    },
    prepayDiscount: {
      rateByYear: { "2026": 0.05 },
      januaryProration: { coveredMonths: 11, totalMonths: 12 }
    }
  };

  // build.py 산출값과 패리티 (아반떼·모닝·쏘나타·그랜저)
  eq(T.taxFor(RATES, 1598, 1).annual, 290830, '아반떼 신차 연세액');
  eq(T.prepay(RATES, 290830).pay, 277510, '아반떼 연납 납부액');
  eq(T.taxFor(RATES, 1598, 13).annual, 145410, '아반떼 13년차(50% 경감)');
  eq(T.taxFor(RATES, 998, 1).annual, 103790, '모닝 신차');
  eq(T.taxFor(RATES, 1999, 1).annual, 519740, '쏘나타 신차');
  eq(T.taxFor(RATES, 2497, 5).annual, 551830, '그랜저 2.5 5년차');
  eq(T.taxFor(RATES, 3470, 1).annual, 902200, '그랜저 3.5 신차');

  // 경계: 1,000cc와 1,600cc는 '이하' 구간
  eq(T.taxFor(RATES, 1000, 1).perCc, 80, '1000cc는 80원 구간');
  eq(T.taxFor(RATES, 1600, 1).perCc, 140, '1600cc는 140원 구간');
  eq(T.taxFor(RATES, 1601, 1).perCc, 200, '1601cc는 200원 구간');

  // 경감률 상한
  eq(T.taxFor(RATES, 1598, 12).discountRate, 0.5, '12년차 50% 상한');
  eq(T.taxFor(RATES, 1598, 3).discountRate, 0.05, '3년차 5%');

  // 전기차 정액
  eq(T.evTax(RATES), 130000, '전기차 고정');

  // 연납 공제율 폴백 (tax-rates.json fallbackRule) — 계산기는 브라우저의 올해를 넘긴다
  var p26 = T.prepay(RATES, 290830, 2026);
  eq(p26.year, '2026', '당해 연도 키가 있으면 그 해 공제율');
  eq(p26.fallback, false, '당해 연도 키가 있으면 폴백 아님');
  eq(p26.pay, 277510, '연도 지정해도 납부액 동일');
  var p27 = T.prepay(RATES, 290830, 2027);
  eq(p27.year, '2026', '키 없는 해(2027)는 가장 최근 연도(2026) 공제율');
  eq(p27.fallback, true, '키 없는 해는 폴백 표시(YYYY년 기준 문구 강제)');
  eq(p27.pay, 277510, '폴백 시 최근 연도 공제율로 계산');
  eq(T.prepay(RATES, 290830).fallback, false, '연도 생략(기존 호출)은 최근 연도·폴백 아님');

  // 당해 연도 키가 최신이 아니어도 당해 연도 우선 (최근 연도로 덮어쓰지 않는다)
  var RATES2 = {
    displacement: RATES.displacement,
    prepayDiscount: {
      rateByYear: { "2025": 0.05, "2026": 0.03 },
      januaryProration: { coveredMonths: 11, totalMonths: 12 }
    }
  };
  eq(T.prepay(RATES2, 290830, 2025).rate, 0.05, '2025년은 2025년 공제율');
  eq(T.prepay(RATES2, 290830, 2026).rate, 0.03, '2026년은 2026년 공제율');
  eq(T.rateFor(RATES2, 2028).year, '2026', '2028년(키 없음)은 2026년 기준');
  eq(T.prepay(RATES2, 290830, 2026).pay, 290830 - T.floor10(290830 * 11 / 12 * 0.03), '3% 공제 납부액');

  print(failures === 0 ? '통과: ' + total + '/' + total : '실패: ' + failures + '/' + total);
  if (failures > 0) throw new Error(failures + '개 실패');
})();
