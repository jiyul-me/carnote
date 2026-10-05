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
      januaryProration: { method: 'daily', windowMonth: 1 },
      applicationWindows: [{ month: 1, startDay: 16, endDay: 31, coveredMonths: 11, label: '1월 연납' }]
    }
  };

  // build.py 산출값과 패리티 (아반떼·모닝·쏘나타·그랜저)
  eq(T.taxFor(RATES, 1598, 1).annual, 290830, '아반떼 신차 연세액');
  eq(T.prepay(RATES, 290830).pay, 277530, '아반떼 연납 납부액 (290,830 × 334/365 × 5% = 13,306 → 13,300 할인)');
  eq(T.taxFor(RATES, 1598, 13).annual, 145410, '아반떼 13년차(50% 경감)');
  eq(T.taxFor(RATES, 998, 1).annual, 103790, '모닝 신차');
  eq(T.taxFor(RATES, 1999, 1).annual, 519740, '쏘나타 신차');
  eq(T.taxFor(RATES, 2497, 5).annual, 551830, '그랜저 2.5 5년차');
  eq(T.taxFor(RATES, 3470, 1).annual, 902200, '그랜저 3.5 신차');

  // 부동소수점 회귀: (1 − 0.35)가 0.6499999…가 되어 10원 더 절사되던 버그 — 정수 연산으로 정확히
  eq(T.taxFor(RATES, 1999, 9).annual, 337830, '1,999cc 9년차 = 259,870 + 77,960 (337,810 아님)');
  eq(T.taxFor(RATES, 3342, 8).annual, 608240, '3,342cc 8년차 = 467,880 + 140,360 (608,230 아님)');
  eq(T.taxFor(RATES, 1999, 9).discountRate, 0.35, '9년차 경감률 표시는 0.35 그대로');

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
  eq(p26.pay, 277530, '연도 지정해도 납부액 동일');
  var p27 = T.prepay(RATES, 290830, 2027);
  eq(p27.year, '2026', '키 없는 해(2027)는 가장 최근 연도(2026) 공제율');
  eq(p27.fallback, true, '키 없는 해는 폴백 표시(YYYY년 기준 문구 강제)');
  eq(p27.pay, 277530, '폴백 시 최근 연도 공제율로 계산 (2027은 평년 334/365)');
  eq(T.prepay(RATES, 290830).fallback, false, '연도 생략(기존 호출)은 최근 연도·폴백 아님');

  // 당해 연도 키가 최신이 아니어도 당해 연도 우선 (최근 연도로 덮어쓰지 않는다)
  var RATES2 = {
    displacement: RATES.displacement,
    prepayDiscount: {
      rateByYear: { "2025": 0.05, "2026": 0.03 },
      januaryProration: RATES.prepayDiscount.januaryProration,
      applicationWindows: RATES.prepayDiscount.applicationWindows
    }
  };
  eq(T.prepay(RATES2, 290830, 2025).rate, 0.05, '2025년은 2025년 공제율');
  eq(T.prepay(RATES2, 290830, 2026).rate, 0.03, '2026년은 2026년 공제율');
  eq(T.rateFor(RATES2, 2028).year, '2026', '2028년(키 없음)은 2026년 기준');
  eq(T.prepay(RATES2, 290830, 2026).pay, 290830 - T.floor10(290830 * 334 / 365 * 0.03), '3% 공제 납부액');

  // ── 1월 연납 공제는 일할 (지방세법 제128조 제3항: 연세액 × 납부기한 다음 날~12/31 일수 ÷ 365(윤년 366) × 이자율, 10원 미만 절사)
  // 서울시 공식 예시(신차·비영업용) — 월할(11/12)이면 모두 20~120원 어긋난다. 근거: data/tax-rates.json januaryProration.verification
  // 공제율 표는 테스트 픽스처 (2023년 7%는 과거 공제율이라 실제 데이터 rateByYear에는 없다)
  var OFFICIAL = {
    displacement: RATES.displacement,
    prepayDiscount: {
      rateByYear: { "2023": 0.07, "2024": 0.05, "2025": 0.05, "2026": 0.05 },
      januaryProration: RATES.prepayDiscount.januaryProration,
      applicationWindows: RATES.prepayDiscount.applicationWindows
    }
  };
  function official(year, annual, discount, label) {
    var p = T.prepay(OFFICIAL, annual, year);
    eq(p.discount, discount, year + '년 ' + label + ' 연세액 ' + annual + ' → 공제 ' + discount);
    eq(p.pay, annual - discount, year + '년 ' + label + ' 납부액');
  }
  // 2025년 5% (news.seoul.go.kr/gov/archives/564402 · 554892)
  official(2025, 668400, 30580, '대형 3,342cc');   // 월할이면 30,630
  official(2025, 399600, 18280, '중형 1,998cc');   // 월할이면 18,310
  official(2025, 223720, 10230, '준중형 1,598cc'); // 월할이면 10,250
  official(2025, 100000, 4570, '전기차');          // 월할이면 4,580
  // 2024년(윤년 335/366) 5%
  official(2024, 399600, 18280, '중형 1,998cc');
  official(2024, 223720, 10230, '준중형 1,598cc');
  // 2023년 7% — 지방교육세 포함 총액에 그대로 적용 (news.seoul.go.kr/gov/archives/544533)
  official(2023, 868920, 55650, 'K9 3,342cc');     // 월할이면 55,750, 윤년식(335/366)이면 55,670
  official(2023, 519480, 33270, '쏘나타 1,998cc'); // 월할이면 33,330
  official(2023, 100000, 6400, '전기차');          // 월할이면 6,410

  // 일수: 1월 기간 endDay(31일) 다음 날 ~ 12/31, 분모는 그 해 일수
  var d26 = T.prorationDays(RATES, 2026);
  eq(d26.days + '/' + d26.yearDays, '334/365', '2026년(평년) 334/365');
  var d24 = T.prorationDays(RATES, 2024);
  eq(d24.days + '/' + d24.yearDays, '335/366', '2024년(윤년) 335/366');
  var d28 = T.prorationDays(RATES, 2028);
  eq(d28.days + '/' + d28.yearDays, '335/366', '2028년(윤년) 335/366');
  var d00 = T.prorationDays(RATES, 2100);
  eq(d00.days + '/' + d00.yearDays, '334/365', '2100년(100의 배수, 평년) 334/365');
  // 윤년에는 일수가 공제액을 바꾼다: 868,920원 × 335/366 × 5% = 39,766 → 39,760 (평년식 334/365면 39,750)
  var p28 = T.prepay(RATES, 868920, 2028);
  eq(p28.discount, 39760, '2028년(윤년, 2026년 공제율 폴백) 공제액은 335/366 기준');
  eq(p28.fallback, true, '2028년은 공제율 키가 없어 폴백 표시');
  eq(p28.days + '/' + p28.yearDays, '335/366', '폴백이어도 일수는 요청한 해(2028) 기준');
  // 연도 생략이면 일수도 공제율 연도(최근 연도) 기준
  eq(T.prepay(RATES, 868920).yearDays, 365, '연도 생략 → 2026년 일수');
  // 1월 기간 데이터가 빠지면 조용히 틀리지 않고 멈춘다
  var threw = false;
  try {
    T.prepay({ prepayDiscount: { rateByYear: { "2026": 0.05 }, januaryProration: { method: 'daily', windowMonth: 1 }, applicationWindows: [] } }, 100000, 2026);
  } catch (e) { threw = true; }
  eq(threw, true, '1월 신청 기간이 없으면 예외');

  print(failures === 0 ? '통과: ' + total + '/' + total : '실패: ' + failures + '/' + total);
  if (failures > 0) throw new Error(failures + '개 실패');
})();
