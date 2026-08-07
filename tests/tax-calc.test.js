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

  print(failures === 0 ? '통과: ' + total + '/' + total : '실패: ' + failures + '/' + total);
  if (failures > 0) throw new Error(failures + '개 실패');
})();
